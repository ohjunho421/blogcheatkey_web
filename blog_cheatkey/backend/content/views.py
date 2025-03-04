from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import BlogContent, MorphemeAnalysis
from key_word.models import Keyword
from .serializers import BlogContentSerializer, MorphemeAnalysisSerializer
from .services.generator import ContentGenerator

class BlogContentViewSet(viewsets.ModelViewSet):
    serializer_class = BlogContentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return BlogContent.objects.filter(user=self.request.user).order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        keyword_id = request.data.get('keyword_id')
        target_audience = request.data.get('target_audience', {})
        business_info = request.data.get('business_info', {})
        
        if not keyword_id:
            return Response({"error": "keyword_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 콘텐츠 생성 서비스 초기화
            generator = ContentGenerator()
            
            # 콘텐츠 생성
            content_id = generator.generate_content(
                keyword_id=keyword_id,
                user_id=request.user.id,
                target_audience=target_audience,
                business_info=business_info
            )
            
            if content_id:
                content = BlogContent.objects.get(id=content_id)
                return Response({
                    "message": "콘텐츠가 성공적으로 생성되었습니다.",
                    "data": BlogContentSerializer(content).data
                })
            else:
                return Response({"error": "콘텐츠 생성에 실패했습니다."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Keyword.DoesNotExist:
            return Response({"error": "Invalid keyword_id"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def optimize(self, request, pk=None):
        content = self.get_object()
        
        try:
            # 콘텐츠 생성 서비스 초기화
            generator = ContentGenerator()
            
            # 형태소 분석
            morpheme_analysis = generator.analyze_morphemes(
                content.content, 
                content.keyword.keyword
            )
            
            # 최적화 필요 여부 확인
            if morpheme_analysis['needs_optimization']:
                # 데이터 구성
                data = {
                    "keyword": content.keyword.keyword,
                    "morphemes": [m for m in morpheme_analysis['morpheme_analysis'].keys()]
                }
                
                # 최적화 프롬프트 생성
                optimization_prompt = generator._create_optimization_prompt(content.content, data)
                
                # 최적화 수행 (Claude API 호출)
                response = generator.client.messages.create(
                    model=generator.model,
                    max_tokens=4096,
                    temperature=0.5,
                    messages=[
                        {"role": "user", "content": optimization_prompt}
                    ]
                )
                
                optimized_content = response.content[0].text
                
                # 업데이트
                content.content = optimized_content
                content.mobile_formatted_content = generator._format_for_mobile(optimized_content)
                content.char_count = len(optimized_content.replace(" ", ""))
                content.is_optimized = True
                content.save()
                
                # 형태소 분석 결과 업데이트
                content.morpheme_analyses.all().delete()
                new_analysis = generator.analyze_morphemes(optimized_content, content.keyword.keyword)
                for morpheme, info in new_analysis.get('morpheme_analysis', {}).items():
                    MorphemeAnalysis.objects.create(
                        content=content,
                        morpheme=morpheme,
                        count=info.get('count', 0),
                        is_valid=info.get('is_valid', False)
                    )
                
                return Response({
                    "message": "콘텐츠가 성공적으로 최적화되었습니다.",
                    "data": BlogContentSerializer(content).data
                })
            else:
                return Response({"message": "이미 최적화된 콘텐츠입니다."})
                
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def mobile_format(self, request, pk=None):
        content = self.get_object()
        
        try:
            # 이미 모바일 포맷이 있는 경우
            if content.mobile_formatted_content:
                return Response({"mobile_content": content.mobile_formatted_content})
            
            # 없는 경우 변환
            generator = ContentGenerator()
            mobile_content = generator._format_for_mobile(content.content)
            
            # 저장
            content.mobile_formatted_content = mobile_content
            content.save()
            
            return Response({"mobile_content": mobile_content})
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


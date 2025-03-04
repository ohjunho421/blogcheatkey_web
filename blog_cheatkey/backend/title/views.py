from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import TitleSuggestion
from content.models import BlogContent
from .serializers import TitleSuggestionSerializer
from .services.generator import TitleGenerator
from .services.summarizer import ContentSummarizer

class TitleSuggestionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TitleSuggestionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = TitleSuggestion.objects.filter(content__user=self.request.user)
        
        # 필터링
        content_id = self.request.query_params.get('content')
        title_type = self.request.query_params.get('type')
        
        if content_id:
            queryset = queryset.filter(content_id=content_id)
        
        if title_type:
            queryset = queryset.filter(title_type=title_type)
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        content_id = request.data.get('content_id')
        
        if not content_id:
            return Response({"error": "content_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 콘텐츠 확인
            content = BlogContent.objects.get(id=content_id, user=request.user)
            
            # 제목 생성 서비스 초기화
            generator = TitleGenerator()
            
            # 제목 생성
            titles = generator.generate_titles(content.pk)
            
            if titles:
                # 결과 포맷팅
                result = {}
                for title_type, suggestions in titles.items():
                    result[title_type] = []
                    for suggestion in suggestions:
                        title_obj = TitleSuggestion.objects.get(id=suggestion['id'])
                        result[title_type].append(TitleSuggestionSerializer(title_obj).data)
                
                return Response({
                    "message": "제목이 성공적으로 생성되었습니다.",
                    "data": result
                })
            else:
                return Response({"error": "제목 생성에 실패했습니다."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except BlogContent.DoesNotExist:
            return Response({"error": "Invalid content_id"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def select(self, request, pk=None):
        title = self.get_object()
        content = title.content
        
        try:
            # 이전에 선택된 제목 해제
            TitleSuggestion.objects.filter(content=content, selected=True).update(selected=False)
            
            # 현재 제목 선택
            title.selected = True
            title.save()
            
            # 콘텐츠 제목 업데이트
            content.title = title.suggestion
            content.save()
            
            return Response({
                "message": "제목이 성공적으로 선택되었습니다.",
                "data": TitleSuggestionSerializer(title).data
            })
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def summarize(self, request):
        content_id = request.data.get('content_id')
        summary_type = request.data.get('summary_type', 'vrew')
        
        if not content_id:
            return Response({"error": "content_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 콘텐츠 확인
            content = BlogContent.objects.get(id=content_id, user=request.user)
            
            # 유효한 요약 유형 확인
            valid_types = ['vrew', 'social', 'bullet']
            if summary_type not in valid_types:
                return Response({"error": "Invalid summary_type"}, status=status.HTTP_400_BAD_REQUEST)
            
            # 요약 생성 서비스 초기화
            summarizer = ContentSummarizer()
            
            # 요약 생성
            summary = summarizer.create_summary(content.pk, summary_type)
            
            return Response({
                "message": "요약이 성공적으로 생성되었습니다.",
                "data": {
                    "summary": summary,
                    "summary_type": summary_type
                }
            })
            
        except BlogContent.DoesNotExist:
            return Response({"error": "Invalid content_id"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
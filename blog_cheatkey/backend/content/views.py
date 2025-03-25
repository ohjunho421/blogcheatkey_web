import threading
import json
import logging
from django.core.cache import cache
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import BlogContent, MorphemeAnalysis
from key_word.models import Keyword
from .serializers import BlogContentSerializer, MorphemeAnalysisSerializer
from .services.generator import ContentGenerator

logger = logging.getLogger(__name__)

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
        custom_morphemes = request.data.get('custom_morphemes', [])
        
        if not keyword_id:
            return Response({"error": "keyword_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 키워드 존재 확인
            keyword = Keyword.objects.get(id=keyword_id)
            
            # 백그라운드에서 콘텐츠 생성 시작
            thread = threading.Thread(
                target=self._generate_content_in_background,
                args=(keyword_id, request.user.id, target_audience, business_info, custom_morphemes)
            )
            thread.daemon = True
            thread.start()
            
            # 생성 작업이 시작됨을 알리는 임시 콘텐츠 생성
            temp_content = BlogContent.objects.create(
                user=request.user,
                keyword=keyword,
                title=f"{keyword.keyword} (생성 중...)",
                content="콘텐츠가 생성 중입니다. 상태를 확인하려면 /status 엔드포인트를 사용하세요.",
                is_optimized=False
            )
            
            # 즉시 응답 반환
            return Response({
                "message": "콘텐츠 생성이 시작되었습니다. 상태를 확인하려면 /status/ 엔드포인트를 사용하세요.",
                "keyword_id": keyword_id,
                "temp_content_id": temp_content.id,
                "status": "processing"
            })
                
        except Keyword.DoesNotExist:
            return Response({"error": "Invalid keyword_id"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _generate_content_in_background(self, keyword_id, user_id, target_audience, business_info, custom_morphemes):
        """백그라운드에서 콘텐츠를 생성하는 메서드"""
        try:
            # 상태 업데이트 - 처리 중
            cache_key = f"content_generation_{keyword_id}_{user_id}"
            cache.set(cache_key, {"status": "running", "progress": 0}, timeout=3600)
            
            # 임시 콘텐츠 찾기
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)
            keyword = Keyword.objects.get(id=keyword_id)
            
            # 중요: 사용자가 수정한 최신 소제목 정보 가져오기
            subtopics = list(keyword.subtopics.order_by('order').values_list('title', flat=True))
            logger.info(f"콘텐츠 생성에 사용될 소제목: {subtopics}")
            
            temp_content = BlogContent.objects.filter(
                user=user,
                keyword=keyword,
                title__contains="(생성 중...)"
            ).order_by('-created_at').first()
            
            # 로깅 추가
            logger.info(f"백그라운드 콘텐츠 생성 시작: keyword_id={keyword_id}, user_id={user_id}")
            
            # 콘텐츠 생성 - 중간 진행 상태 업데이트
            cache.set(cache_key, {"status": "running", "progress": 25, "message": "연구 자료 수집 중..."}, timeout=3600)
            
            generator = ContentGenerator()
            
            # 상태 업데이트
            cache.set(cache_key, {"status": "running", "progress": 50, "message": "AI가 콘텐츠 작성 중..."}, timeout=3600)
            
            # 여기서 명시적으로 subtopics를 전달
            content_id = generator.generate_content(
                keyword_id=keyword_id,
                user_id=user_id,
                target_audience=target_audience,
                business_info=business_info,
                custom_morphemes=custom_morphemes,
                subtopics=subtopics
            )
            
            # 상태 업데이트
            cache.set(cache_key, {"status": "running", "progress": 75, "message": "콘텐츠 최적화 중..."}, timeout=3600)
            
            # 결과 캐싱
            if content_id:
                # 실제 콘텐츠가 생성됨 - 임시 콘텐츠 삭제
                if temp_content and temp_content.id != content_id:
                    temp_content.delete()
                    
                cache.set(
                    cache_key, 
                    {
                        "status": "completed", 
                        "progress": 100,
                        "content_id": content_id,
                        "message": "콘텐츠가 성공적으로 생성되었습니다."
                    }, 
                    timeout=3600
                )
                
                # 로깅 추가
                logger.info(f"백그라운드 콘텐츠 생성 완료: content_id={content_id}")
            else:
                # 생성 실패 - 임시 콘텐츠 업데이트
                if temp_content:
                    temp_content.content = "콘텐츠 생성에 실패했습니다. 다시 시도해주세요."
                    temp_content.save()
                    
                cache.set(
                    cache_key, 
                    {
                        "status": "failed", 
                        "error": "콘텐츠 생성에 실패했습니다."
                    }, 
                    timeout=3600
                )
                
                # 로깅 추가
                logger.error(f"백그라운드 콘텐츠 생성 실패: keyword_id={keyword_id}, user_id={user_id}")
                
        except Exception as e:
            # 오류 상태 저장
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"백그라운드 콘텐츠 생성 오류: {str(e)}")
            logger.error(error_traceback)
            
            # 임시 콘텐츠 오류 메시지 업데이트
            try:
                if 'temp_content' in locals() and temp_content:
                    temp_content.content = f"콘텐츠 생성 중 오류가 발생했습니다: {str(e)}"
                    temp_content.save()
            except:
                pass
                
            cache.set(
                cache_key, 
                {
                    "status": "failed", 
                    "error": str(e)
                }, 
                timeout=3600
            )
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """콘텐츠 생성 상태 확인 API"""
        keyword_id = request.query_params.get('keyword_id')
        
        if not keyword_id:
            return Response({"error": "keyword_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 캐시에서 상태 확인
        cache_key = f"content_generation_{keyword_id}_{request.user.id}"
        status_data = cache.get(cache_key)
        
        if not status_data:
            # 상태 정보가 없으면 완료된 콘텐츠 확인
            try:
                content = BlogContent.objects.filter(
                    keyword_id=keyword_id, 
                    user=request.user,
                    is_optimized=True  # 최적화까지 완료된 콘텐츠만
                ).order_by('-created_at').first()
                
                if content:
                    return Response({
                        "status": "completed",
                        "message": "콘텐츠가 이미 생성되어 있습니다.",
                        "content_id": content.id,
                        "data": BlogContentSerializer(content).data
                    })
                else:
                    # 생성 중이지만 최적화는 안 된 콘텐츠 확인
                    processing_content = BlogContent.objects.filter(
                        keyword_id=keyword_id, 
                        user=request.user,
                        is_optimized=False
                    ).order_by('-created_at').first()
                    
                    if processing_content:
                        if "(생성 중...)" in processing_content.title:
                            return Response({
                                "status": "processing",
                                "message": "콘텐츠 생성이 진행 중입니다.",
                                "temp_content_id": processing_content.id
                            })
                        else:
                            return Response({
                                "status": "optimization_needed",
                                "message": "콘텐츠 생성은 완료되었으나 최적화가 필요합니다.",
                                "content_id": processing_content.id,
                                "data": BlogContentSerializer(processing_content).data
                            })
                    else:
                        return Response({
                            "status": "not_started",
                            "message": "콘텐츠 생성이 시작되지 않았습니다."
                        })
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(status_data)
    
    @action(detail=True, methods=['post'])
    def optimize(self, request, pk=None):
        """콘텐츠 최적화 API"""
        content = self.get_object()
        
        # 백그라운드에서 최적화 시작
        thread = threading.Thread(
            target=self._optimize_content_in_background,
            args=(content.pk,)
        )
        thread.daemon = True
        thread.start()
        
        return Response({
            "message": "콘텐츠 최적화가 시작되었습니다. 상태를 확인하려면 /optimize_status/ 엔드포인트를 사용하세요.",
            "content_id": content.pk,
            "status": "processing"
        })
    
    def _optimize_content_in_background(self, content_id):
        """백그라운드에서 콘텐츠를 최적화하는 메서드"""
        try:
            # 상태 업데이트 - 처리 중
            cache_key = f"content_optimization_{content_id}"
            cache.set(cache_key, {"status": "running", "progress": 0}, timeout=3600)
            
            content = BlogContent.objects.get(id=content_id)
            
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
                    if morpheme and len(morpheme) > 1:  # 1글자 미만은 저장하지 않음
                        MorphemeAnalysis.objects.create(
                            content=content,
                            morpheme=morpheme,
                            count=info.get('count', 0),
                            is_valid=info.get('is_valid', False)
                        )
                
                # 결과 캐싱
                cache.set(
                    cache_key, 
                    {
                        "status": "completed", 
                        "message": "콘텐츠가 성공적으로 최적화되었습니다.",
                        "content_id": content_id
                    }, 
                    timeout=3600
                )
            else:
                # 이미 최적화된 콘텐츠
                cache.set(
                    cache_key, 
                    {
                        "status": "completed", 
                        "message": "이미 최적화된 콘텐츠입니다.",
                        "content_id": content_id
                    }, 
                    timeout=3600
                )
                
        except Exception as e:
            # 오류 상태 저장
            import traceback
            print(f"백그라운드 콘텐츠 최적화 오류: {str(e)}")
            print(traceback.format_exc())
            
            cache.set(
                cache_key, 
                {
                    "status": "failed", 
                    "error": str(e)
                }, 
                timeout=3600
            )
    
    @action(detail=True, methods=['get'])
    def optimize_status(self, request, pk=None):
        """콘텐츠 최적화 상태 확인 API"""
        content = self.get_object()
        
        # 캐시에서 상태 확인
        cache_key = f"content_optimization_{content.pk}"
        status_data = cache.get(cache_key)
        
        if not status_data:
            # 상태 정보가 없으면 콘텐츠 최적화 상태 직접 확인
            if content.is_optimized:
                return Response({
                    "status": "completed",
                    "message": "콘텐츠가 이미 최적화되어 있습니다.",
                    "content_id": content.pk,
                    "data": BlogContentSerializer(content).data
                })
            else:
                return Response({
                    "status": "not_started",
                    "message": "콘텐츠 최적화가 시작되지 않았습니다.",
                    "content_id": content.pk
                })
        
        # 최적화가 완료된 경우 최신 데이터 반환
        if status_data.get('status') == 'completed':
            return Response({
                **status_data,
                "data": BlogContentSerializer(content).data
            })
        
        return Response(status_data)
    
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
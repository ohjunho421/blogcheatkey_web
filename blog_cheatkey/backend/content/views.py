import threading
import json
import logging
import asyncio
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
        """쿼리셋 최적화: select_related 및 필터링 개선"""
        queryset = BlogContent.objects.filter(user=self.request.user).select_related('keyword')
        
        # 쿼리 파라미터에 따른 추가 필터링
        keyword_id = self.request.query_params.get('keyword_id')
        if keyword_id:
            queryset = queryset.filter(keyword_id=keyword_id)
            
        # 최적화 상태에 따른 필터링
        optimized = self.request.query_params.get('optimized')
        if optimized is not None:
            queryset = queryset.filter(is_optimized=(optimized.lower() == 'true'))
        
        return queryset.order_by('-created_at')
    
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
            
            # 백그라운드에서 콘텐츠 생성 시작 (개선된 방식)
            def start_generation():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    generator = ContentGenerator()
                    # 비동기 생성 메서드 호출
                    content_id = loop.run_until_complete(
                        generator.generate_content_async(
                            keyword_id, 
                            request.user.id, 
                            target_audience, 
                            business_info, 
                            custom_morphemes
                        )
                    )
                    
                    # 결과 캐싱
                    if content_id:
                        cache.set(
                            f"content_generation_{keyword_id}_{request.user.id}",
                            {
                                "status": "completed",
                                "progress": 100,
                                "content_id": content_id,
                                "message": "콘텐츠가 성공적으로 생성되었습니다."
                            },
                            timeout=3600
                        )
                    else:
                        cache.set(
                            f"content_generation_{keyword_id}_{request.user.id}",
                            {
                                "status": "failed",
                                "error": "콘텐츠 생성에 실패했습니다."
                            },
                            timeout=3600
                        )
                except Exception as e:
                    logger.error(f"콘텐츠 생성 오류: {str(e)}", exc_info=True)
                    cache.set(
                        f"content_generation_{keyword_id}_{request.user.id}",
                        {
                            "status": "failed",
                            "error": str(e)
                        },
                        timeout=3600
                    )
                finally:
                    loop.close()
            
            # 스레드 시작
            thread = threading.Thread(target=start_generation)
            thread.daemon = True
            thread.start()
            
            # 임시 콘텐츠 생성
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
            logger.error(f"생성 요청 처리 오류: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def status(self, request):
        """콘텐츠 생성 상태 확인 API"""
        keyword_id = request.query_params.get('keyword_id')
        
        if not keyword_id:
            return Response({"error": "keyword_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 캐시에서 상태 확인
            cache_key = f"content_generation_{keyword_id}_{request.user.id}"
            status_data = cache.get(cache_key)
            
            if not status_data:
                # 상태 정보가 없으면 완료된 콘텐츠 확인
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
            
            return Response(status_data)
        except Exception as e:
            logger.error(f"상태 확인 중 오류: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        
    @action(detail=False, methods=['get'])
    def generator_status(self, request):
        """콘텐츠 생성 진행 상태 확인 API"""
        keyword_id = request.query_params.get('keyword_id')
        
        if not keyword_id:
            return Response({"error": "keyword_id 파라미터가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # ContentGenerator의 클래스 메서드를 통해 현재 진행 상태 조회
            generator = ContentGenerator()
            status_data = ContentGenerator.get_generation_status(keyword_id)
            
            # 진행 상태가 completed이고 실제 콘텐츠가 존재하는 경우 콘텐츠 정보 추가
            if status_data.get('status') == 'completed':
                content = BlogContent.objects.filter(
                    keyword_id=keyword_id, 
                    user=request.user
                ).order_by('-created_at').first()
                
                if content:
                    status_data['content_id'] = content.id
            
            return Response(status_data)
        except Exception as e:
            logger.error(f"생성 상태 확인 중 오류: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
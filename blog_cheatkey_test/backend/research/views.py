from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ResearchSource, StatisticData
from key_word.models import Keyword
from .serializers import ResearchSourceSerializer, StatisticDataSerializer
from .services.collector import ResearchCollector
from .services.duckduckgo_search import DuckDuckGoSearchService
import logging
import threading
import time
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

# 백그라운드에서 연구 자료 수집을 위한 딕셔너리
research_tasks = {}

class ResearchSourceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ResearchSourceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = ResearchSource.objects.filter(keyword__user=self.request.user)
        
        # 필터링
        keyword_id = self.request.query_params.get('keyword')
        source_type = self.request.query_params.get('source_type')
        search_query = self.request.query_params.get('search')
        
        if keyword_id:
            queryset = queryset.filter(keyword_id=keyword_id)
        
        if source_type and source_type != 'all':
            queryset = queryset.filter(source_type=source_type)
        
        if search_query:
            queryset = queryset.filter(
                title__icontains=search_query) | queryset.filter(
                snippet__icontains=search_query)
        
        return queryset.order_by('-published_date', '-created_at')
    
    # 백그라운드에서 연구 자료 수집 함수
    def _collect_research_in_background(self, keyword_id, user_id):
        try:
            # 태스크 상태 업데이트
            research_tasks[keyword_id] = {
                'status': 'running',
                'start_time': time.time(),
                'result': None,
                'error': None
            }
            
            # 연구 자료 수집 수행
            collector = ResearchCollector()
            result = collector.collect_and_save(keyword_id)
            
            # 성공 상태 업데이트
            research_tasks[keyword_id]['status'] = 'completed'
            research_tasks[keyword_id]['result'] = result
            research_tasks[keyword_id]['end_time'] = time.time()
            
            logger.info(f"키워드 ID {keyword_id}에 대한 연구 자료 수집 완료")
            
        except Exception as e:
            # 실패 상태 업데이트
            research_tasks[keyword_id]['status'] = 'failed'
            research_tasks[keyword_id]['error'] = str(e)
            research_tasks[keyword_id]['end_time'] = time.time()
            
            logger.error(f"키워드 ID {keyword_id}에 대한 연구 자료 수집 실패: {str(e)}")
    
    @action(detail=False, methods=['post'])
    def collect(self, request):
        keyword_id = request.data.get('keyword_id')
        
        if not keyword_id:
            return Response({"error": "keyword_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 키워드 확인
            keyword = Keyword.objects.get(id=keyword_id, user=request.user)
            
            # 이미 실행 중인 작업이 있는지 확인
            if keyword_id in research_tasks and research_tasks[keyword_id]['status'] == 'running':
                elapsed_time = time.time() - research_tasks[keyword_id]['start_time']
                
                # 30초 이상 실행 중이면 새로운 작업 시작
                if elapsed_time > 30:
                    research_tasks[keyword_id]['status'] = 'timeout'
                else:
                    return Response({
                        "message": "연구 자료 수집이 이미 진행 중입니다.",
                        "elapsed_seconds": int(elapsed_time)
                    })
            
            # 백그라운드 스레드에서 연구 자료 수집 시작
            thread = threading.Thread(
                target=self._collect_research_in_background,
                args=(keyword.pk, request.user.id)
            )
            thread.daemon = True
            thread.start()
            
            return Response({
                "message": "연구 자료 수집이 시작되었습니다. 상태를 확인하려면 /status/ 엔드포인트를 사용하세요.",
                "keyword_id": keyword_id
            })
                
        except Keyword.DoesNotExist:
            return Response({"error": "Invalid keyword_id"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        keyword_id = request.query_params.get('keyword_id')
        
        if not keyword_id:
            return Response({"error": "keyword_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 작업 상태 확인
        task_info = research_tasks.get(keyword_id)
        if not task_info:
            # 작업 정보가 없으면 연구 자료 존재 여부 확인
            try:
                keyword = Keyword.objects.get(id=keyword_id, user=request.user)
                sources_count = ResearchSource.objects.filter(keyword=keyword).count()
                
                if sources_count > 0:
                    return Response({
                        "status": "completed",
                        "message": "이미 연구 자료가 수집되어 있습니다.",
                        "sources_count": sources_count
                    })
                else:
                    return Response({
                        "status": "not_started",
                        "message": "연구 자료 수집이 시작되지 않았습니다."
                    })
            except Keyword.DoesNotExist:
                return Response({"error": "Invalid keyword_id"}, status=status.HTTP_404_NOT_FOUND)
        
        # 작업 상태에 따른 응답
        status_info = {
            "status": task_info['status'],
            "elapsed_seconds": int(time.time() - task_info['start_time']) if 'start_time' in task_info else 0
        }
        
        if task_info['status'] == 'completed':
            # 수집된 자료 수 추가
            result = task_info.get('result', {})
            status_info['data'] = {
                "news_count": len(result.get('news', [])),
                "academic_count": len(result.get('academic', [])),
                "general_count": len(result.get('general', [])),
                "statistics_count": len(result.get('statistics', []))
            }
        elif task_info['status'] == 'failed':
            status_info['error'] = task_info.get('error')
        
        return Response(status_info)
    
    @action(detail=False, methods=['post'])
    def duckduckgo(self, request):
        """
        DuckDuckGo 검색 API 엔드포인트
        """
        query = request.data.get('query')
        search_type = request.data.get('search_type', 'general')
        max_results = int(request.data.get('max_results', 5))
        
        if not query:
            return Response({"error": "query is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            duckduckgo_service = DuckDuckGoSearchService()
            results = duckduckgo_service.search(query, search_type, max_results)
            statistics = []
            for result in results:
                snippet = result.get('snippet', '')
                stats = duckduckgo_service.extract_statistics(snippet)
                if stats:
                    for stat in stats:
                        stat['source_url'] = result.get('url', '')
                        stat['source_title'] = result.get('title', '')
                    statistics.extend(stats)
            return Response({
                "search_results": results,
                "statistics": statistics
            })
        except Exception as e:
            logger.error(f"DuckDuckGo 검색 오류: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def collect_research(request):
    """연구 자료 수집 API - 백그라운드 방식으로 변경"""
    keyword_id = request.data.get('keyword_id')
    
    if not keyword_id:
        return Response({"error": "keyword_id is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # 키워드 확인
        keyword = Keyword.objects.get(id=keyword_id, user=request.user)
        
        # 이미 실행 중인 작업이 있는지 확인
        if keyword_id in research_tasks and research_tasks[keyword_id]['status'] == 'running':
            elapsed_time = time.time() - research_tasks[keyword_id]['start_time']
            
            # 30초 이상 실행 중이면 새로운 작업 시작
            if elapsed_time > 30:
                research_tasks[keyword_id]['status'] = 'timeout'
            else:
                return Response({
                    "message": "연구 자료 수집이 이미 진행 중입니다.",
                    "elapsed_seconds": int(elapsed_time)
                })
        
        # 백그라운드 스레드에서 연구 자료 수집 시작
        def _collect_in_background(keyword_id, user_id):
            try:
                # 태스크 상태 업데이트
                research_tasks[keyword_id] = {
                    'status': 'running',
                    'start_time': time.time(),
                    'result': None,
                    'error': None
                }
                
                # 연구 자료 수집 수행
                collector = ResearchCollector()
                result = collector.collect_and_save(keyword_id)
                
                # 성공 상태 업데이트
                research_tasks[keyword_id]['status'] = 'completed'
                research_tasks[keyword_id]['result'] = result
                research_tasks[keyword_id]['end_time'] = time.time()
                
                logger.info(f"키워드 ID {keyword_id}에 대한 연구 자료 수집 완료")
                
            except Exception as e:
                # 실패 상태 업데이트
                research_tasks[keyword_id]['status'] = 'failed'
                research_tasks[keyword_id]['error'] = str(e)
                research_tasks[keyword_id]['end_time'] = time.time()
                
                logger.error(f"키워드 ID {keyword_id}에 대한 연구 자료 수집 실패: {str(e)}")
        
        # 백그라운드 스레드 시작
        thread = threading.Thread(
            target=_collect_in_background,
            args=(keyword.pk, request.user.id)
        )
        thread.daemon = True
        thread.start()
        
        return Response({
            "message": "연구 자료 수집이 시작되었습니다. 상태를 확인하려면 /status/ 엔드포인트를 사용하세요.",
            "keyword_id": keyword_id
        })
            
    except Keyword.DoesNotExist:
        return Response({"error": "Invalid keyword_id"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def extract_statistics(request):
    """텍스트에서 통계 데이터 추출 API"""
    text = request.data.get('text')
    
    if not text:
        return Response({"error": "text is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        duckduckgo_service = DuckDuckGoSearchService()
        statistics = duckduckgo_service.extract_statistics(text)
        return Response({
            "statistics_count": len(statistics),
            "statistics": statistics
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

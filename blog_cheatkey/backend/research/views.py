from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ResearchSource, StatisticData
from key_word.models import Keyword
from .serializers import ResearchSourceSerializer, StatisticDataSerializer
from .services.collector import ResearchCollector

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
    
    @action(detail=False, methods=['post'])
    def collect(self, request):
        keyword_id = request.data.get('keyword_id')
        
        if not keyword_id:
            return Response({"error": "keyword_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 키워드 확인
            keyword = Keyword.objects.get(id=keyword_id, user=request.user)
            
            # 연구 자료 수집 서비스 초기화
            collector = ResearchCollector()
            
            # 수집 수행
            result = collector.collect_and_save(keyword.pk)
            
            if result:
                return Response({
                    "message": "연구 자료 수집이 완료되었습니다.",
                    "data": {
                        "news_count": len(result.get('news', [])),
                        "academic_count": len(result.get('academic', [])),
                        "general_count": len(result.get('general', [])),
                        "statistics_count": len(result.get('statistics', []))
                    }
                })
            else:
                return Response({"error": "연구 자료 수집에 실패했습니다."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Keyword.DoesNotExist:
            return Response({"error": "Invalid keyword_id"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StatisticDataViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StatisticDataSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = StatisticData.objects.filter(source__keyword__user=self.request.user)
        
        # 필터링
        keyword_id = self.request.query_params.get('keyword')
        
        if keyword_id:
            queryset = queryset.filter(source__keyword_id=keyword_id)
        
        return queryset

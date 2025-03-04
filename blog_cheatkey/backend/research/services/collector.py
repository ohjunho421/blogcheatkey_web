from django.conf import settings
from research.models import ResearchSource, StatisticData
from key_word.models import Keyword
from .search import GPTSearchService
import logging

logger = logging.getLogger(__name__)

class ResearchCollector:
    """
    연구 자료 수집 및 데이터베이스 저장 서비스
    """
    
    def __init__(self):
        self.search_service = GPTSearchService()
    
    def collect_and_save(self, keyword_id):
        """
        키워드 기반 연구 자료 수집 및 저장
        
        Args:
            keyword_id (int): 키워드 ID
            
        Returns:
            dict: 수집된 연구 자료 정보
        """
        try:
            # 키워드 및 소제목 정보 가져오기
            keyword_obj = Keyword.objects.get(id=keyword_id)
            keyword = keyword_obj.keyword
            subtopics = list(keyword_obj.subtopics.order_by('order').values_list('title', flat=True))
            
            # 기존 자료 삭제 (새로 수집)
            ResearchSource.objects.filter(keyword=keyword_obj).delete()
            
            # 연구 자료 수집
            research_data = self.search_service.collect_research(keyword, subtopics)
            
            # 수집된 자료 저장
            saved_data = {
                'news': [],
                'academic': [],
                'general': [],
                'statistics': []
            }
            
            # 뉴스 저장
            for item in research_data.get('news', []):
                source = ResearchSource.objects.create(
                    keyword=keyword_obj,
                    source_type='news',
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    snippet=item.get('snippet', ''),
                    author=item.get('source', ''),
                    published_date=item.get('date')
                )
                saved_data['news'].append(source.id)
            
            # 학술 자료 저장
            for item in research_data.get('academic', []):
                source = ResearchSource.objects.create(
                    keyword=keyword_obj,
                    source_type='academic',
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    snippet=item.get('snippet', ''),
                    author=item.get('source', ''),
                    published_date=item.get('date')
                )
                saved_data['academic'].append(source.id)
            
            # 일반 자료 저장
            for item in research_data.get('general', []):
                source = ResearchSource.objects.create(
                    keyword=keyword_obj,
                    source_type='general',
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    snippet=item.get('snippet', ''),
                    author=item.get('source', ''),
                    published_date=item.get('date')
                )
                saved_data['general'].append(source.id)
            
            # 통계 데이터 저장
            for item in research_data.get('statistics', []):
                # 해당 URL의 소스 찾기
                url = item.get('source_url', '')
                sources = ResearchSource.objects.filter(url=url, keyword=keyword_obj)
                
                if sources.exists():
                    source = sources.first()
                else:
                    # 소스가 없으면 새로 생성
                    source = ResearchSource.objects.create(
                        keyword=keyword_obj,
                        source_type='statistic',
                        title=item.get('source_title', '통계 자료'),
                        url=url,
                        snippet=item.get('context', ''),
                        author=item.get('source', ''),
                        published_date=item.get('date')
                    )
                
                # 통계 데이터 저장
                statistic = StatisticData.objects.create(
                    source=source,
                    value=item.get('value', ''),
                    context=item.get('context', ''),
                    pattern_type=item.get('pattern_type', '')
                )
                saved_data['statistics'].append(statistic.id)
            
            return saved_data
            
        except Keyword.DoesNotExist:
            logger.error(f"키워드 ID {keyword_id}를 찾을 수 없습니다.")
            return None
        except Exception as e:
            logger.error(f"연구 자료 수집 중 오류 발생: {str(e)}")
            return None
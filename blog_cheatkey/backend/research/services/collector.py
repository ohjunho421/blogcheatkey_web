import logging
import re
from datetime import datetime
from key_word.models import Keyword, Subtopic
from research.models import ResearchSource, StatisticData
from .perplexity_search import PerplexitySearchService

logger = logging.getLogger(__name__)

class ResearchCollector:
    """
    키워드와 소제목에 관련된 연구 자료를 수집하는 클래스
    """
    
    def __init__(self):
        # PerplexitySearchService 사용
        self.search_service = PerplexitySearchService()
    
    def collect_and_save(self, keyword_id):
        """
        키워드와 연관된 연구 자료를 수집하여 저장
        
        Args:
            keyword_id (int): 키워드 ID
            
        Returns:
            dict: 수집된 연구 자료 정보
        """
        try:
            # 키워드 정보 조회
            keyword = Keyword.objects.get(id=keyword_id)
            keyword_text = keyword.keyword
            
            # 소제목 목록 조회
            subtopics = list(Subtopic.objects.filter(
                keyword=keyword
            ).values_list('title', flat=True))
            
            # 연구 자료 수집
            logger.info(f"'{keyword_text}' 키워드에 대한 연구 자료 수집 시작")
            
            # PerplexitySearchService를 사용하여 자료 수집
            collected_data = self.search_service.collect_research(
                keyword_text, subtopics, limit_per_type=3
            )
            
            if not collected_data:
                logger.warning(f"'{keyword_text}' 키워드에 대한 연구 자료를 찾을 수 없습니다.")
                return None
            
            # 기존 연구 자료 삭제
            ResearchSource.objects.filter(keyword=keyword).delete()
            
            # 새로운 연구 자료 저장
            self._save_research_sources(keyword, collected_data)
            self._save_statistics(keyword, collected_data.get('statistics', []))
            
            logger.info(f"'{keyword_text}' 키워드에 대한 연구 자료 수집 완료")
            return collected_data
            
        except Keyword.DoesNotExist:
            logger.error(f"키워드 ID {keyword_id}를 찾을 수 없습니다.")
            return None
        except Exception as e:
            logger.error(f"연구 자료 수집 중 오류 발생: {str(e)}")
            return None
    
    def _format_date(self, date_str):
        """
        날짜 문자열을 YYYY-MM-DD 형식으로 변환
        
        Args:
            date_str (str): 변환할 날짜 문자열
            
        Returns:
            str or None: 변환된 날짜 문자열 또는 None
        """
        if not date_str:
            return None
            
        # 이미 YYYY-MM-DD 형식인 경우
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str
            
        # YYYY-MM 형식인 경우 (일을 01로 추가)
        if re.match(r'^\d{4}-\d{2}$', date_str):
            return f"{date_str}-01"
            
        # YYYY 형식인 경우 (월과 일을 01-01로 추가)
        if re.match(r'^\d{4}$', date_str):
            return f"{date_str}-01-01"
            
        try:
            # 다른 형식의 날짜 처리 (예: "Mar 18, 2025")
            dt = datetime.strptime(date_str, "%b %d, %Y")
            return dt.strftime("%Y-%m-%d")
        except:
            try:
                # 다른 형식 시도 (예: "18/03/2025")
                dt = datetime.strptime(date_str, "%d/%m/%Y")
                return dt.strftime("%Y-%m-%d")
            except:
                try:
                    # 또 다른 형식 시도 (예: "2025/03/18")
                    dt = datetime.strptime(date_str, "%Y/%m/%d")
                    return dt.strftime("%Y-%m-%d")
                except:
                    # 변환 실패시 None 반환
                    return None
    
    def _save_research_sources(self, keyword, collected_data):
        """
        수집된 연구 자료를 데이터베이스에 저장
        
        Args:
            keyword (Keyword): 키워드 객체
            collected_data (dict): 수집된 연구 자료
        """
        # 뉴스 자료 저장
        for item in collected_data.get('news', []):
            try:
                ResearchSource.objects.create(
                    keyword=keyword,
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    snippet=item.get('snippet', ''),
                    author=item.get('source', ''),
                    published_date=self._format_date(item.get('date')),
                    source_type='news'
                )
            except Exception as e:
                logger.error(f"뉴스 자료 저장 중 오류: {str(e)}")
                continue
        
        # 학술 자료 저장
        for item in collected_data.get('academic', []):
            try:
                ResearchSource.objects.create(
                    keyword=keyword,
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    snippet=item.get('snippet', ''),
                    author=item.get('source', ''),
                    published_date=self._format_date(item.get('date')),
                    source_type='academic'
                )
            except Exception as e:
                logger.error(f"학술 자료 저장 중 오류: {str(e)}")
                continue
        
        # 일반 자료 저장
        for item in collected_data.get('general', []):
            try:
                ResearchSource.objects.create(
                    keyword=keyword,
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    snippet=item.get('snippet', ''),
                    author=item.get('source', ''),
                    published_date=self._format_date(item.get('date')),
                    source_type='general'
                )
            except Exception as e:
                logger.error(f"일반 자료 저장 중 오류: {str(e)}")
                continue
    
    def _save_statistics(self, keyword, statistics_data):
        """
        수집된 통계 데이터를 데이터베이스에 저장
        
        Args:
            keyword (Keyword): 키워드 객체
            statistics_data (list): 수집된 통계 데이터
        """
        for stat in statistics_data:
            try:
                # 먼저 ResearchSource 객체 생성 또는 가져오기
                source, created = ResearchSource.objects.get_or_create(
                    keyword=keyword,
                    title=stat.get('source_title', ''),
                    url=stat.get('source_url', ''),
                    defaults={
                        'author': stat.get('source', ''),
                        'published_date': self._format_date(stat.get('date')),
                        'source_type': 'statistic',
                        'snippet': stat.get('context', '')[:500]
                    }
                )
                
                # 그 다음 StatisticData 생성
                StatisticData.objects.create(
                    source=source,
                    value=stat.get('value', ''),
                    context=stat.get('context', ''),
                    pattern_type=stat.get('pattern_type', 'numeric')
                )
            except Exception as e:
                logger.error(f"통계 데이터 저장 중 오류: {str(e)}")
                continue
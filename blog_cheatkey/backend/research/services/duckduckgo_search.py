# research/services/duckduckgo_search.py
import requests
import logging
import json
import re
import time
from datetime import datetime, timedelta
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

class DuckDuckGoSearchService:
    """
    DuckDuckGo 검색 API를 사용한 자료 수집 서비스
    """
    
    def __init__(self):
        self.base_url = "https://duckduckgo.com/html/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://duckduckgo.com/',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def search(self, query, search_type='general', max_results=5, timeout=30):
        """
        DuckDuckGo 검색 수행
        
        Args:
            query (str): 검색 쿼리
            search_type (str): 검색 유형 ('general', 'news', 'academic')
            max_results (int): 최대 결과 수
            timeout (int): 요청 타임아웃 (초)
            
        Returns:
            list: 검색 결과 목록
        """
        try:
            # 검색 유형에 따른 쿼리 수정
            formatted_query = query
            if search_type == 'news':
                formatted_query = f"{query} (site:news.com OR site:cnn.com OR site:bbc.com OR site:reuters.com OR site:bloomberg.com OR site:nytimes.com OR site:wsj.com)"
            elif search_type == 'academic':
                formatted_query = f"{query} (site:scholar.google.com OR site:researchgate.net OR site:academia.edu OR site:ncbi.nlm.nih.gov OR site:jstor.org)"
            
            # 요청 파라미터 설정
            params = {
                'q': formatted_query,
                'kl': 'kr-kr',  # 한국어 검색 (지역 설정)
                'ia': 'web'
            }
            
            # DuckDuckGo 검색 요청
            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=timeout
            )
            
            if response.status_code != 200:
                logger.error(f"DuckDuckGo 검색 실패: 상태 코드 {response.status_code}")
                return []
            
            # HTML 파싱
            results = self._parse_html_results(response.text, max_results)
            return results
            
        except Exception as e:
            logger.error(f"DuckDuckGo 검색 오류: {str(e)}")
            return []
    
    def _parse_html_results(self, html_content, max_results):
        """
        DuckDuckGo 검색 결과 HTML 파싱
        
        Args:
            html_content (str): HTML 콘텐츠
            max_results (int): 최대 결과 수
            
        Returns:
            list: 파싱된 검색 결과
        """
        results = []
        
        try:
            # 결과 항목 추출 (정규식 사용)
            result_pattern = r'<div class="result__body[^>]*>(.*?)<\/div>\s*<\/div>\s*<\/div>'
            items = re.findall(result_pattern, html_content, re.DOTALL)
            
            for item in items[:max_results]:
                result = {}
                
                # 제목 추출
                title_match = re.search(r'<a class="result__a[^>]*>(.*?)<\/a>', item, re.DOTALL)
                if title_match:
                    result['title'] = self._clean_html(title_match.group(1))
                
                # URL 추출
                url_match = re.search(r'<a class="result__a[^>]*href="([^"]+)"', item)
                if url_match:
                    result['url'] = url_match.group(1)
                
                # 스니펫 추출
                snippet_match = re.search(r'<a[^>]*class="result__snippet"[^>]*>(.*?)<\/a>', item, re.DOTALL)
                if snippet_match:
                    result['snippet'] = self._clean_html(snippet_match.group(1))
                
                # 출처 도메인 추출
                domain_match = re.search(r'<a[^>]*class="result__url"[^>]*>(.*?)<\/a>', item, re.DOTALL)
                if domain_match:
                    result['source'] = self._clean_html(domain_match.group(1))
                
                # 모든 필수 필드가 있는 경우만 결과에 추가
                if 'title' in result and 'url' in result and 'snippet' in result:
                    # 날짜 추정 (스니펫에서 날짜 형식 찾기)
                    date_match = re.search(r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', result.get('snippet', ''))
                    if date_match:
                        result['date'] = date_match.group(1)
                    else:
                        # 현재 날짜 사용
                        result['date'] = datetime.now().strftime('%Y-%m-%d')
                    
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"HTML 파싱 오류: {str(e)}")
            return []
    
    def _clean_html(self, text):
        """
        HTML 태그 제거 및 텍스트 정리
        
        Args:
            text (str): 정리할 텍스트
            
        Returns:
            str: 정리된 텍스트
        """
        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', '', text)
        
        # HTML 엔티티 디코딩
        text = text.replace('&quot;', '"').replace('&apos;', "'").replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        
        # 연속된 공백 정리
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def extract_statistics(self, text):
        """
        텍스트에서 통계 데이터 (숫자, 퍼센트 등) 추출
        
        Args:
            text (str): 분석할 텍스트
            
        Returns:
            list: 추출된 통계 데이터 목록
        """
        statistics = []
        
        # 숫자/퍼센트 패턴
        patterns = [
            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:%|퍼센트|명|개|원|달러|위|배|천|만|억)',  # 한글 단위
            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:people|users|dollars|percent|%)',  # 영문 단위
            r'(\d+(?:\.\d+)?)[%％]'  # 퍼센트 기호
        ]
        
        try:
            for pattern in patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    # 통계 데이터의 전후 문맥 추출 (최대 100자)
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end].strip()
                    
                    statistics.append({
                        'value': match.group(0),
                        'context': context,
                        'pattern_type': 'numeric' if '%' not in match.group(0) else 'percentage'
                    })
            
            return statistics
            
        except Exception as e:
            logger.error(f"통계 데이터 추출 오류: {str(e)}")
            return []
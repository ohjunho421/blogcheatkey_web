import re
import json
import logging
import requests
from datetime import datetime, timedelta
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

class GPTSearchService:
    """
    OpenAI의 GPT API를 사용한 웹 검색 서비스
    기존 코드의 Perplexity, Serper, Tavily API 대신 GPT를 사용
    """
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o"  # 웹 브라우징 가능한 모델 사용
    
    def search_with_gpt(self, query, search_type='general', limit=3):
        """
        GPT를 사용하여 웹 검색 수행
        
        Args:
            query (str): 검색 쿼리
            search_type (str): 검색 유형 (general, news, academic)
            limit (int): 결과 최대 수
            
        Returns:
            list: 검색 결과 목록
        """
        try:
            # 검색 유형에 따른 시스템 프롬프트 설정
            system_prompts = {
                'general': "웹에서 다음 검색어에 대한 정보를 검색해서 결과를 제공해주세요. 반드시 URL과 제목, 간략한 내용을 제공해 주세요.",
                'news': "웹에서 다음 검색어에 관련된 최신 뉴스 기사를 검색해주세요. 최근 1년 내의 뉴스만 검색하고, 각 결과에 URL, 제목, 출처, 게시일, 간략한 내용을 포함해주세요.",
                'academic': "웹에서 다음 검색어에 관련된 학술 자료나 연구 논문을 검색해주세요. 각 결과에 URL, 제목, 저자, 발행일(알 수 있다면), 간략한 내용을 포함해주세요.",
                'statistics': "웹에서 다음 검색어에 관련된 통계 자료와 수치 데이터를 검색해주세요. 숫자와 퍼센트가 포함된 내용을 우선적으로 찾아주세요. 각 통계 데이터의 출처와 URL, 관련 맥락도 함께 제공해주세요."
            }
            
            # 검색 유형에 따른 사용자 메시지 조정
            search_type_text = {
                'general': "",
                'news': "최신 뉴스 기사만 찾아주세요. 1년 이내의 자료만 검색하세요.",
                'academic': "학술 자료, 연구 논문, 학술지 게시글만 찾아주세요.",
                'statistics': "통계 자료, 수치 데이터, 퍼센트 정보가 포함된 내용을 찾아주세요."
            }
            
            # 결과 형식 지정
            format_instruction = f"""
            결과는 반드시 다음 JSON 형식으로 제공해주세요:
            ```json
            [
                {{
                    "title": "제목",
                    "url": "URL",
                    "snippet": "내용 요약 (200자 이내)",
                    "source": "출처/사이트 이름",
                    "date": "YYYY-MM-DD" (알 수 있는 경우)
                }},
                // 최대 {limit}개의 결과
            ]
            ```
            
            JSON 형식을 엄격하게 지켜주세요. 다른 설명은 제공하지 말고 JSON만 응답해주세요.
            """
            
            # 메시지 구성
            messages = [
                {"role": "system", "content": system_prompts.get(search_type, system_prompts['general'])},
                {"role": "user", "content": f"'{query}'에 대해 검색해주세요. {search_type_text.get(search_type, '')} {format_instruction}"}
            ]
            
            # API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,  # 정확한 정보 검색을 위해 낮은 온도 사용
                response_format={"type": "json_object"}
            )
            
            # 응답에서 JSON 추출
            content = response.choices[0].message.content
            content = content.strip()
            
            # JSON 포맷 추출
            if "```json" in content:
                json_content = content.split("```json")[1].split("```")[0].strip()
            else:
                json_content = content
                
            results = json.loads(json_content)
            
            # 결과가 리스트가 아닌 경우 변환
            if not isinstance(results, list):
                if "results" in results:
                    results = results["results"]
                else:
                    results = [results]
            
            # 결과 제한
            results = results[:limit]
            
            return results
            
        except Exception as e:
            logger.error(f"GPT 검색 서비스 오류: {str(e)}")
            return []
    
    def extract_statistics(self, text):
        """
        텍스트에서 통계 데이터 (숫자, 퍼센트 등) 추출
        
        Args:
            text (str): 분석할 텍스트
            
        Returns:
            list: 추출된 통계 데이터 목록
        """
        try:
            statistics = []
            
            # 숫자/퍼센트 패턴
            patterns = [
                r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:명|개|원|달러|위|배|천|만|억|%|퍼센트)',  # 한글 단위
                r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:people|users|dollars|percent|%)',  # 영문 단위
                r'(\d+(?:\.\d+)?)[%％]'  # 퍼센트 기호
            ]
            
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

    def collect_research(self, keyword, subtopics, limit_per_type=3):
        """
        키워드와 소제목 관련 연구 자료 수집
        
        Args:
            keyword (str): 키워드
            subtopics (list): 소제목 목록
            limit_per_type (int): 각 유형별 최대 결과 수
            
        Returns:
            dict: 수집된 연구 자료
        """
        all_results = {
            'news': [],
            'academic': [],
            'general': [],
            'statistics': []
        }
        
        # 1. 기본 키워드 검색 수행
        base_queries = [
            f"{keyword} 통계",
            f"{keyword} 연구결과",
            f"{keyword} 최신 동향"
        ]
        
        for query in base_queries:
            news_results = self.search_with_gpt(query, 'news', limit=1)
            academic_results = self.search_with_gpt(query, 'academic', limit=1)
            stats_results = self.search_with_gpt(query, 'statistics', limit=1)
            
            all_results['news'].extend(news_results)
            all_results['academic'].extend(academic_results)
            all_results['general'].extend(stats_results)
            
            # 통계 데이터 추출
            for result in news_results + academic_results + stats_results:
                snippet = result.get('snippet', '')
                statistics = self.extract_statistics(snippet)
                
                for stat in statistics:
                    stat['source_url'] = result.get('url', '')
                    stat['source_title'] = result.get('title', '')
                    stat['source'] = result.get('source', '')
                    stat['date'] = result.get('date', '')
                    
                all_results['statistics'].extend(statistics)
        
        # 2. 소제목 검색
        for subtopic in subtopics:
            subtopic_query = f"{keyword} {subtopic}"
            
            # 소제목별로 적은 수의 결과만 가져와 전체 검색 횟수 최소화
            if len(all_results['news']) < limit_per_type:
                news = self.search_with_gpt(subtopic_query, 'news', limit=1)
                all_results['news'].extend(news)
                
            if len(all_results['academic']) < limit_per_type:
                academic = self.search_with_gpt(subtopic_query, 'academic', limit=1)
                all_results['academic'].extend(academic)
        
        # 3. 중복 제거 및 정렬
        for category in all_results:
            all_results[category] = self._deduplicate_results(all_results[category])
            # 날짜 기준 정렬 (최신순)
            if category in ['news', 'academic', 'general']:
                all_results[category].sort(
                    key=lambda x: x.get('date', ''),
                    reverse=True
                )
            # 각 카테고리별 최대 결과 수 제한
            all_results[category] = all_results[category][:limit_per_type]
        
        return all_results
    
    def _deduplicate_results(self, results):
        """
        중복 결과 제거
        
        Args:
            results (list): 결과 목록
            
        Returns:
            list: 중복 제거된 결과 목록
        """
        return list({result.get('url', ''): result for result in results if result.get('url')}.values())


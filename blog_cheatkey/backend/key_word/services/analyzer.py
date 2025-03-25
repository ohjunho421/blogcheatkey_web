# keyword/services/analyzer.py
import logging
import json
import re
from django.conf import settings
from openai import OpenAI

# from research.services.collector import ResearchCollector 제거 (순환 참조 방지)

logger = logging.getLogger(__name__)

class KeywordAnalyzer:
    """
    OpenAI의 GPT API를 사용한 키워드 분석 서비스
    기존 코드의 Perplexity API 대신 OpenAI API 사용
    """
    
    def __init__(self):
        import os
        os.environ.pop('http_proxy', None)
        os.environ.pop('https_proxy', None)
        
        from dotenv import load_dotenv
        import pathlib
        
        backend_dir = pathlib.Path(__file__).parent.parent.parent
        env_path = os.path.join(backend_dir, '.env')
        load_dotenv(dotenv_path=env_path)
        
        self.api_key = os.environ.get('OPENAI_API_KEY')
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o"
    
    def analyze_keyword(self, keyword):
        """
        키워드 분석 수행
        
        Args:
            keyword (str): 분석할 키워드
            
        Returns:
            dict: 분석 결과
        """
        try:
            # 시스템 프롬프트 설정
            system_prompt = "당신은 SEO 및 콘텐츠 마케팅 전문가입니다. 키워드를 분석하여 구체적이고 실용적인 정보를 제공해야 합니다."
            
            # 프롬프트 생성
            prompt = f"""
            다음 키워드를 SEO 관점에서 분석해주세요:
            키워드: {keyword}

            다음 형식으로 분석 결과를 제공해주세요:

            1. 주요 검색 의도: 
            (2-3문장으로 이 키워드를 검색하는 사람들의 주요 의도를 설명해주세요)

            2. 검색자가 얻고자 하는 정보:
            (가장 중요한 3가지만 bullet point로 작성해주세요)
            - 
            - 
            - 

            3. 검색자가 겪고 있는 불편함이나 어려움:
            (가장 일반적인 3가지 어려움만 bullet point로 작성해주세요)
            - 
            - 
            - 
            """
            
            # API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
            )
            
            content = response.choices[0].message.content
            return self._parse_analysis_result(content)
            
        except Exception as e:
            logger.error(f"키워드 분석 중 오류 발생: {str(e)}")
            raise
    
    def suggest_subtopics(self, keyword):
        """
        키워드 기반 소제목 추천
        
        Args:
            keyword (str): 키워드
            
        Returns:
            list: 추천 소제목 목록
        """
        try:
            # 시스템 프롬프트 설정
            system_prompt = "당신은 블로그 콘텐츠 구조화 전문가입니다. 제공된 키워드를 바탕으로 논리적이고 포괄적인 소제목을 추천해야 합니다."
            
            # 프롬프트 생성
            prompt = f"""
            검색 키워드 '{keyword}'에 대한 블로그 소제목 4개를 추천해주세요.

            조건:
            1. 모든 소제목은 반드시 '{keyword}'와 직접적으로 관련되어야 함
            2. 소제목들은 논리적 순서로 구성
            3. 각 소제목은 검색자의 실제 고민/궁금증을 해결할 수 있는 내용
            4. 전체적으로 '{keyword}'에 대한 포괄적 이해를 제공할 수 있는 구성
            

            형식:
            1. [첫 번째 소제목]: {keyword} 중요성
            2. [두 번째 소제목]: 주요 정보/특징
            3. [세 번째 소제목]: 실용적 팁/방법
            4. [네 번째 소제목]: 선택/관리 방법
            """
            
            # API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
            
            content = response.choices[0].message.content
            return self._parse_subtopics(content)
            
        except Exception as e:
            logger.error(f"소제목 추천 중 오류 발생: {str(e)}")
            raise
    
    # 이 메서드 추가
    def collect_research_materials(self, keyword_id):
        """
        키워드 관련 연구 자료 수집 (ResearchCollector 사용)
        
        Args:
            keyword_id (int): 키워드 ID
            
        Returns:
            dict: 수집된 연구 자료 정보
        """
        # 필요한 시점에 임포트하여 순환 참조 방지
        from research.services.collector import ResearchCollector
        
        try:
            collector = ResearchCollector()
            result = collector.collect_and_save(keyword_id)
            return result
        except Exception as e:
            logger.error(f"연구 자료 수집 중 오류 발생: {str(e)}")
            return None
    
    def _parse_analysis_result(self, content):
        """
        분석 결과 파싱
        
        Args:
            content (str): API 응답 내용
            
        Returns:
            dict: 파싱된 분석 결과
        """
        # 섹션별 내용 추출
        sections = content.split('\n\n')
        main_intent = ""
        info_needed = []
        pain_points = []
        
        for section in sections:
            if '1. 주요 검색 의도:' in section:
                main_intent = section.split('주요 검색 의도:')[1].strip()
            elif '2. 검색자가 얻고자 하는 정보:' in section:
                info_lines = section.split('\n')[1:]
                info_needed = [line.strip('- ').strip() for line in info_lines if line.strip().startswith('-')]
            elif '3. 검색자가 겪고 있는 불편함이나 어려움:' in section:
                pain_lines = section.split('\n')[1:]
                pain_points = [line.strip('- ').strip() for line in pain_lines if line.strip().startswith('-')]
        
        return {
            'raw_text': content,
            'main_intent': main_intent,
            'info_needed': info_needed,
            'pain_points': pain_points
        }
    
    def _parse_subtopics(self, content):
        """
        소제목 파싱
        
        Args:
            content (str): API 응답 내용
            
        Returns:
            list: 파싱된 소제목 목록
        """
        subtopics = []
        
        for line in content.split('\n'):
            if line.strip() and line[0].isdigit() and '. ' in line:
                subtitle = line.split('. ', 1)[1].strip()
                if ':' in subtitle:
                    subtitle = subtitle.split(':', 1)[1].strip()
                if subtitle:
                    subtopics.append(subtitle)
        
        return subtopics[:4]  # 최대 4개의 소제목만 반환
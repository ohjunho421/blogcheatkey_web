# title/services/generator.py
import re
import logging
from anthropic import Anthropic
from openai import OpenAI
from django.conf import settings
from content.models import BlogContent
from title.models import TitleSuggestion
import time

logger = logging.getLogger(__name__)

class TitleGenerator:
    """
    블로그 콘텐츠 기반 제목 생성 서비스
    """
    
    TITLE_TYPES = {
        'general': '일반 상식 반박형',
        'approval': '인정욕구 자극형',
        'secret': '숨겨진 비밀형',
        'trend': '트렌드 제시형',
        'failure': '실패담 공유형',
        'comparison': '비교형',
        'warning': '경고형',
        'blame': '남탓 공감형',
        'beginner': '초보자 가이드형',
        'benefit': '효과 제시형'
    }
    
    def __init__(self, use_openai=True):
        """
        제목 생성 서비스 초기화
        
        Args:
            use_openai (bool): OpenAI API 사용 여부 (False면 Claude API 사용)
        """
        self.use_openai = use_openai
        
        if use_openai:
            self.openai_api_key = settings.OPENAI_API_KEY
            self.client = OpenAI(api_key=self.openai_api_key)
            self.model = "gpt-4"  # GPT-4 사용
        else:
            self.anthropic_api_key = settings.ANTHROPIC_API_KEY
            self.client = Anthropic(api_key=self.anthropic_api_key)
            self.model = "claude-3-7-sonnet-20250219"  # Claude 최신 모델 사용
        
        # 재시도 설정
        self.max_retries = 3
        self.retry_delay = 2
    
    def generate_titles(self, content_id):
        """
        블로그 콘텐츠 기반 제목 생성
        모든 유형의 제목을 생성하여 저장
        
        Args:
            content_id (int): BlogContent 모델의 ID
            
        Returns:
            dict: 생성된 제목 정보
        """
        for attempt in range(self.max_retries):
            try:
                # 블로그 콘텐츠 정보 가져오기
                blog_content = BlogContent.objects.get(id=content_id)
                keyword = blog_content.keyword.keyword
                content = blog_content.content
                
                # 이미 생성된 제목이 있는지 확인
                existing_titles = TitleSuggestion.objects.filter(content=blog_content)
                if existing_titles.exists():
                    # 이미 생성된 제목이 있으면 그대로 반환
                    titles = {}
                    for title_type in self.TITLE_TYPES.keys():
                        type_titles = existing_titles.filter(title_type=title_type)
                        titles[title_type] = [
                            {
                                'id': t.id,
                                'title': t.suggestion
                            } for t in type_titles
                        ]
                    
                    # 선택된 제목이 있으면 콘텐츠의 제목으로 설정
                    selected_title = existing_titles.filter(selected=True).first()
                    if selected_title:
                        blog_content.title = selected_title.suggestion
                        blog_content.save()
                    
                    return titles
                
                # 기존 제목 제안 삭제
                TitleSuggestion.objects.filter(content=blog_content).delete()
                
                # 제목 생성
                titles = {}
                all_titles = self._generate_title_suggestions(keyword, content)
                
                # 각 유형별 제목 저장
                for title_type, title_suggestions in all_titles.items():
                    titles[title_type] = []
                    
                    for suggestion in title_suggestions:
                        title = TitleSuggestion.objects.create(
                            content=blog_content,
                            title_type=title_type,
                            suggestion=suggestion
                        )
                        titles[title_type].append({
                            'id': title.id,
                            'title': suggestion
                        })
                
                # 첫 번째 제목을 콘텐츠의 제목으로 설정
                if titles and titles.get('general') and titles['general']:
                    blog_content.title = titles['general'][0]['title']
                    blog_content.save()
                
                return titles
                
            except BlogContent.DoesNotExist:
                logger.error(f"블로그 콘텐츠 ID {content_id}를 찾을 수 없습니다.")
                return None
            except Exception as e:
                logger.error(f"제목 생성 중 오류 (시도 {attempt+1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    # 재시도 지연 시간 계산 (지수 백오프)
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"{delay}초 후 재시도합니다...")
                    time.sleep(delay)
                else:
                    # 모든 재시도 실패
                    logger.error("최대 재시도 횟수를 초과했습니다.")
                    return None
    
    def _generate_title_suggestions(self, keyword, content):
        """
        키워드와 콘텐츠 기반 제목 추천 생성
        
        Args:
            keyword (str): 키워드
            content (str): 블로그 콘텐츠
            
        Returns:
            dict: 유형별 제목 추천 목록
        """
        try:
            # 콘텐츠에서 주요 정보 추출
            extracted_info = self._extract_key_info(content)
            
            # 프롬프트 생성
            prompt = self._create_title_prompt(keyword, extracted_info)
            
            # API에 따른 응답 생성
            if self.use_openai:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "당신은 상위 1%의 블로그 제목 생성 전문가입니다. SEO에 최적화되면서도 독자의 클릭을 유도하는 매력적인 제목을 생성해야 합니다."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    timeout=120  # 타임아웃 추가 (120초)
                )
                
                response_text = response.choices[0].message.content
            else:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1500,
                    temperature=0.7,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                response_text = response.content[0].text
            
            # 응답 파싱
            return self._parse_title_response(response_text)
        
        except Exception as e:
            logger.error(f"제목 추천 생성 중 오류: {str(e)}")
            # 오류 발생 시 기본 제목 목록 반환
            default_titles = {}
            for title_type in self.TITLE_TYPES.keys():
                if title_type == 'general':
                    default_titles[title_type] = [f"{keyword} 완벽 가이드", f"{keyword} 기본 원리", f"{keyword} 마스터하기"]
                else:
                    default_titles[title_type] = [f"{keyword} 알아보기", f"{keyword} 이해하기", f"{keyword} 분석"]
            
            return default_titles
    
    def _extract_key_info(self, content):
        """
        콘텐츠에서 주요 정보 추출
        
        Args:
            content (str): 블로그 콘텐츠
            
        Returns:
            dict: 추출된 주요 정보
        """
        # 소제목 추출
        subtopic_pattern = r'###\s+(.*?)\n'
        subtopics = re.findall(subtopic_pattern, content)
        
        # 통계 데이터 추출 (숫자, 퍼센트 등)
        stats_pattern = r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:%|퍼센트|명|개|원|달러|위|배|천|만|억)'
        statistics = re.findall(stats_pattern, content)
        
        # 주요 키워드 추출 (고유명사, 전문 용어 등)
        # 간단한 추출을 위해 소제목에서 추출
        keywords = []
        for subtopic in subtopics:
            words = subtopic.split()
            for word in words:
                if len(word) >= 2 and word not in ['그리고', '또한', '그러나', '하지만', '이것', '저것', '그것']:
                    keywords.append(word)
        
        return {
            'subtopics': subtopics[:4],  # 최대 4개만 추출
            'statistics': statistics[:5],  # 최대 5개만 추출
            'keywords': list(set(keywords))[:10]  # 중복 제거 후 최대 10개만 추출
        }
    
    def _create_title_prompt(self, keyword, extracted_info):
        """
        제목 생성 프롬프트 생성
        
        Args:
            keyword (str): 키워드
            extracted_info (dict): 추출된 주요 정보
            
        Returns:
            str: 제목 생성 프롬프트
        """
        subtopics = extracted_info.get('subtopics', [])
        statistics = extracted_info.get('statistics', [])
        keywords = extracted_info.get('keywords', [])
        
        prompt = f"""
        다음 키워드와 관련 정보를 바탕으로 10가지 유형의 블로그 제목을 각 유형별로 3개씩 생성해주세요.
        
        키워드: {keyword}
        
        관련 정보:
        - 소제목: {', '.join(subtopics) if subtopics else '정보 없음'}
        - 통계 데이터: {', '.join(statistics) if statistics else '정보 없음'}
        - 주요 키워드: {', '.join(keywords) if keywords else '정보 없음'}
        
        제목 유형별 특징:
        1. 일반 상식 반박형 (general) - 기존의 상식이나 고정관념을 반박하는 제목
           예시: "아직도 {keyword}는 [일반적 상식]라고 생각하시나요?"
        
        2. 인정욕구 자극형 (approval) - 독자의 인정 욕구를 자극하는 제목
           예시: "'이것' 확인할 줄 안다면 {keyword} 전문가입니다"
        
        3. 숨겨진 비밀형 (secret) - 전문가만 아는 비밀을 알려주는 제목
           예시: "{keyword} 전문가들이 몰래 사용하는 방법 TOP3"
        
        4. 트렌드 제시형 (trend) - 현재 트렌드를 제시하는 제목
           예시: "요즘은 {keyword}보다 '이것'이 대세입니다"
        
        5. 실패담 공유형 (failure) - 실패 경험을 공유하는 제목
           예시: "{keyword} 잘못 선택해서 후회한 사람들의 공통점"
        
        6. 비교형 (comparison) - 전후 비교나 대안 비교를 제시하는 제목
           예시: "{keyword} 전후 비교! 차이가 이렇게 납니다"
        
        7. 경고형 (warning) - 주의사항이나 경고를 제시하는 제목
           예시: "{keyword} 전에 꼭 알아야 할 5가지 체크리스트"
        
        8. 남탓 공감형 (blame) - 외부 요인을 탓하며 공감을 이끌어내는 제목
           예시: "{keyword} 후에도 효과가 없다면 [외부 요인] 때문입니다"
        
        9. 초보자 가이드형 (beginner) - 초보자를 위한 가이드 제목
           예시: "{keyword} 초보라면 이렇게 시작하세요"
        
        10. 효과 제시형 (benefit) - 기대 효과를 명확히 제시하는 제목
            예시: "{keyword}만 잘해도 [효과] 15% 올라가는 이유"
        
        응답 형식:
        ```
        {{일반 상식 반박형}}
        1. [제목1]
        2. [제목2]
        3. [제목3]
        
        {{인정욕구 자극형}}
        1. [제목1]
        2. [제목2]
        3. [제목3]
        
        ...계속...
        ```
        
        다음 조건을 반드시 준수해주세요:
        1. 각 유형별로 정확히 3개의 제목을 생성해주세요.
        2. 제목은 클릭을 유도하면서도 과장되거나 허위 정보를 담지 않도록 해주세요.
        3. 각 제목에 키워드 '{keyword}'를 반드시 포함시켜주세요.
        4. 제목 길이는 한글 기준 15-30자 사이로 해주세요.
        5. 추출된 통계 데이터나 키워드를 적절히 활용해주세요.
        """
        
        return prompt
    
    def _parse_title_response(self, response_text):
        """
        API 응답에서 제목 추천 파싱
        
        Args:
            response_text (str): API 응답 텍스트
            
        Returns:
            dict: 유형별 제목 추천 목록
        """
        titles = {
            'general': [],
            'approval': [],
            'secret': [],
            'trend': [],
            'failure': [],
            'comparison': [],
            'warning': [],
            'blame': [],
            'beginner': [],
            'benefit': []
        }
        
        # 응답에서 유형별 제목 추출
        title_sections = response_text.split('\n\n')
        
        current_type = None
        for section in title_sections:
            # 유형 섹션 시작 확인
            for title_type, type_name in self.TITLE_TYPES.items():
                if section.strip().startswith(f'{{{type_name}}}') or section.strip().startswith(f'{type_name}'):
                    current_type = title_type
                    break
            
            # 번호가 매겨진 제목 추출
            if current_type:
                lines = section.split('\n')
                for line in lines:
                    if re.match(r'^\d+\.', line.strip()):
                        title = line.strip().split('. ', 1)[-1].strip()
                        if title:
                            # 제목에서 따옴표 제거
                            title = title.strip('"\'')
                            titles[current_type].append(title)
        
        # 각 유형별 결과 개수 확인 및 보완
        for title_type in titles:
            # 유형별 제목이 없는 경우 기본값 설정
            if not titles[title_type]:
                titles[title_type] = self._get_default_titles(title_type)
            # 최대 3개로 제한
            titles[title_type] = titles[title_type][:3]
        
        return titles
    
    def _get_default_titles(self, title_type):
        """
        특정 유형의 기본 제목 생성
        
        Args:
            title_type (str): 제목 유형
            
        Returns:
            list: 기본 제목 목록
        """
        defaults = {
            'general': ["아직도 이렇게 하시나요? 올바른 방법 알아보기", "일반적인 상식과 다른 진실", "대부분의 사람들이 잘못 알고 있는 것"],
            'approval': ["전문가들만 아는 비밀 기술", "당신이 모르는 숨겨진 팁", "이것을 알고 있다면 당신은 전문가!"],
            'secret': ["전문가들이 알려주지 않는 비밀", "숨겨진 팁으로 효과 두 배로!", "아무도 알려주지 않았던 비밀 노하우"],
            'trend': ["2024년 최신 트렌드 총정리", "요즘 대세는 이것! 놓치지 마세요", "트렌드를 선도하는 최신 방법"],
            'failure': ["실패한 사람들의 공통된 습관", "이것 때문에 실패했다! 피해야 할 함정", "후회하지 않으려면 이 실수들을 피하세요"],
            'comparison': ["전과 후, 확실한 차이 비교", "어떤 방법이 더 효과적일까? 비교 분석", "A vs B: 어떤 것이 더 좋을까?"],
            'warning': ["반드시 알아야 할 5가지 주의사항", "이것만은 꼭 피하세요! 위험 신호", "시작하기 전에 꼭 확인해야 할 체크리스트"],
            'blame': ["효과가 없는 진짜 이유, 당신 탓이 아닙니다", "실패의 원인은 외부에 있었다", "당신의 노력이 헛되게 느껴지는 진짜 이유"],
            'beginner': ["초보자를 위한 완벽 가이드", "처음 시작하는 분들을 위한 기초 팁", "초보자도 쉽게 따라할 수 있는 방법"],
            'benefit': ["이것만 바꿔도 효과 30% 상승", "단 7일만에 놀라운 변화를 경험하세요", "손쉽게 얻을 수 있는 5가지 핵심 효과"]
        }
        
        # 기본값에 없는 유형이면 일반형 반환
        return defaults.get(title_type, defaults['general'])
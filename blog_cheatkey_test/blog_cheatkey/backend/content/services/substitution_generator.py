import re
import json
import logging
import time
import traceback
from konlpy.tag import Okt
from anthropic import Anthropic
from django.conf import settings

logger = logging.getLogger(__name__)

class SubstitutionGenerator:
    """
    키워드와 형태소에 대한 대체어를 완전히 동적으로 생성하는 클래스
    """
    
    def __init__(self):
        self.anthropic_api_key = settings.ANTHROPIC_API_KEY
        self.model = "claude-3-7-sonnet-20250219"
        self.client = Anthropic(api_key=self.anthropic_api_key)
        self.okt = Okt()
        
        # 캐시 - 키워드/형태소에 대한 대체어 목록을 저장
        self.substitution_cache = {}
    
    def get_substitutions(self, keyword, morpheme=None):
        """
        키워드 또는 특정 형태소에 대한 대체어 목록 반환
        
        Args:
            keyword (str): 주요 키워드
            morpheme (str, optional): 대체어를 찾을 형태소. None이면 키워드에 대한 대체어 생성
            
        Returns:
            list: 대체어 목록
        """
        # 이미 캐시에 있는지 확인
        cache_key = f"{keyword}:{morpheme}" if morpheme else keyword
        
        if cache_key in self.substitution_cache:
            return self.substitution_cache[cache_key]
        
        # API를 이용한 동적 대체어 생성
        try:
            dynamic_substitutions = self._generate_dynamic_substitutions(keyword, morpheme)
            
            # 자연스러운 지시어는 항상 포함시키기
            common_pronouns = ["이것", "이", "해당 항목", "이 주제", "그것"]
            
            # 이미 포함된 지시어가 있는지 확인
            has_pronoun = any(pronoun in dynamic_substitutions for pronoun in common_pronouns)
            
            # 지시어가 없으면 추가
            if not has_pronoun:
                dynamic_substitutions = dynamic_substitutions + common_pronouns[:3]
            
            self.substitution_cache[cache_key] = dynamic_substitutions
            return dynamic_substitutions
        except Exception as e:
            logger.error(f"대체어 생성 중 오류 발생: {str(e)}")
            # 오류 발생 시 기본 대체어 리스트 제공
            default_substitutions = self._get_default_substitutions(keyword, morpheme)
            self.substitution_cache[cache_key] = default_substitutions
            return default_substitutions
    
    def _get_default_substitutions(self, keyword, morpheme=None):
        """
        API 호출 실패 시 제공할 기본 대체어 목록
        
        Args:
            keyword (str): 주요 키워드
            morpheme (str, optional): 대체어를 찾을 형태소
            
        Returns:
            list: 기본 대체어 목록
        """
        target_term = morpheme if morpheme else keyword
        
        # 키워드/형태소가 명사인지 확인
        is_noun = False
        try:
            pos_tagged = self.okt.pos(target_term)
            is_noun = any(tag.startswith('N') for _, tag in pos_tagged)
        except:
            is_noun = True  # 확인할 수 없으면 명사로 취급
        
        if is_noun:
            return ["이것", "이", "해당 항목", "이 주제", "그것", "해당 제품", "이 분야", "이 항목"]
        else:
            return ["이렇게", "이런 방식으로", "이와 같이", "그렇게", "이러한 방식으로"]
    
    def _generate_dynamic_substitutions(self, keyword, morpheme=None):
        """
        Claude API를 사용하여 키워드 또는 형태소에 대한 대체어를 동적으로 생성
        
        Args:
            keyword (str): 주요 키워드
            morpheme (str, optional): 대체어를 찾을 형태소
            
        Returns:
            list: 대체어 목록
        """
        target_term = morpheme if morpheme else keyword
        
        prompt = f"""
        다음 단어의 동의어, 유사어, 대체 표현을 10개 제시해 주세요:
        
        단어: {target_term}
        키워드 컨텍스트: {keyword}
        
        추가 컨텍스트: 이 단어는 블로그 글에서 자주 반복되어 대체어가 필요합니다. 
        대체어는 문맥상 자연스럽게 사용될 수 있는 표현이어야 합니다.
        
        블로그 글의 주제와 관련된 구체적인 동의어/유사어와 일반적인 대체 표현을 모두 포함해 주세요:
        - 직접적인 동의어/유사어
        - 특정 맥락에서 대체 가능한 단어
        - 지시어(이것, 이, 해당 등)
        
        JSON 형식으로 반환해주세요: ["대체어1", "대체어2", ...]
        """
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.content[0].text
            
            # JSON 패턴 찾기
            json_pattern = r'\[.*?\]'
            json_matches = re.findall(json_pattern, content, re.DOTALL)
            
            if json_matches:
                try:
                    substitutions = json.loads(json_matches[0])
                    # 최대 10개만 사용
                    return substitutions[:10]
                except json.JSONDecodeError:
                    pass
            
            # JSON 파싱 실패 시 대체어 직접 추출
            # "- ", "* " 또는 숫자로 시작하는 목록 항목 추출
            item_pattern = r'(?:^|\n)(?:[-*]|\d+\.)\s*([^:\n]+?)(?::|$)'
            item_matches = re.findall(item_pattern, content)
            
            if item_matches:
                # 각 항목에서 콜론 이후 텍스트를 제거
                substitutions = [re.sub(r':.*$', '', item).strip() for item in item_matches]
                # 빈 항목 및 Target_term과 동일한 항목 제거
                substitutions = [item for item in substitutions if item and item.lower() != target_term.lower()]
                return substitutions[:10]
            
            # 위 방법들이 실패하면 "," 기준으로 분리
            comma_split = content.split(',')
            if len(comma_split) > 1:
                substitutions = [item.strip() for item in comma_split]
                substitutions = [item for item in substitutions if item and item.lower() != target_term.lower()]
                return substitutions[:10]
            
            # 콘텐츠에서 따옴표로 둘러싸인 단어 검색
            quote_pattern = r'["\']([^"\']+)["\']'
            quote_matches = re.findall(quote_pattern, content)
            if quote_matches:
                return quote_matches[:10]
                
            # 모든 방법 실패 시 기본 대체어 반환
            return self._get_default_substitutions(keyword, morpheme)
            
        except Exception as e:
            logger.error(f"대체어 API 생성 중 오류 발생: {str(e)}")
            return self._get_default_substitutions(keyword, morpheme)
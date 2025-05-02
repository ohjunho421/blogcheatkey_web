import redis
import hashlib
import json
import logging
import os
import redis
from anthropic import Anthropic
from konlpy.tag import Okt
from django.conf import settings

logger = logging.getLogger(__name__)

class SubstitutionGenerator:
    """최적화된 대체어 생성기"""
    
    def __init__(self):
        # 기존 초기화 코드 유지
        self.anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')
        self.model = "claude-3-7-sonnet-20250219"
        self.client = Anthropic(api_key=self.anthropic_api_key)
        self.okt = Okt()
        
        # Redis 캐시 연결 (환경 변수에서 설정 가져오기)
        redis_host = os.environ.get('REDIS_HOST', 'localhost')
        redis_port = int(os.environ.get('REDIS_PORT', 6379))
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=0)
        self.cache_ttl = 60 * 60 * 24 * 7  # 1주일 캐시
    
    def get_substitutions(self, keyword, morpheme=None):
        """Redis 캐싱을 활용한 대체어 목록 반환"""
        # 캐시 키 생성
        cache_key = f"subst:{keyword}:{morpheme}" if morpheme else f"subst:{keyword}"
        cache_key = hashlib.md5(cache_key.encode()).hexdigest()
        
        # 캐시 확인
        cached_result = self.redis_client.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
        
        # 캐시 미스: 새로 생성
        try:
            substitutions = self._generate_dynamic_substitutions(keyword, morpheme)
            
            # 자연스러운 지시어 추가
            common_pronouns = ["이것", "이", "해당 항목", "이 주제", "그것"]
            has_pronoun = any(pronoun in substitutions for pronoun in common_pronouns)
            
            if not has_pronoun:
                substitutions = substitutions + common_pronouns[:3]
            
            # 결과 캐싱
            self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(substitutions)
            )
            
            return substitutions
            
        except Exception as e:
            logger.error(f"대체어 생성 중 오류 발생: {str(e)}")
            # 오류 발생 시 기본값 반환
            default_substitutions = self._get_default_substitutions(keyword, morpheme)
            return default_substitutions
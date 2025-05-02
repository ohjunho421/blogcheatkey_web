"""캐싱 관련 유틸리티"""
import redis
import json
import hashlib
import logging
from django.conf import settings
from functools import wraps

logger = logging.getLogger(__name__)

# Redis 연결 설정
REDIS_HOST = getattr(settings, 'REDIS_HOST', 'localhost')
REDIS_PORT = getattr(settings, 'REDIS_PORT', 6379)
REDIS_DB = getattr(settings, 'REDIS_DB', 0)

try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True
    )
    logger.info(f"Redis 캐시 연결됨: {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    logger.warning(f"Redis 연결 실패, 로컬 캐싱으로 대체됨: {str(e)}")

# 로컬 메모리 캐시 (Redis 연결 실패 시 대체용)
local_cache = {}

def get_cached_item(key, default=None):
    """캐시에서 항목 가져오기 (Redis 우선, 실패 시 로컬 캐시)"""
    cache_key = _normalize_cache_key(key)
    
    try:
        # Redis에서 먼저 시도
        if 'redis_client' in globals():
            result = redis_client.get(cache_key)
            if result:
                return json.loads(result)
    except Exception as e:
        logger.warning(f"Redis 조회 실패: {str(e)}")
    
    # 로컬 캐시에서 시도
    return local_cache.get(cache_key, default)

def set_cached_item(key, value, ttl=86400):
    """캐시에 항목 저장 (Redis 우선, 실패 시 로컬 캐시)"""
    cache_key = _normalize_cache_key(key)
    json_value = json.dumps(value)
    
    try:
        # Redis에 먼저 시도
        if 'redis_client' in globals():
            redis_client.setex(cache_key, ttl, json_value)
    except Exception as e:
        logger.warning(f"Redis 저장 실패: {str(e)}")
    
    # 로컬 캐시에도 저장
    local_cache[cache_key] = value

def _normalize_cache_key(key):
    """캐시 키 정규화 (해시 처리)"""
    if isinstance(key, str):
        return hashlib.md5(key.encode()).hexdigest()
    return hashlib.md5(str(key).encode()).hexdigest()

def cache_result(ttl=86400):
    """함수 결과를 캐싱하는 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            key_parts = [func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            cache_key = ":".join(key_parts)
            
            # 캐시에서 결과 확인
            cached_result = get_cached_item(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 캐시 미스: 함수 실행
            result = func(*args, **kwargs)
            
            # 결과 캐싱
            set_cached_item(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator
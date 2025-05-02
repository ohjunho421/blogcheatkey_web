#!/usr/bin/env python
"""
최적화된 블로그치트키 실행 스크립트
- uWSGI 또는 Gunicorn과 함께 사용
"""
import os
import multiprocessing
import concurrent.futures
from django.core.wsgi import get_wsgi_application

# 환경변수 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.blog_cheatkey.settings')

# 최적 워커 수 계산
def get_optimal_workers():
    cpu_count = multiprocessing.cpu_count()
    return max(2, cpu_count * 2 + 1)  # 2x CPUs + 1 공식

# 사전 로딩 함수
def preload_app():
    print("블로그치트키 애플리케이션 사전 로딩 중...")
    
    # 애플리케이션 로드
    application = get_wsgi_application()
    
    # 자주 사용되는 모델 사전 로드
    from content.models import BlogContent
    from key_word.models import Keyword
    from research.models import ResearchSource
    
    # 형태소 분석기 사전 로딩 (백그라운드)
    def load_okt():
        from konlpy.tag import Okt
        okt = Okt()
        okt.morphs("블로그치트키 자연어 처리 최적화")  # 워밍업
        print("Okt 형태소 분석기 로드 완료")
    
    # 병렬로 여러 초기화 작업 수행
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(load_okt),
            # 여기에 다른 사전 로딩 작업 추가 가능
        ]
        concurrent.futures.wait(futures)
    
    print("애플리케이션 사전 로딩 완료")
    return application

# uWSGI 또는 Gunicorn에서 사용할 애플리케이션
# uWSGI 또는 Gunicorn에서 사용할 애플리케이션 객체
application = preload_app()

# Gunicorn 설정 (gunicorn 실행 시)
bind = os.environ.get('BIND', '0.0.0.0:8000')
workers = int(os.environ.get('WORKERS', get_optimal_workers()))
worker_class = 'uvicorn.workers.UvicornWorker'  # ASGI 지원
threads = int(os.environ.get('THREADS', 2))
timeout = int(os.environ.get('TIMEOUT', 120))
keepalive = int(os.environ.get('KEEPALIVE', 5))
max_requests = int(os.environ.get('MAX_REQUESTS', 1000))
max_requests_jitter = int(os.environ.get('MAX_REQUESTS_JITTER', 50))
worker_connections = int(os.environ.get('WORKER_CONNECTIONS', 1000))

# 로깅 설정
errorlog = os.environ.get('ERROR_LOG', '-')
accesslog = os.environ.get('ACCESS_LOG', '-')
loglevel = os.environ.get('LOG_LEVEL', 'info')

# 기본 실행 코드 (직접 실행 시)
if __name__ == '__main__':
    import uvicorn
    import sys
    
    # 커맨드라인 인자
    host = '0.0.0.0'
    port = 8000
    
    if len(sys.argv) > 1:
        if ':' in sys.argv[1]:
            host, port = sys.argv[1].split(':')
            port = int(port)
        else:
            port = int(sys.argv[1])
    
    print(f"블로그치트키 서버를 {host}:{port}에서 시작합니다...")
    uvicorn.run(
        "backend.blog_cheatkey.asgi:application",
        host=host,
        port=port,
        reload=os.environ.get('DEBUG', 'False') == 'True',
        workers=1,
        log_level="info"
    )
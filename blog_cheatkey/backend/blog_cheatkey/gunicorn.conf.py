# Gunicorn 설정 파일
import multiprocessing

# 최적 워커 수 계산
def get_optimal_workers():
    cpu_count = multiprocessing.cpu_count()
    return max(2, cpu_count * 2 + 1)  # 2x CPUs + 1 공식

# 기본 설정
bind = "0.0.0.0:8000"
workers = get_optimal_workers()  # 자동 최적화
worker_class = "uvicorn.workers.UvicornWorker"  # ASGI 지원
threads = 2
timeout = 120
keepalive = 5

# 성능 최적화
max_requests = 1000  # 메모리 누수 방지
max_requests_jitter = 50  # 동시 재시작 방지
worker_connections = 1000  # 워커당 최대 연결 수

# 로깅 설정
errorlog = "logs/gunicorn-error.log"
accesslog = "logs/gunicorn-access.log"
loglevel = "info"

# 프로세스 관리
daemon = False
pidfile = "gunicorn.pid"

# 보안 설정
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
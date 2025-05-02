# celery.py
import os
from celery import Celery

# Django 설정 지정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.blog_cheatkey.settings')

app = Celery('blog_cheatkey')

# 설정 파일에서 Celery 관련 설정 가져오기
app.config_from_object('django.conf:settings', namespace='CELERY')

# 등록된 앱에서 태스크 자동 로드
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
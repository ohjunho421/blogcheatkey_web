# core/urls.py
from django.urls import path, re_path
from django.views.generic import TemplateView

app_name = 'core'

urlpatterns = [
    # React 앱을 서빙하는 URL 패턴
    # 모든 URL을 프론트엔드 앱에 연결 (URL 라우팅은 리액트 라우터가 처리)
    re_path(r'^(?!api/|admin/|media/|static/).*$', TemplateView.as_view(template_name='index.html'), name='index'),
]
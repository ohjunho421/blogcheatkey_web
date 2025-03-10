from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from django.views.generic import TemplateView  # 추가
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    # REST API 경로 추가
    path("api/", include([
        path("auth/", include("accounts.urls")),  # 인증 관련 API
        path("key-word/", include("key_word.urls")),  # 키워드 관련 API
        path("content/", include("content.urls")),  # 콘텐츠 관련 API
        path("history/", include("history.urls")),  # 히스토리 관련 API
    ])),
    
    # React 앱의 모든 경로를 처리하는 catch-all 뷰 (관리자 페이지를 제외한 모든 경로)
    path("", TemplateView.as_view(template_name="index.html"), name='index'),
    path("<path:path>", TemplateView.as_view(template_name="index.html"), name='catch-all'),
]

# 개발 환경에서 미디어 파일 제공
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
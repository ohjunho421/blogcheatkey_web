# title/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TitleSuggestionViewSet

app_name = 'title'

# ViewSet을 사용하므로 라우터를 설정합니다
router = DefaultRouter()
router.register('', TitleSuggestionViewSet, basename='title')

urlpatterns = [
    path('', include(router.urls)),
]
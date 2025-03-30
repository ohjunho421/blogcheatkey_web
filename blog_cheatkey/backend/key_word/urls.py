# key_word/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import KeywordViewSet, SubtopicViewSet

router = DefaultRouter()
router.register(r'', KeywordViewSet, basename='keyword')  # 빈 문자열로 변경
router.register(r'subtopics', SubtopicViewSet, basename='subtopic')

urlpatterns = [
    path('', include(router.urls)),
]
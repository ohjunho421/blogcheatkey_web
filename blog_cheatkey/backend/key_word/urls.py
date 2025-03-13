# key_word/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import KeywordViewSet, SubtopicViewSet

router = DefaultRouter()
router.register(r'keywords', KeywordViewSet, basename='keyword')
router.register(r'subtopics', SubtopicViewSet, basename='subtopic')

urlpatterns = [
    path('', include(router.urls)),
]
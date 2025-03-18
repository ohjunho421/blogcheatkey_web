from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ResearchSourceViewSet, collect_research, extract_statistics

router = DefaultRouter()
router.register(r'sources', ResearchSourceViewSet, basename='research-source')

urlpatterns = [
    path('collect/', collect_research, name='collect-research'),
    path('extract-statistics/', extract_statistics, name='extract-statistics'),
    path('', include(router.urls)),
]
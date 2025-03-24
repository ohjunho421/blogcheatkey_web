from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BlogContentViewSet

router = DefaultRouter()
router.register('', BlogContentViewSet, basename='blog-content')

urlpatterns = [
    path('', include(router.urls)),
    # 상태 확인 엔드포인트 추가
    path('status/', BlogContentViewSet.as_view({'get': 'status'}), name='content-status'),
    path('<int:pk>/optimize_status/', BlogContentViewSet.as_view({'get': 'optimize_status'}), name='content-optimize-status'),
]
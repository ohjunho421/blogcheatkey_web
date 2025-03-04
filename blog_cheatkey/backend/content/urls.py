from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BlogContentViewSet  # 'ContentViewSet'에서 'BlogContentViewSet'로 변경

router = DefaultRouter()
router.register('', BlogContentViewSet, basename='blog-content')

urlpatterns = [
    path('', include(router.urls)),
]
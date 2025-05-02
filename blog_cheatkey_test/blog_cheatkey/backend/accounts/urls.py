from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from .views import (
    RegisterView, LogoutView, ProfileView, ProfileUpdateView, 
    SocialLoginView, SocialLoginCallbackView  # SocialLoginCallbackView 추가
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', obtain_auth_token, name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/update/', ProfileUpdateView.as_view(), name='profile-update'),
    
    # 소셜 로그인 관련 URL
    path('social/', include('allauth.urls')),
    path('social/token/', SocialLoginView.as_view(), name='social-token'),
    # 소셜 로그인 콜백 URL 추가
    path('social/<str:provider>/callback/', SocialLoginCallbackView.as_view(), name='social-callback'),
]
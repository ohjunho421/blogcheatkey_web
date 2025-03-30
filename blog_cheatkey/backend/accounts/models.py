from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """사용자 확장 모델"""
    bio = models.TextField(blank=True, verbose_name="자기소개")
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True, verbose_name="프로필 이미지")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="가입일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="정보 수정일")
    
    class Meta:
        verbose_name = "사용자"
        verbose_name_plural = "사용자 목록"
    
    def __str__(self):
        return self.username

from django.db import models
from accounts.models import User

class Keyword(models.Model):
    """키워드 및 분석 결과 모델"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='keywords', verbose_name="사용자")
    keyword = models.CharField(max_length=100, verbose_name="키워드")
    main_intent = models.TextField(blank=True, verbose_name="주요 검색 의도")
    info_needed = models.JSONField(default=list, verbose_name="필요 정보")
    pain_points = models.JSONField(default=list, verbose_name="불편/어려움")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    class Meta:
        verbose_name = "키워드"
        verbose_name_plural = "키워드 목록"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.keyword

class Subtopic(models.Model):
    """소제목 모델"""
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name='subtopics', verbose_name="키워드")
    title = models.CharField(max_length=200, verbose_name="소제목")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="순서")
    
    class Meta:
        verbose_name = "소제목"
        verbose_name_plural = "소제목 목록"
        ordering = ['order']
    
    def __str__(self):
        return self.title

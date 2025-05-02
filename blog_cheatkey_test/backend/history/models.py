from django.db import models
from django.conf import settings

class ContentHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='content_history')
    title = models.CharField(max_length=255, verbose_name="제목")
    content = models.TextField(verbose_name="콘텐츠")
    keywords = models.JSONField(null=True, blank=True, verbose_name="키워드")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    class Meta:
        verbose_name = "콘텐츠 히스토리"
        verbose_name_plural = "콘텐츠 히스토리 목록"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}의 콘텐츠: {self.title}"
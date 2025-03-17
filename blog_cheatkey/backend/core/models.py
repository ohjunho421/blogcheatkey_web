from django.db import models
from content.models import BlogContent

class GeneratedImage(models.Model):
    """생성된 이미지 모델"""
    blog_content = models.ForeignKey(BlogContent, on_delete=models.CASCADE, related_name='images', verbose_name="블로그 콘텐츠")
    subtopic = models.CharField(max_length=200, blank=True, verbose_name="관련 소제목")
    image = models.ImageField(upload_to='generated_images/', verbose_name="이미지")
    prompt = models.TextField(blank=True, verbose_name="생성 프롬프트")
    alt_text = models.CharField(max_length=200, blank=True, verbose_name="대체 텍스트")
    is_infographic = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    
    class Meta:
        verbose_name = "생성 이미지"
        verbose_name_plural = "생성 이미지 목록"
    
    def __str__(self):
        return f"이미지 - {self.blog_content.title} ({self.subtopic})"
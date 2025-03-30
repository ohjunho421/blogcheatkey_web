from django.db import models
from key_word.models import Keyword
from accounts.models import User

class BlogContent(models.Model):
    """블로그 콘텐츠 모델"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contents', verbose_name="사용자")
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name='contents', verbose_name="키워드")
    title = models.CharField(max_length=200, verbose_name="제목")
    content = models.TextField(verbose_name="콘텐츠")
    mobile_formatted_content = models.TextField(blank=True, verbose_name="모바일 포맷 콘텐츠")
    references = models.JSONField(default=list, verbose_name="참고 자료")
    char_count = models.PositiveIntegerField(default=0, verbose_name="글자수(공백제외)")
    is_optimized = models.BooleanField(default=False, verbose_name="최적화 여부")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    class Meta:
        verbose_name = "블로그 콘텐츠"
        verbose_name_plural = "블로그 콘텐츠 목록"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title

class MorphemeAnalysis(models.Model):
    """형태소 분석 결과 모델"""
    content = models.ForeignKey(BlogContent, on_delete=models.CASCADE, related_name='morpheme_analyses', verbose_name="콘텐츠")
    morpheme = models.CharField(max_length=50, verbose_name="형태소")
    count = models.PositiveIntegerField(default=0, verbose_name="출현 횟수")
    is_valid = models.BooleanField(default=False, verbose_name="유효성(17-20회)")
    
    class Meta:
        verbose_name = "형태소 분석"
        verbose_name_plural = "형태소 분석 목록"
    
    def __str__(self):
        return f"{self.morpheme}: {self.count}회"
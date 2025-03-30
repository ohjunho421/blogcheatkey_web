from django.db import models
from key_word.models import Keyword

class ResearchSource(models.Model):
    """수집된 연구 자료 모델"""
    TYPE_CHOICES = (
        ('news', '뉴스'),
        ('academic', '학술 자료'),
        ('statistic', '통계 자료'),
        ('general', '일반 자료'),
    )
    
    keyword = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name='sources', verbose_name="키워드")
    source_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="자료 유형")
    title = models.CharField(max_length=300, verbose_name="제목")
    url = models.URLField(verbose_name="URL")
    snippet = models.TextField(blank=True, verbose_name="스니펫")
    author = models.CharField(max_length=100, blank=True, verbose_name="작성자/출처")
    published_date = models.DateField(null=True, blank=True, verbose_name="발행일")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="수집일")
    
    class Meta:
        verbose_name = "연구 자료"
        verbose_name_plural = "연구 자료 목록"
        ordering = ['-published_date', '-created_at']
    
    def __str__(self):
        return self.title

class StatisticData(models.Model):
    """통계 데이터 모델"""
    source = models.ForeignKey(ResearchSource, on_delete=models.CASCADE, related_name='statistics', verbose_name="출처")
    value = models.CharField(max_length=100, verbose_name="통계값")
    context = models.TextField(verbose_name="맥락")
    pattern_type = models.CharField(max_length=50, blank=True, verbose_name="패턴 유형")
    
    class Meta:
        verbose_name = "통계 데이터"
        verbose_name_plural = "통계 데이터 목록"
    
    def __str__(self):
        return f"{self.value} ({self.source.title[:30]}...)"

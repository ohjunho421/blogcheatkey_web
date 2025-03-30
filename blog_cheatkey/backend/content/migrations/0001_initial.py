# Generated by Django 5.1.6 on 2025-02-28 16:35

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('key_word', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BlogContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='제목')),
                ('content', models.TextField(verbose_name='콘텐츠')),
                ('mobile_formatted_content', models.TextField(blank=True, verbose_name='모바일 포맷 콘텐츠')),
                ('references', models.JSONField(default=list, verbose_name='참고 자료')),
                ('char_count', models.PositiveIntegerField(default=0, verbose_name='글자수(공백제외)')),
                ('is_optimized', models.BooleanField(default=False, verbose_name='최적화 여부')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일')),
                ('keyword', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contents', to='key_word.keyword', verbose_name='키워드')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contents', to=settings.AUTH_USER_MODEL, verbose_name='사용자')),
            ],
            options={
                'verbose_name': '블로그 콘텐츠',
                'verbose_name_plural': '블로그 콘텐츠 목록',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='MorphemeAnalysis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('morpheme', models.CharField(max_length=50, verbose_name='형태소')),
                ('count', models.PositiveIntegerField(default=0, verbose_name='출현 횟수')),
                ('is_valid', models.BooleanField(default=False, verbose_name='유효성(17-20회)')),
                ('content', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='morpheme_analyses', to='content.blogcontent', verbose_name='콘텐츠')),
            ],
            options={
                'verbose_name': '형태소 분석',
                'verbose_name_plural': '형태소 분석 목록',
            },
        ),
    ]

# Generated by Django 5.1.6 on 2025-02-28 16:35

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('content', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='GeneratedImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subtopic', models.CharField(blank=True, max_length=200, verbose_name='관련 소제목')),
                ('image', models.ImageField(upload_to='generated_images/', verbose_name='이미지')),
                ('prompt', models.TextField(blank=True, verbose_name='생성 프롬프트')),
                ('alt_text', models.CharField(blank=True, max_length=200, verbose_name='대체 텍스트')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('blog_content', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='content.blogcontent', verbose_name='블로그 콘텐츠')),
            ],
            options={
                'verbose_name': '생성 이미지',
                'verbose_name_plural': '생성 이미지 목록',
            },
        ),
    ]

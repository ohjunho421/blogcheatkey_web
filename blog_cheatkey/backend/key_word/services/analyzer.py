# keyword/services/analyzer.py
import logging
import json
import re
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

class KeywordAnalyzer:
    """
    OpenAI의 GPT API를 사용한 키워드 분석 서비스
    기존 코드의 Perplexity API 대신 OpenAI API 사용
    """
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o" 
    
    def analyze_keyword(self, keyword):
        """
        키워드 분석 수행
        
        Args:
            keyword (str): 분석할 키워드
            
        Returns:
            dict: 분석 결과
        """
        try:
            # 시스템 프롬프트 설정
            system_prompt = "당신은 SEO 및 콘텐츠 마케팅 전문가입니다. 키워드를 분석하여 구체적이고 실용적인 정보를 제공해야 합니다."
            
            # 프롬프트 생성
            prompt = f"""
            다음 키워드를 SEO 관점에서 분석해주세요:
            키워드: {keyword}

            다음 형식으로 분석 결과를 제공해주세요:

            1. 주요 검색 의도: 
            (2-3문장으로 이 키워드를 검색하는 사람들의 주요 의도를 설명해주세요)

            2. 검색자가 얻고자 하는 정보:
            (가장 중요한 3가지만 bullet point로 작성해주세요)
            - 
            - 
            - 

            3. 검색자가 겪고 있는 불편함이나 어려움:
            (가장 일반적인 3가지 어려움만 bullet point로 작성해주세요)
            - 
            - 
            - 
            """
            
            # API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
            )
            
            content = response.choices[0].message.content
            return self._parse_analysis_result(content)
            
        except Exception as e:
            logger.error(f"키워드 분석 중 오류 발생: {str(e)}")
            raise
    
    def suggest_subtopics(self, keyword):
        """
        키워드 기반 소제목 추천
        
        Args:
            keyword (str): 키워드
            
        Returns:
            list: 추천 소제목 목록
        """
        try:
            # 시스템 프롬프트 설정
            system_prompt = "당신은 블로그 콘텐츠 구조화 전문가입니다. 제공된 키워드를 바탕으로 논리적이고 포괄적인 소제목을 추천해야 합니다."
            
            # 프롬프트 생성
            prompt = f"""
            검색 키워드 '{keyword}'에 대한 블로그 소제목 4개를 추천해주세요.

            조건:
            1. 모든 소제목은 반드시 '{keyword}'와 직접적으로 관련되어야 함
            2. 소제목들은 논리적 순서로 구성
            3. 각 소제목은 검색자의 실제 고민/궁금증을 해결할 수 있는 내용
            4. 전체적으로 '{keyword}'에 대한 포괄적 이해를 제공할 수 있는 구성

            형식:
            1. [첫 번째 소제목]: 기초/개요
            2. [두 번째 소제목]: 주요 정보/특징
            3. [세 번째 소제목]: 실용적 팁/방법
            4. [네 번째 소제목]: 선택/관리 방법
            """
            
            # API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
            
            content = response.choices[0].message.content
            return self._parse_subtopics(content)
            
        except Exception as e:
            logger.error(f"소제목 추천 중 오류 발생: {str(e)}")
            raise
    
    def _parse_analysis_result(self, content):
        """
        분석 결과 파싱
        
        Args:
            content (str): API 응답 내용
            
        Returns:
            dict: 파싱된 분석 결과
        """
        # 섹션별 내용 추출
        sections = content.split('\n\n')
        main_intent = ""
        info_needed = []
        pain_points = []
        
        for section in sections:
            if '1. 주요 검색 의도:' in section:
                main_intent = section.split('주요 검색 의도:')[1].strip()
            elif '2. 검색자가 얻고자 하는 정보:' in section:
                info_lines = section.split('\n')[1:]
                info_needed = [line.strip('- ').strip() for line in info_lines if line.strip().startswith('-')]
            elif '3. 검색자가 겪고 있는 불편함이나 어려움:' in section:
                pain_lines = section.split('\n')[1:]
                pain_points = [line.strip('- ').strip() for line in pain_lines if line.strip().startswith('-')]
        
        return {
            'raw_text': content,
            'main_intent': main_intent,
            'info_needed': info_needed,
            'pain_points': pain_points
        }
    
    def _parse_subtopics(self, content):
        """
        소제목 파싱
        
        Args:
            content (str): API 응답 내용
            
        Returns:
            list: 파싱된 소제목 목록
        """
        subtopics = []
        
        for line in content.split('\n'):
            if line.strip() and line[0].isdigit() and '. ' in line:
                subtitle = line.split('. ', 1)[1].strip()
                if ':' in subtitle:
                    subtitle = subtitle.split(':', 1)[1].strip()
                if subtitle:
                    subtopics.append(subtitle)
        
        return subtopics[:4]  # 최대 4개의 소제목만 반환


# research/forms.py
from django import forms
from research.models import ResearchSource

class ResearchFilterForm(forms.Form):
    """연구 자료 필터링 폼"""
    TYPE_CHOICES = (
        ('all', '전체'),
        ('news', '뉴스'),
        ('academic', '학술 자료'),
        ('statistic', '통계 자료'),
        ('general', '일반 자료'),
    )
    
    source_type = forms.ChoiceField(
        choices=TYPE_CHOICES,
        required=False,
        initial='all',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    search_query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '검색어 입력'})
    )


# research/views.py
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.http import JsonResponse
from django.contrib import messages
from key_word.models import Keyword
from research.models import ResearchSource, StatisticData
from research.services.collector import ResearchCollector
from research.forms import ResearchFilterForm

logger = logging.getLogger(__name__)

class ResearchListView(LoginRequiredMixin, ListView):
    """연구 자료 목록 뷰"""
    model = ResearchSource
    template_name = 'research/list.html'
    context_object_name = 'sources'
    paginate_by = 10
    
    def get_queryset(self):
        keyword_pk = self.kwargs.get('keyword_pk')
        keyword = get_object_or_404(Keyword, pk=keyword_pk, user=self.request.user)
        
        queryset = ResearchSource.objects.filter(keyword=keyword)
        
        # 필터링
        form = ResearchFilterForm(self.request.GET)
        if form.is_valid():
            source_type = form.cleaned_data.get('source_type')
            search_query = form.cleaned_data.get('search_query')
            
            if source_type and source_type != 'all':
                queryset = queryset.filter(source_type=source_type)
            
            if search_query:
                queryset = queryset.filter(
                    title__icontains=search_query) | queryset.filter(
                    snippet__icontains=search_query)
        
        return queryset.order_by('-published_date', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        keyword_pk = self.kwargs.get('keyword_pk')
        context['keyword'] = get_object_or_404(Keyword, pk=keyword_pk, user=self.request.user)
        context['filter_form'] = ResearchFilterForm(self.request.GET)
        context['statistics'] = StatisticData.objects.filter(
            source__keyword__id=keyword_pk).select_related('source')
        return context

class ResearchDetailView(LoginRequiredMixin, DetailView):
    """연구 자료 상세 뷰"""
    model = ResearchSource
    template_name = 'research/detail.html'
    context_object_name = 'source'
    
    def get_queryset(self):
        return ResearchSource.objects.filter(keyword__user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statistics'] = self.object.statistics.all()
        return context

class ResearchCreateView(LoginRequiredMixin, View):
    """연구 자료 수집 뷰 (AJAX 요청 처리)"""
    
    def get(self, request, keyword_pk):
        keyword = get_object_or_404(Keyword, pk=keyword_pk, user=request.user)
        
        # 이미 자료가 있는지 확인
        sources_count = ResearchSource.objects.filter(keyword=keyword).count()
        
        return render(request, 'research/create.html', {
            'keyword': keyword,
            'sources_count': sources_count
        })
    
    def post(self, request, keyword_pk):
        keyword = get_object_or_404(Keyword, pk=keyword_pk, user=request.user)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                # 연구 자료 수집 서비스 초기화
                collector = ResearchCollector()
                
                # 수집 수행 (백그라운드 작업으로 변경 가능)
                result = collector.collect_and_save(keyword.pk)
                
                if result:
                    return JsonResponse({
                        'status': 'success',
                        'message': '연구 자료 수집이 완료되었습니다.',
                        'data': {
                            'news_count': len(result.get('news', [])),
                            'academic_count': len(result.get('academic', [])),
                            'general_count': len(result.get('general', [])),
                            'statistics_count': len(result.get('statistics', []))
                        }
                    })
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': '연구 자료 수집에 실패했습니다.'
                    }, status=500)
                
            except Exception as e:
                logger.error(f'연구 자료 수집 중 오류 발생: {str(e)}')
                return JsonResponse({
                    'status': 'error',
                    'message': f'연구 자료 수집 중 오류가 발생했습니다: {str(e)}'
                }, status=500)
        
        # 일반 요청인 경우
        try:
            # 연구 자료 수집 서비스 초기화
            collector = ResearchCollector()
            
            # 수집 수행
            result = collector.collect_and_save(keyword.pk)
            
            if result:
                messages.success(request, '연구 자료 수집이 완료되었습니다.')
                return redirect('research:list', keyword_pk=keyword.pk)
            else:
                messages.error(request, '연구 자료 수집에 실패했습니다.')
                return redirect('keyword:detail', pk=keyword.pk)
                
        except Exception as e:
            logger.error(f'연구 자료 수집 중 오류 발생: {str(e)}')
            messages.error(request, f'연구 자료 수집 중 오류가 발생했습니다: {str(e)}')
            return redirect('keyword:detail', pk=keyword.pk)
import re
import json
import logging
import time
import traceback
from urllib.parse import urlparse
from django.conf import settings
from konlpy.tag import Okt
from anthropic import Anthropic
from research.models import ResearchSource, StatisticData
from key_word.models import Keyword, Subtopic
from content.models import BlogContent, MorphemeAnalysis
from accounts.models import User
from .substitution_generator import SubstitutionGenerator

logger = logging.getLogger(__name__)


class ContentGenerator:
    """
    Claude API를 사용한 블로그 콘텐츠 생성 서비스
    - 생성과 동시에 최적화 조건을 만족하는 콘텐츠 생성
    """
    
    def __init__(self):
        self.anthropic_api_key = settings.ANTHROPIC_API_KEY
        self.model = "claude-3-7-sonnet-20250219"
        self.client = Anthropic(api_key=self.anthropic_api_key)
        self.okt = Okt()
        self.max_retries = 5
        self.retry_delay = 2
        self.substitution_generator = SubstitutionGenerator()
    
    def generate_content(self, keyword_id, user_id, target_audience=None, business_info=None, custom_morphemes=None):
        """
        키워드 기반 블로그 콘텐츠 생성 (최적화 조건 충족)
        
        Args:
            keyword_id (int): 키워드 ID
            user_id (int): 사용자 ID
            target_audience (dict): 타겟 독자 정보
            business_info (dict): 사업자 정보
            custom_morphemes (list): 사용자 지정 형태소 목록
            
        Returns:
            int: 생성된 BlogContent 객체의 ID
        """
        for attempt in range(self.max_retries):
            try:
                # 키워드 및 관련 정보 가져오기
                keyword = Keyword.objects.get(id=keyword_id)
                user = User.objects.get(id=user_id)
                subtopics = list(keyword.subtopics.order_by('order').values_list('title', flat=True))
                
                # 연구 자료 가져오기
                news_sources = ResearchSource.objects.filter(keyword=keyword, source_type='news')
                academic_sources = ResearchSource.objects.filter(keyword=keyword, source_type='academic')
                general_sources = ResearchSource.objects.filter(keyword=keyword, source_type='general')
                statistics = StatisticData.objects.filter(source__keyword=keyword)
                
                # 기존 "생성 중..." 콘텐츠 찾기 (시간 제한 없음)
                existing_content = BlogContent.objects.filter(
                    keyword=keyword, 
                    user=user, 
                    title__contains="(생성 중...)"
                ).order_by('-created_at').first()
                
                # 형태소 분석
                morphemes = self.okt.morphs(keyword.keyword)
                
                # 사용자 지정 형태소 추가
                if custom_morphemes:
                    morphemes.extend(custom_morphemes)
                    morphemes = list(set(morphemes))  # 중복 제거
                
                # 데이터 구성
                data = {
                    "keyword": keyword.keyword,
                    "subtopics": subtopics,
                    "target_audience": target_audience or {
                        "primary": keyword.main_intent,
                        "pain_points": keyword.pain_points
                    },
                    "business_info": business_info or {
                        "name": user.username,
                        "expertise": ""
                    },
                    "morphemes": morphemes,
                    "research_data": self._format_research_data(
                        news_sources, 
                        academic_sources, 
                        general_sources, 
                        statistics
                    )
                }
                
                # 로깅 추가 - API 호출 시작 전
                logger.info(f"콘텐츠 생성 API 호출 시작: 키워드={keyword.keyword}, 사용자={user.username}")
                
                # 최적화 조건이 포함된 콘텐츠 생성 프롬프트 
                prompt = self._create_optimized_content_prompt(data)
                
                # API 요청
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=8192,
                    temperature=0.7,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                # 로깅 추가 - API 호출 완료
                logger.info("콘텐츠 생성 API 호출 완료")
                
                content = response.content[0].text
                
                # 최적화 검증
                verification_result = self._verify_content_optimization(content, keyword.keyword, morphemes)
                
                # 최적화 조건을 만족하지 않는 경우 추가 최적화 시도
                if not verification_result['is_fully_optimized']:
                    # 로깅 추가 - 최적화 시작
                    logger.info("콘텐츠 최적화 시작: 미달 조건 있음")
                    logger.info(f"검증 결과: 글자수={verification_result['char_count']}, 유효={verification_result['is_valid_char_count']}, 형태소 유효={verification_result['is_valid_morphemes']}")
                    
                    # 최적화 프롬프트 생성 및 API 호출
                    optimization_prompt = self._create_verification_optimization_prompt(
                        content, 
                        keyword.keyword, 
                        morphemes,
                        verification_result
                    )
                    
                    optimization_response = self.client.messages.create(
                        model=self.model,
                        max_tokens=8192,
                        temperature=0.5,
                        messages=[
                            {"role": "user", "content": optimization_prompt}
                        ]
                    )
                    
                    optimized_content = optimization_response.content[0].text
                    
                    # 최종 검증
                    final_verification = self._verify_content_optimization(optimized_content, keyword.keyword, morphemes)
                    
                    if final_verification['is_fully_optimized'] or final_verification['is_better_than'](verification_result):
                        content = optimized_content
                        logger.info("최적화된 콘텐츠 사용: 더 나은 결과")
                    else:
                        logger.info("원본 콘텐츠 사용: 최적화 시도 후에도 개선되지 않음")
                    
                    # 로깅 추가 - 최적화 완료
                    logger.info(f"콘텐츠 최적화 완료: 글자수={final_verification['char_count']}, 유효={final_verification['is_valid_char_count']}, 형태소 유효={final_verification['is_valid_morphemes']}")
                
                # 참고 자료 추가
                content_with_references = self._add_references(content, data['research_data'])
                
                # 모바일 최적화 포맷 생성
                mobile_formatted_content = self._format_for_mobile(content_with_references)
                
                # 참고 자료 목록 추출
                references = self._extract_references(content_with_references)
                
                # 이전 '생성 중' 콘텐츠 삭제
                if existing_content:
                    # 형태소 분석 결과도 같이 삭제됨 (CASCADE)
                    existing_content.delete()
                
                # 콘텐츠 저장
                blog_content = BlogContent.objects.create(
                    user=user,
                    keyword=keyword,
                    title=f"{keyword.keyword} 완벽 가이드",  # 기본 제목, 나중에 변경 가능
                    content=content_with_references,
                    mobile_formatted_content=mobile_formatted_content,
                    references=references,  # 참고자료 목록 저장
                    char_count=len(content.replace(" ", "")),
                    is_optimized=True
                )
                
                # 로깅 추가 - 형태소 분석 시작
                logger.info("형태소 분석 시작")
                
                # 형태소 분석 결과 저장
                morpheme_analysis = self.analyze_morphemes(content, keyword.keyword, custom_morphemes)
                for morpheme, info in morpheme_analysis.get('morpheme_analysis', {}).items():
                    if morpheme and len(morpheme) > 1:  # 1글자 미만은 저장하지 않음
                        MorphemeAnalysis.objects.create(
                            content=blog_content,
                            morpheme=morpheme,
                            count=info.get('count', 0),
                            is_valid=info.get('is_valid', False)
                        )
                
                # 로깅 추가 - 콘텐츠 생성 완료
                logger.info(f"콘텐츠 생성 완료: ID={blog_content.id}")
                
                return blog_content.id
                    
            except Exception as e:
                logger.error(f"콘텐츠 생성 중 오류 발생: {str(e)}")
                logger.error(traceback.format_exc())
                
                if 'overloaded_error' in str(e) and attempt < self.max_retries - 1:
                    logger.warning(f"서버가 혼잡합니다. {self.retry_delay}초 후 재시도합니다... ({attempt + 1}/{self.max_retries})")
                    time.sleep(self.retry_delay)
                    continue
                raise e
        
        return None
    
    def _verify_content_optimization(self, content, keyword, morphemes):
        """
        콘텐츠가 최적화 조건을 만족하는지 검증
        
        Args:
            content (str): 검증할 콘텐츠
            keyword (str): 주요 키워드
            morphemes (list): 형태소 목록
            
        Returns:
            dict: 검증 결과
        """
        # 참고자료 분리 (검증 대상에서 제외)
        content_without_refs = content
        if "## 참고자료" in content:
            content_without_refs = content.split("## 참고자료", 1)[0]
        
        # 글자수 검증
        char_count = len(content_without_refs.replace(" ", ""))
        is_valid_char_count = 1700 <= char_count <= 2000
        
        # 형태소 분석
        morpheme_analysis = self.analyze_morphemes(content_without_refs, keyword)
        is_valid_morphemes = morpheme_analysis.get('is_valid', False)
        
        # 완전 최적화 여부
        is_fully_optimized = is_valid_char_count and is_valid_morphemes
        
        result = {
            'is_fully_optimized': is_fully_optimized,
            'char_count': char_count,
            'is_valid_char_count': is_valid_char_count,
            'morpheme_analysis': morpheme_analysis,
            'is_valid_morphemes': is_valid_morphemes,
            'content_without_refs': content_without_refs
        }
        
        # 비교 함수 추가
        result['is_better_than'] = lambda other: self._is_optimization_better(result, other)
        
        return result
    
    def _is_optimization_better(self, new_result, old_result):
        """
        새 최적화 결과가 이전 결과보다 나은지 비교
        
        Args:
            new_result (dict): 새 검증 결과
            old_result (dict): 이전 검증 결과
            
        Returns:
            bool: 더 나은 결과이면 True
        """
        # 모든 조건 만족 여부 비교
        if new_result['is_fully_optimized'] and not old_result['is_fully_optimized']:
            return True
            
        # 글자수 조건 만족 여부 비교
        if new_result['is_valid_char_count'] and not old_result['is_valid_char_count']:
            return True
            
        # 형태소 조건 만족 여부 비교
        if new_result['is_valid_morphemes'] and not old_result['is_valid_morphemes']:
            return True
        
        # 유효한 형태소 개수 비교
        new_valid_count = sum(1 for m, info in new_result['morpheme_analysis'].get('morpheme_analysis', {}).items() 
                             if info.get('is_valid', False))
        old_valid_count = sum(1 for m, info in old_result['morpheme_analysis'].get('morpheme_analysis', {}).items() 
                             if info.get('is_valid', False))
        
        if new_valid_count > old_valid_count:
            return True
            
        # 글자수가 목표에 더 가까운지 확인
        if not new_result['is_valid_char_count'] and not old_result['is_valid_char_count']:
            target_center = (1700 + 2000) / 2  # 목표 범위의 중간값
            new_distance = abs(new_result['char_count'] - target_center)
            old_distance = abs(old_result['char_count'] - target_center)
            
            if new_distance < old_distance:
                return True
                
        return False
    
    def _format_research_data(self, news_sources, academic_sources, general_sources, statistics):
        """
        연구 자료 포맷팅
        """
        research_data = {
            'news': [],
            'academic': [],
            'general': [],
            'statistics': []
        }
        
        # 뉴스 자료
        for source in news_sources:
            research_data['news'].append({
                'title': source.title,
                'url': source.url,
                'snippet': source.snippet,
                'date': source.published_date.isoformat() if source.published_date else '',
                'source': source.author
            })
        
        # 학술 자료
        for source in academic_sources:
            research_data['academic'].append({
                'title': source.title,
                'url': source.url,
                'snippet': source.snippet,
                'date': source.published_date.isoformat() if source.published_date else '',
                'source': source.author
            })
        
        # 일반 자료
        for source in general_sources:
            research_data['general'].append({
                'title': source.title,
                'url': source.url,
                'snippet': source.snippet,
                'date': source.published_date.isoformat() if source.published_date else '',
                'source': source.author
            })
        
        # 통계 자료
        for stat in statistics:
            research_data['statistics'].append({
                'value': stat.value,
                'context': stat.context,
                'pattern_type': stat.pattern_type,
                'source_url': stat.source.url,
                'source_title': stat.source.title,
                'source': stat.source.author,
                'date': stat.source.published_date.isoformat() if source.published_date else ''
            })
        
        return research_data
    
    def _create_optimized_content_prompt(self, data):
        """
        최적화 조건이 포함된 콘텐츠 생성 프롬프트 생성
        
        Args:
            data (dict): 콘텐츠 생성 데이터
            
        Returns:
            str: 콘텐츠 생성 프롬프트
        """
        keyword = data["keyword"]
        morphemes = data.get("morphemes", self.okt.morphs(keyword))
        
        # 안전한 데이터 가져오기
        target_audience = data.get('target_audience', {})
        business_info = data.get('business_info', {})
        research_data = data.get('research_data', {})
        
        # 연구 자료 포맷팅 (최대 2개씩만 사용)
        research_text = ""
        if isinstance(research_data, dict):
            news = research_data.get('news', [])[:2]
            academic = research_data.get('academic', [])[:2]
            general = research_data.get('general', [])[:2]
            
            if news:
                research_text += "📰 뉴스 자료:\n"
                for item in news:
                    research_text += f"- {item.get('title', '')}: {item.get('snippet', '')}\n"
            
            if academic:
                research_text += "\n📚 학술 자료:\n"
                for item in academic:
                    research_text += f"- {item.get('title', '')}: {item.get('snippet', '')}\n"
                    
            if general:
                research_text += "\n🔍 일반 자료:\n"
                for item in general:
                    research_text += f"- {item.get('title', '')}: {item.get('snippet', '')}\n"

        statistics_text = ""
        if isinstance(research_data.get('statistics'), list):
            statistics_text = "\n💡 활용 가능한 통계 자료:\n"
            for stat in research_data['statistics']:
                statistics_text += f"- {stat['context']} (출처: {stat['source_title']})\n"

        # 최적화 조건 섹션 추가
        optimization_requirements = f"""
        ⚠️ 중요: 다음 최적화 조건을 반드시 준수해야 합니다.
        
        1. 글자수 조건: 정확히 1700-2000자 (공백 제외, 참고자료 섹션 제외)
           - 완성 후 Ctrl+F로 검색하여 글자수 확인
           - 내용을 간결하게 유지하거나 필요시 확장하여 이 범위에 맞추기
        
        2. 키워드 및 형태소 출현 횟수 조건:
           - 주 키워드 '{keyword}': 정확히 17-20회 사용
           - 각 형태소({', '.join(morphemes)}): 정확히 17-20회 사용
           - 완성 후 Ctrl+F로 검색하여 각 키워드와 형태소의 출현 횟수 확인
        
        3. 키워드 및 형태소 최적화 방법:
           - 지시어 활용: "{keyword}는" → "이것은"
           - 자연스러운 생략: 문맥상 이해 가능한 경우 생략
           - 동의어/유사어 대체: 과다 사용된 단어를 적절한 동의어로 대체
        
        ✓ 최종 검증: 생성 완료 후 모든 키워드와 형태소가 정확히 17-20회 범위 내에서 사용되었는지 확인하세요.
        """

        prompt = f"""
        다음 조건들을 준수하여 전문성과 친근함이 조화된, 읽기 쉽고 실용적인 블로그 글을 작성해주세요:

        {optimization_requirements}

        필수 활용 자료:
        {research_text}
        
        통계 자료 (반드시 1개 이상 활용):
        {statistics_text}

        **중요 참고자료 인용 지침:**
        1. 본문에서 [1], [2]와 같은 인용번호 표시는 절대 사용하지 마세요.
        2. 대신 "한국석유공사의 보고서에 따르면" 또는 "API의 연구 결과에 의하면" 등 출처 이름을 직접 언급하는 방식으로 인용하세요.
        3. 참고자료의 출처명과 내용을 정확하게 언급해주세요. (예: "한국석유공사에 따르면 국내 자동차용 윤활유 수요는...")
        4. 링크는 글 하단의 참고자료 섹션에 자동으로 추가되므로 본문에 URL을 포함하지 마세요.
        5. 각 소제목 섹션에서 최소 1개 이상의 관련 참고자료를 출처를 명시하여 인용하세요.

        1. 글의 구조와 형식
        - 전체 구조: 서론(20%) - 본론(60%) - 결론(20%)
        - 각 소제목은 ### 마크다운으로 표시
        - 소제목 구성:
        ### {data['subtopics'][0] if len(data['subtopics']) > 0 else '소제목1'}
        ### {data['subtopics'][1] if len(data['subtopics']) > 1 else '소제목2'}
        ### {data['subtopics'][2] if len(data['subtopics']) > 2 else '소제목3'}
        ### {data['subtopics'][3] if len(data['subtopics']) > 3 else '소제목4'}
        - 전체 길이: 1700-2000자 (공백 제외)

        2. [필수] 서론 작성 가이드
        반드시 다음 구조로 서론을 작성해주세요:
        1) 독자의 고민/문제 공감 (반드시 최신 통계나 연구 결과 인용)
        - 수집된 통계자료나 연구결과를 활용하여 문제의 심각성이나 중요성 강조
        - "최근 한국석유공사의 조사에 따르면..." 또는 "미국석유협회의 통계에 의하면..."과 같은 방식으로 시작
        - "{keyword}에 대해 고민이 많으신가요?"
        - 타겟 독자의 구체적인 어려움 언급: {', '.join(target_audience.get('pain_points', []))}
        
        2) 전문가로서의 해결책 제시
        - "이런 문제는 {keyword}만 잘 알고있어도 해결되는 문제입니다"
        - "{business_info.get('name', '')}가 {business_info.get('expertise', '')}을 바탕으로 해결해드리겠습니다"
        
        3) 독자 관심 유도
        - "이 글에서는 구체적으로 다음과 같은 내용을 다룹니다" 후 소제목 미리보기
        - "5분만 투자하시면 {keyword}에 대한 모든 것을 알 수 있습니다"

        3. 글쓰기 스타일
        - 전문가의 지식을 쉽게 설명하듯이 편안한 톤 유지
        - 각 문단은 자연스럽게 다음 문단으로 연결
        - 스토리텔링 요소 활용
        - 실제 사례나 비유를 통해 이해하기 쉽게 설명

        4. 핵심 키워드 활용
        - 주 키워드: {keyword}
        - 형태소: {', '.join(morphemes)}
        - 각 키워드와 형태소 17-20회 자연스럽게 사용
            
        5. [필수] 참고 자료 활용
        - 각 소제목 섹션마다 최소 1개 이상의 관련 통계/연구 자료 반드시 인용
        - 인용할 때는 "~에 따르면", "~의 연구 결과", "~의 통계에 의하면" 등 명확한 표현 사용
        - 모든 통계와 수치는 출처를 구체적으로 명시 (예: "2024년 한국석유공사의 조사에 따르면...")
        - 가능한 최신 자료를 우선적으로 활용
        - 통계나 수치를 인용할 때는 그 의미나 시사점도 함께 설명

        6. 본론 작성 가이드
        - 각 소제목마다 핵심 주제 한 줄 요약으로 시작
        - 이론 → 사례 → 실천 방법 순으로 구성
        - 참고 자료의 통계나 연구 결과를 자연스럽게 인용
        - 전문적 내용도 쉽게 풀어서 설명
        - 각 섹션 끝에서 다음 섹션으로 자연스러운 연결

        7. 결론 작성 가이드
        - 본론 내용 요약
        - 실천 가능한 다음 단계 제시
        - "{business_info.get('name', '')}가 도와드릴 수 있다"는 메시지
        - 독자와의 상호작용 유도

        위 조건들을 바탕으로, 특히 타겟 독자({target_audience.get('primary', '')})의 어려움을 해결하는 데 초점을 맞추어 블로그 글을 작성해주세요.
        """
        return prompt
    
    def _create_verification_optimization_prompt(self, content, keyword, morphemes, verification_result):
        """
        검증 결과를 기반으로 최적화 프롬프트 생성
        
        Args:
            content (str): 최적화할 콘텐츠
            keyword (str): 주요 키워드
            morphemes (list): 형태소 목록
            verification_result (dict): 검증 결과
            
        Returns:
            str: 최적화 프롬프트
        """
        # 최적화가 필요한 형태소 목록
        morpheme_issues = []
        morpheme_analysis = verification_result['morpheme_analysis']
        
        for morpheme, info in morpheme_analysis.get('morpheme_analysis', {}).items():
            if not info.get('is_valid', True):
                count = info.get('count', 0)
                if count < 17:
                    morpheme_issues.append(f"- '{morpheme}': 현재 {count}회 → 17-20회로 증가 필요 (+{17-count}회)")
                elif count > 20:
                    morpheme_issues.append(f"- '{morpheme}': 현재 {count}회 → 17-20회로 감소 필요 (-{count-20}회)")
        
        morpheme_issues_text = "\n".join(morpheme_issues)
        
        # 글자수 조정 안내
        char_count = verification_result['char_count']
        char_count_guidance = ""
        
        if char_count < 1700:
            char_count_guidance = f"글자수가 부족합니다. 현재 {char_count}자 → 1700-2000자로 증가 필요 (최소 {1700-char_count}자 추가)"
        elif char_count > 2000:
            char_count_guidance = f"글자수가 초과되었습니다. 현재 {char_count}자 → 1700-2000자로 감소 필요 (최소 {char_count-2000}자 제거)"
        else:
            char_count_guidance = f"글자수는 적정 범위입니다 (현재 {char_count}자). 형태소 조정 과정에서 유지하세요."
        
        # 최적화 전략 제시 - 동적 대체어 생성 활용
        optimization_strategies = self._generate_dynamic_optimization_strategies(keyword, morpheme_analysis.get('morpheme_analysis', {}))
        
        return f"""
        다음 블로그 콘텐츠를 최적화해주세요. 다음 조건을 모두 충족하도록 수정해주세요:
        
        ========== 최적화 목표 ==========
        
        1. 글자수 조건: 1700-2000자 (공백 제외)
           {char_count_guidance}
        
        2. 형태소 출현 횟수 조건: 각 형태소 정확히 17-20회 사용
           조정이 필요한 형태소:
           {morpheme_issues_text}
        
        ========== 최적화 전략 ==========
        {optimization_strategies}
        
        ========== 중요 지침 ==========
        
        1. 콘텐츠의 핵심 메시지와 전문성은 유지하세요.
        2. 모든 소제목과 주요 섹션을 유지하세요.
        3. 자연스러운 문체와 흐름을 유지하세요.
        4. 모든 통계 자료 인용과 출처 표시를 유지하세요.
        5. 조정 후에는 반드시 각 형태소가 17-20회 범위 내에서 사용되었는지 확인하세요.
        6. 결과물만 제시하고 추가 설명은 하지 마세요.
        
        ========== 원본 콘텐츠 ==========
        {content}
        """
    
    def _generate_dynamic_optimization_strategies(self, keyword, morpheme_analysis):
        """
        동적으로 키워드와 형태소에 대한 최적화 전략 생성
        
        Args:
            keyword (str): 주요 키워드
            morpheme_analysis (dict): 형태소 분석 결과
            
        Returns:
            str: 최적화 전략 텍스트
        """
        # 과다/부족 형태소 분류
        excess_morphemes = []
        lacking_morphemes = []
        
        for morpheme, info in morpheme_analysis.items():
            count = info.get('count', 0)
            if count > 20:
                excess_morphemes.append(morpheme)
            elif count < 17:
                lacking_morphemes.append(morpheme)
        
        # 기본 전략 제시
        strategies = """
        1. 과다 사용된 형태소 감소 방법:
           - 동의어/유사어 대체: 반복되는 용어를 유사한 의미의 다른 표현으로 바꾸기
           - 지시어 사용: "이것", "이", "그", "해당" 등의 지시어로 대체
           - 자연스러운 생략: 문맥상 이해 가능한 경우 과감히 생략
           - 다른 표현으로 문장 재구성: 같은 의미를 다른 방식으로 표현
        
        2. 부족한 형태소 증가 방법:
           - 구체적인 예시나 사례 추가: 해당 형태소가 포함된 예시 추가
           - 설명 확장: 핵심 개념에 대한 추가 설명 제공
           - 실용적인 팁이나 조언 추가: 형태소가 포함된 팁 제시
           - 기존 문장 분리: 한 문장을 두 개로 나누어 형태소 사용 기회 증가
        """
        
        # 구체적인 대체어 제안
        substitution_text = "\n3. 유용한 대체어 예시:"
        
        # 키워드 대체어
        keyword_substitutions = self.substitution_generator.get_substitutions(keyword)
        if keyword_substitutions:
            substitution_text += f"\n   - '{keyword}' 대체어: {', '.join(keyword_substitutions[:5])}"
        
        # 과다 사용된 각 형태소에 대한 대체어
        for morpheme in excess_morphemes:
            if morpheme != keyword:  # 키워드는 이미 처리됨
                morpheme_substitutions = self.substitution_generator.get_substitutions(keyword, morpheme)
                if morpheme_substitutions:
                    substitution_text += f"\n   - '{morpheme}' 대체어: {', '.join(morpheme_substitutions[:5])}"
        
        return strategies + substitution_text
        
    def analyze_morphemes(self, text, keyword=None, custom_morphemes=None):
        """
        형태소 분석 및 출현 횟수 검증
        
        Args:
            text (str): 분석할 텍스트
            keyword (str): 주요 키워드
            custom_morphemes (list): 사용자 지정 형태소
            
        Returns:
            dict: 형태소 분석 결과
        """
        if not keyword:
            return {}

        # 정확한 카운팅을 위한 전처리
        text = re.sub(r'<[^>]+>', '', text)  # HTML 태그 제거
        text = re.sub(r'[^\w\s가-힣]', ' ', text)  # 특수문자 처리 (한글 포함)
        
        # 키워드와 형태소 출현 횟수 계산
        keyword_count = self._count_exact_word(keyword, text)
        morphemes = self.okt.morphs(keyword)
        
        # 사용자 지정 형태소 추가
        if custom_morphemes:
            morphemes.extend(custom_morphemes)
        morphemes = list(set(morphemes))  # 중복 제거

        analysis = {
            "is_valid": True,
            "morpheme_analysis": {},
            "needs_optimization": False
        }

        # 키워드 분석
        analysis["morpheme_analysis"][keyword] = {
            "count": keyword_count,
            "is_valid": 17 <= keyword_count <= 20,
            "status": "적정" if 17 <= keyword_count <= 20 else "과다" if keyword_count > 20 else "부족"
        }

        # 형태소 분석
        for morpheme in morphemes:
            # 2글자 미만 형태소는 분석에서 제외
            if len(morpheme) < 2:
                continue
                
            count = self._count_exact_word(morpheme, text)
            is_valid = 17 <= count <= 20
            
            if not is_valid:
                analysis["is_valid"] = False
                analysis["needs_optimization"] = True

            analysis["morpheme_analysis"][morpheme] = {
                "count": count,
                "is_valid": is_valid,
                "status": "적정" if is_valid else "과다" if count > 20 else "부족"
            }

        return analysis

    def _count_exact_word(self, word, text):
        """
        텍스트에서 특정 단어의 정확한 출현 횟수를 계산
        
        Args:
            word (str): 찾을 단어
            text (str): 검색할 텍스트
            
        Returns:
            int: 단어의 출현 횟수
        """
        # 한글의 경우 경계가 명확하지 않아 다른 패턴 필요
        if re.search(r'[가-힣]', word):
            pattern = rf'(?<![가-힣]){re.escape(word)}(?![가-힣])'
        else:
            pattern = rf'\b{re.escape(word)}\b'
        
        return len(re.findall(pattern, text))
        
    def _add_references(self, content, research_data):
        """
        콘텐츠에 참고자료 섹션 추가
        
        Args:
            content (str): 원본 콘텐츠
            research_data (dict): 연구 자료 데이터
            
        Returns:
            str: 참고자료가 추가된 콘텐츠
        """
        # 이미 참고자료 섹션이 있는지 확인
        if "## 참고자료" in content:
            return content
        
        # 인용된 참고자료 추출
        references = []
        
        # 뉴스 자료 중 인용된 자료 찾기
        for source in research_data.get('news', []):
            if self._find_citation_in_content(content, source):
                references.append({
                    'title': source.get('title', ''),
                    'url': source.get('url', ''),
                    'source': source.get('source', '')
                })
        
        # 학술 자료 중 인용된 자료 찾기
        for source in research_data.get('academic', []):
            if self._find_citation_in_content(content, source):
                references.append({
                    'title': source.get('title', ''),
                    'url': source.get('url', ''),
                    'source': source.get('source', '')
                })
        
        # 일반 자료 중 인용된 자료 찾기
        for source in research_data.get('general', []):
            if self._find_citation_in_content(content, source):
                references.append({
                    'title': source.get('title', ''),
                    'url': source.get('url', ''),
                    'source': source.get('source', '')
                })
        
        # 통계 자료의 출처 추가
        for stat in research_data.get('statistics', []):
            source_url = stat.get('source_url', '')
            source_title = stat.get('source_title', '')
            
            # 이미 추가된 출처는 건너뛰기
            if any(ref.get('url') == source_url for ref in references):
                continue
                
            if source_url and source_title and self._find_citation_in_content(content, {'title': source_title, 'snippet': stat.get('context', '')}):
                references.append({
                    'title': source_title,
                    'url': source_url,
                    'source': stat.get('source', '')
                })
        
        # 참고자료가 없으면 원본 그대로 반환
        if not references:
            return content
        
        # 참고자료 섹션 추가
        reference_section = "\n\n## 참고자료\n"
        
        for i, ref in enumerate(references, 1):
            title = ref.get('title', '제목 없음')
            url = ref.get('url', '#')
            source = ref.get('source', '')
            
            # 출처 정보 포함
            if source:
                reference_section += f"{i}. [{title}]({url}) - {source}\n"
            else:
                reference_section += f"{i}. [{title}]({url})\n"
        
        return content + reference_section

    def _extract_references(self, content):
        """
        콘텐츠에서 참고자료 링크 추출
        
        Args:
            content (str): 콘텐츠
            
        Returns:
            list: 참고자료 목록
        """
        references = []
        
        # 참고자료 섹션 찾기
        if "## 참고자료" in content:
            refs_section = content.split("## 참고자료", 1)[1]
            
            # 마크다운 링크 추출 패턴
            link_pattern = r'\[(.*?)\]\((.*?)\)'
            matches = re.findall(link_pattern, refs_section)
            
            for title, url in matches:
                # 출처 정보 추출 (있는 경우)
                source = ""
                if " - " in title:
                    title_parts = title.split(" - ", 1)
                    title = title_parts[0]
                    source = title_parts[1]
                
                references.append({
                    'title': title.strip(),
                    'url': url.strip(),
                    'source': source.strip()
                })
        
        return references

    def _format_for_mobile(self, content):
        """
        모바일 화면에 최적화된 포맷으로 변환
        한글 기준 23자 내외로 줄바꿈 처리
        """
        # 제목, 소제목 처리 (마크다운 형식 유지)
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            # 마크다운 제목은 그대로 유지
            if line.strip().startswith('#'):
                formatted_lines.append(line)
                continue
                
            # 빈 줄은 그대로 유지
            if not line.strip():
                formatted_lines.append(line)
                continue
                
            # 목록(리스트) 항목은 그대로 유지
            if line.strip().startswith(('- ', '* ', '1. ', '2. ', '3. ')):
                formatted_lines.append(line)
                continue
            
            # 일반 텍스트는 23자 내외로 분리
            words = line.split()
            current_line = ""
            
            for word in words:
                # 현재 줄 + 새 단어가 23자를 초과하면 새 줄로
                if len((current_line + " " + word).replace(" ", "")) > 23 and current_line:
                    formatted_lines.append(current_line)
                    current_line = word
                else:
                    current_line = (current_line + " " + word).strip()
            
            # 마지막 줄 추가
            if current_line:
                formatted_lines.append(current_line)
        
        return '\n'.join(formatted_lines)
    
    def _find_citation_in_content(self, content, source_info):
        """
        본문에서 인용 여부 확인
        
        Args:
            content (str): 본문 콘텐츠
            source_info (dict): 출처 정보
            
        Returns:
            bool: 인용 여부
        """
        content_lower = content.lower()
        title = source_info.get('title', '').lower()
        author = source_info.get('source', '').lower()
        snippet = source_info.get('snippet', '').lower()
        
        # 출처 이름 확인
        source_name = None
        if author and len(author) > 2:
            source_name = author
        elif title:
            # 제목에서 가능한 출처 이름 추출 (첫 몇 단어)
            title_words = title.split()
            if len(title_words) >= 2:
                source_name = ' '.join(title_words[:2])
        
        # 출처 이름이 본문에서 언급되었는지 확인
        if source_name and source_name in content_lower:
            return True
        
        # 인용 패턴 확인
        citation_patterns = [
            "에 따르면",
            "의 연구에 따르면",
            "의 조사에 따르면",
            "의 보고서에 따르면",
            "에서 발표한",
            "의 발표에 따르면",
            "에서 조사한",
            "의 통계에 의하면",
            "에서 제시한",
            "의 자료에 따르면"
        ]
        
        # 1. 제목이나 스니펫에서 핵심 정보 추출
        numbers = re.findall(r'\d+(?:\.\d+)?%?', snippet)
        key_phrases = re.findall(r'[^\s,]+\s[^\s,]+\s[^\s,]+', snippet)
        
        # 2. 인용 패턴과 함께 핵심 정보가 사용되었는지 확인
        for pattern in citation_patterns:
            for number in numbers:
                if f"{pattern} {number}" in content_lower:
                    return True
            for phrase in key_phrases:
                if f"{pattern} {phrase}" in content_lower:
                    return True
        
        # 3. 제목이나 스니펫의 핵심 내용이 본문에 포함되어 있는지 확인
        # 최소 3단어 이상의 연속된 구문이 일치하는지 확인
        title_phrases = re.findall(r'[^\s,]+\s[^\s,]+\s[^\s,]+', title)
        snippet_phrases = re.findall(r'[^\s,]+\s[^\s,]+\s[^\s,]+', snippet)
        
        for phrase in title_phrases + snippet_phrases:
            if phrase in content_lower:
                return True
        
        return False
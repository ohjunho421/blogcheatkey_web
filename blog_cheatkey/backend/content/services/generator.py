import re
import json
import logging
import time
from urllib.parse import urlparse
from django.conf import settings
from konlpy.tag import Okt
from anthropic import Anthropic
from research.models import ResearchSource, StatisticData
from key_word.models import Keyword, Subtopic
from content.models import BlogContent, MorphemeAnalysis
from accounts.models import User

logger = logging.getLogger(__name__)


class ContentGenerator:
    """
    Claude API를 사용한 블로그 콘텐츠 생성 서비스
    """
    
    def __init__(self):
        self.anthropic_api_key = settings.ANTHROPIC_API_KEY
        self.model = "claude-3-opus-20240229"  # 최신 모델로 업데이트 필요
        self.client = Anthropic(api_key=self.anthropic_api_key)
        self.okt = Okt()
        self.max_retries = 3
        self.retry_delay = 2
    
    def generate_content(self, keyword_id, user_id, target_audience=None, business_info=None, custom_morphemes=None):
        """
        키워드 기반 블로그 콘텐츠 생성
        
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
                
                # 이미 생성된 콘텐츠가 있는지 확인
                existing_content = BlogContent.objects.filter(keyword=keyword, user=user).order_by('-created_at').first()
                
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
                
                # 이미 생성 중인 콘텐츠가 있는지 확인 (1시간 이내)
                one_hour_ago = time.time() - 3600
                if existing_content and existing_content.created_at.timestamp() > one_hour_ago:
                    logger.info(f"이미 생성된 콘텐츠가 있습니다: {existing_content.id}")
                    return existing_content.id
                
                # 프롬프트 생성 및 콘텐츠 생성
                prompt = self._create_content_prompt(data)
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    temperature=0.7,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                content = response.content[0].text
                
                # 콘텐츠 최적화 필요 여부 확인
                if self._needs_optimization(content, keyword.keyword):
                    optimization_prompt = self._create_optimization_prompt(content, data)
                    optimization_response = self.client.messages.create(
                        model=self.model,
                        max_tokens=4096,
                        temperature=0.5,
                        messages=[
                            {"role": "user", "content": optimization_prompt}
                        ]
                    )
                    content = optimization_response.content[0].text
                
                # 참고 자료 추가
                content_with_references = self._add_references(content, data['research_data'])
                
                # 모바일 최적화 포맷 생성
                mobile_formatted_content = self._format_for_mobile(content_with_references)
                
                # 참고 자료 목록 추출
                references = self._extract_references(content_with_references)
                
                # 이전 콘텐츠가 있다면 삭제
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
                
                return blog_content.id
                
            except Exception as e:
                logger.error(f"콘텐츠 생성 중 오류 발생: {str(e)}")
                if 'overloaded_error' in str(e) and attempt < self.max_retries - 1:
                    logger.warning(f"서버가 혼잡합니다. {self.retry_delay}초 후 재시도합니다... ({attempt + 1}/{self.max_retries})")
                    time.sleep(self.retry_delay)
                    continue
                raise e
        
        return None
    
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
                'date': stat.source.published_date.isoformat() if stat.source.published_date else ''
            })
        
        return research_data
    
    def _create_content_prompt(self, data):
        """
        콘텐츠 생성 프롬프트 생성
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

        # 프롬프트에 추가 지시사항 반영
        prompt = f"""
        다음 조건들을 준수하여 전문성과 친근함이 조화된, 읽기 쉽고 실용적인 블로그 글을 작성해주세요:

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
    
    def _needs_optimization(self, content, keyword):
        """
        콘텐츠가 최적화가 필요한지 판단
        
        Args:
            content (str): 분석할 콘텐츠
            keyword (str): 키워드
            
        Returns:
            bool: 최적화 필요 여부
        """
        # 형태소 분석 결과 가져오기
        analysis = self.analyze_morphemes(content, keyword)
        
        # 형태소 분석 결과에 이미 needs_optimization 필드가 있으면 그 값 사용
        if 'needs_optimization' in analysis:
            return analysis['needs_optimization']
        
        # 아니면 분석 결과를 기반으로 판단
        # 하나라도 유효하지 않은 형태소가 있으면 최적화 필요
        return not analysis.get('is_valid', True)

    def _create_optimization_prompt(self, content, data):
        """
        콘텐츠 최적화 프롬프트 생성
        """
        keyword = data['keyword']
        morphemes = data.get('morphemes', self.okt.morphs(keyword))
        
        analysis = self.analyze_morphemes(content, keyword)
        current_counts = {word: info["count"] for word, info in analysis["morpheme_analysis"].items()}
        
        # 동적으로 예시 생성
        example_instructions = f"""
        1. 동의어/유의어로 대체:
        - '{keyword}' 또는 각 형태소를 자연스러운 동의어/유의어로 대체
        - 해당 분야의 전문용어와 일반적인 표현을 적절히 혼용
        
        2. 문맥상 자연스러운 생략:
        - "{keyword}가 중요합니다" → "중요합니다"
        - "{keyword}를 살펴보면" → "살펴보면"
        
        3. 지시어로 대체:
        - "{keyword}는" → "이것은"
        - "{keyword}의 경우" → "이 경우"
        - "이", "이것", "해당", "이러한" 등의 지시어 활용
        """

        return f"""
        다음 블로그 글을 최적화해주세요. 다음의 출현 횟수 제한을 반드시 지켜주세요:

        🎯 목표:
        1. 키워드 '{keyword}': 정확히 17-20회 사용
        2. 각 형태소({', '.join(morphemes)}): 정확히 17-20회 사용
        
        📊 현재 상태:
        {chr(10).join([f"- '{word}': {count}회" for word, count in current_counts.items()])}

        ✂️ 과다 사용된 단어 최적화 방법 (우선순위 순):
        {example_instructions}

        ⚠️ 중요:
        - 각 형태소와 키워드가 정확히 17-20회 범위 내에서 사용되어야 함
        - ctrl+f로 검색했을 때의 횟수를 기준으로 함
        - 전체 문맥의 자연스러움을 반드시 유지
        - 전문성과 가독성의 균형 유지
        - 동의어/유의어 사용을 우선으로 하고, 자연스러운 경우에만 생략이나 지시어 사용
        - 본문에서 [1], [2]와 같은 인용번호는 절대로 사용하지 마세요. 대신 출처 이름을 직접 언급하세요.

        원문:
        {content}

        위 지침에 따라 과다 사용된 형태소들을 최적화하여 모든 형태소가 17-20회 범위 내에 들도록 
        자연스럽게 수정해주세요. 전문성은 유지하되 읽기 쉽게 수정해주세요.
        """
    
    def analyze_morphemes(self, text, keyword=None, custom_morphemes=None):
        """형태소 분석 및 출현 횟수 검증"""
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
        텍스트에서 특정 단어의 정확한 출현 횟수를 계산합니다.
        
        Args:
            word (str): 찾을 단어
            text (str): 검색할 텍스트
            
        Returns:
            int: 단어의 출현 횟수
        """
        pattern = rf'\b{word}\b|\b{word}(?=[\s.,!?])|(?<=[\s.,!?]){word}\b'
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
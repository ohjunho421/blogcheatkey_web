import re
import json
import logging
import time
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
    
    def generate_content(self, keyword_id, user_id, target_audience=None, business_info=None):
        """
        키워드 기반 블로그 콘텐츠 생성
        
        Args:
            keyword_id (int): 키워드 ID
            user_id (int): 사용자 ID
            target_audience (dict): 타겟 독자 정보
            business_info (dict): 사업자 정보
            
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
                
                # 형태소 분석
                morphemes = self.okt.morphs(keyword.keyword)
                
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
                
                # 모바일 최적화 포맷 생성
                mobile_formatted_content = self._format_for_mobile(content)
                
                # 참고 자료 추가
                content_with_references = self._add_references(content, data['research_data'])
                
                # 콘텐츠 저장
                blog_content = BlogContent.objects.create(
                    user=user,
                    keyword=keyword,
                    title=f"{keyword.keyword} 완벽 가이드",  # 기본 제목, 나중에 변경 가능
                    content=content_with_references,
                    mobile_formatted_content=self._format_for_mobile(content_with_references),
                    references=self._extract_references(content_with_references),
                    char_count=len(content.replace(" ", "")),
                    is_optimized=True
                )
                
                # 형태소 분석 결과 저장
                morpheme_analysis = self.analyze_morphemes(content, keyword.keyword)
                for morpheme, info in morpheme_analysis.get('morpheme_analysis', {}).items():
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

        **추가 지시사항:**
        1. 각 소제목 중 최소 2개 소제목에 대해서는 해당 소제목과 직접 연관된 기사나 통계자료를 최소 1건 이상 인용하여 내용을 보강해 주세요.
        2. 생성된 글 내에 [숫자] 형태의 인용 표기가 있을 경우, 그 숫자에 해당하는 연구 자료의 링크를 활용하거나, 글의 참고자료 섹션에서 해당 링크를 명확하게 표시해 주세요.
        예를 들어, "브레이크라이닝의 구조와 작동 원리[2][6]"라면, [2]와 [6]에 연결된 링크(출처)가 실제로 활용되도록 작성해 주세요.

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
        - "최근 연구에 따르면..." 또는 "...의 통계에 의하면..."과 같은 방식으로 시작
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
        - 모든 통계와 수치는 출처를 구체적으로 명시 (예: "2024년 OO연구소의 조사에 따르면...")
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

        원문:
        {content}

        위 지침에 따라 과다 사용된 형태소들을 최적화하여 모든 형태소가 17-20회 범위 내에 들도록 
        자연스럽게 수정해주세요. 전문성은 유지하되 읽기 쉽게 수정해주세요.
        """
    
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
    
    def _extract_references(self, content):
        """
        콘텐츠에서 참고 자료 목록 추출
        """
        references = []
        
        # 참고자료 섹션 추출
        if "## 참고자료" in content:
            refs_section = content.split("## 참고자료")[1]
            
            # URL 추출
            urls = re.findall(r'\[.+?\]\((.+?)\)', refs_section)
            
            # 제목 추출
            titles = re.findall(r'\[(.+?)\]', refs_section)
            
            # 참고 자료 맵핑
            for i in range(min(len(urls), len(titles))):
                references.append({
                    'title': titles[i],
                    'url': urls[i]
                })
        
        return references
    
    def _find_citation_in_content(self, content, source_info):
        """
        본문에서 인용 여부 확인
        """
        content_lower = content.lower()
        title = source_info.get('title', '').lower()
        snippet = source_info.get('snippet', '').lower()
        
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
    
    def _add_references(self, content, research_data):
        """
        콘텐츠에 참고자료 추가
        """
        used_sources = []
        all_sources = []
        
        # 1. 모든 소스 수집 및 분류
        for source_type, items in research_data.items():
            if not isinstance(items, list):
                continue
                    
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = item.get('title', '')
                url = item.get('url', '')
                snippet = item.get('snippet', '').lower()
                date = item.get('date', '')
                source = item.get('source', '')
                
                if not url:  # URL이 없는 경우 건너뛰기
                    continue
                
                source_info = {
                    'type': source_type,
                    'title': title,
                    'url': url,
                    'date': date,
                    'source': source,
                    'snippet': snippet
                }
                
                # 본문에서 사용된 자료 확인 (인용 여부 판단)
                if self._find_citation_in_content(content, source_info):
                    used_sources.append(source_info)
                
                all_sources.append(source_info)
        
        # 2. 본문에서 [n] 형식의 인용 표기 제거
        clean_content = re.sub(r'\[\d+\]', '', content)
        
        # 3. 참고자료 섹션 추가
        references_section = "\n\n---\n## 참고자료\n"
        
        # 본문에서 인용된 자료 (클릭 가능한 링크로 표시)
        if used_sources:
            references_section += "\n### 📚 본문에서 인용된 자료\n"
            for idx, source in enumerate(used_sources, start=1):
                title = source['title']
                url = source['url']
                date = source['date']
                source_name = source['source']
                
                if date:
                    references_section += f"{idx}. [{title}]({url}) ({date}) - {source_name}\n"
                else:
                    references_section += f"{idx}. [{title}]({url}) - {source_name}\n"
        
        # 추가 참고자료
        references_section += "\n### 🔍 추가 참고자료\n"
        
        # 뉴스 자료
        news_sources = [s for s in all_sources if s['type'] == 'news' and s not in used_sources]
        if news_sources:
            references_section += "\n#### 📰 뉴스 자료\n"
            for idx, source in enumerate(news_sources, start=1):
                if source['date']:
                    references_section += f"{idx}. [{source['title']}]({source['url']}) ({source['date']}) - {source['source']}\n"
                else:
                    references_section += f"{idx}. [{source['title']}]({source['url']}) - {source['source']}\n"
        
        # 학술/연구 자료
        academic_sources = [s for s in all_sources if s['type'] == 'academic' and s not in used_sources]
        if academic_sources:
            references_section += "\n#### 📚 학술/연구 자료\n"
            for idx, source in enumerate(academic_sources, start=1):
                references_section += f"{idx}. [{source['title']}]({source['url']})\n"
        
        # 일반 자료
        general_sources = [s for s in all_sources if s['type'] == 'general' and s not in used_sources]
        if general_sources:
            references_section += "\n#### 🔍 일반 검색 결과\n"
            for idx, source in enumerate(general_sources, start=1):
                references_section += f"{idx}. [{source['title']}]({source['url']})\n"
        
        # 4. 정리된 본문과 참고자료 섹션 결합
        final_content = clean_content.split("---")[0].strip() + references_section
        
        return final_content
# formatter.py
import re
import logging
import json

logger = logging.getLogger(__name__)

class ContentFormatter:
    """
    블로그 콘텐츠 포맷팅을 위한 유틸리티 클래스
    """
    
    @staticmethod
    def format_for_mobile(content):
        """
        모바일 화면에 최적화된 포맷으로 변환
        한글 기준 23자 내외로 줄바꿈 처리
        
        Args:
            content (str): 변환할 원본 콘텐츠
            
        Returns:
            str: 모바일 최적화된 콘텐츠
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
    
    @staticmethod
    def format_with_references(content, research_data):
        """
        콘텐츠에 참고자료 목록 추가
        
        Args:
            content (str): 원본 콘텐츠
            research_data (dict): 연구 자료 데이터
            
        Returns:
            str: 참고자료가 추가된 콘텐츠
        """
        # 본문에서 [n] 형식의 인용 표기 제거
        clean_content = re.sub(r'\[\d+\]', '', content)
        
        # 참고자료 섹션 추가
        references_section = "\n\n---\n## 참고자료\n"
        
        # 사용된 출처 목록 생성
        used_sources = []
        all_sources = []
        
        # 자료 수집 및 분류
        for source_type, items in research_data.items():
            if not isinstance(items, list):
                continue
                
            for item in items:
                if not isinstance(item, dict):
                    continue
                    
                url = item.get('url', '')
                if not url:  # URL이 없는 경우 건너뛰기
                    continue
                    
                source_info = {
                    'type': source_type,
                    'title': item.get('title', ''),
                    'url': url,
                    'date': item.get('date', ''),
                    'source': item.get('source', ''),
                    'snippet': item.get('snippet', '').lower()
                }
                
                # 본문에서 사용된 자료 확인 (인용 여부 판단)
                if ContentFormatter._find_citation_in_content(clean_content, source_info):
                    used_sources.append(source_info)
                
                all_sources.append(source_info)
        
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
        
        # 자료 유형별 정렬
        news_sources = [s for s in all_sources if s['type'] == 'news' and s not in used_sources]
        academic_sources = [s for s in all_sources if s['type'] == 'academic' and s not in used_sources]
        general_sources = [s for s in all_sources if s['type'] == 'general' and s not in used_sources]
        
        # 뉴스 자료
        if news_sources:
            references_section += "\n#### 📰 뉴스 자료\n"
            for idx, source in enumerate(news_sources, start=1):
                if source['date']:
                    references_section += f"{idx}. [{source['title']}]({source['url']}) ({source['date']}) - {source['source']}\n"
                else:
                    references_section += f"{idx}. [{source['title']}]({source['url']}) - {source['source']}\n"
        
        # 학술/연구 자료
        if academic_sources:
            references_section += "\n#### 📚 학술/연구 자료\n"
            for idx, source in enumerate(academic_sources, start=1):
                references_section += f"{idx}. [{source['title']}]({source['url']})\n"
        
        # 일반 자료
        if general_sources:
            references_section += "\n#### 🔍 일반 검색 결과\n"
            for idx, source in enumerate(general_sources, start=1):
                references_section += f"{idx}. [{source['title']}]({source['url']})\n"
        
        # 4. 정리된 본문과 참고자료 섹션 결합
        final_content = clean_content.split("---")[0].strip() + references_section
        
        return final_content
    
    @staticmethod
    def extract_references(content):
        """
        콘텐츠에서 참고 자료 목록 추출
        
        Args:
            content (str): 콘텐츠
            
        Returns:
            list: 참고 자료 목록
        """
        references = []
        
        try:
            # 참고자료 섹션 추출
            if "## 참고자료" in content:
                refs_section = content.split("## 참고자료")[1]
                
                # URL 추출 - 마크다운 링크 패턴 [제목](URL)
                link_pattern = r'\[(.*?)\]\((https?:\/\/[^\s)]+)\)'
                matches = re.findall(link_pattern, refs_section)
                
                for title, url in matches:
                    references.append({
                        'title': title.strip(),
                        'url': url.strip()
                    })
                
                # 결과 로깅
                logger.info(f"추출된 참고자료 {len(references)}개: {json.dumps(references, ensure_ascii=False)}")
            
        except Exception as e:
            logger.error(f"참고자료 추출 중 오류: {str(e)}")
        
        return references
    
    @staticmethod
    def _find_citation_in_content(content, source_info):
        """
        본문에서 인용 여부 확인
        
        Args:
            content (str): 검사할 콘텐츠
            source_info (dict): 출처 정보
            
        Returns:
            bool: 인용 여부
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
# formatter.py
import re
import json
import logging
import traceback

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
    def format_with_references(content, research_data=None):
        """
        콘텐츠에 참고자료 목록 추가
        
        Args:
            content (str): 원본 콘텐츠
            research_data (dict, optional): 연구 자료 데이터
            
        Returns:
            str: 참고자료가 추가된 콘텐츠
        """
        # 본문에서 [n] 형식의 인용 표기 제거
        clean_content = re.sub(r'\[\d+\]', '', content)
        
        # 통계 및 형태소 정보 제거 (총 글자수, 키워드 횟수 등)
        main_content_lines = clean_content.split('\n')
        filtered_lines = []
        skip_section = False
        
        for line in main_content_lines:
            # 총 글자수 및 키워드 출현 횟수 섹션 감지 및 제거
            if line.strip().startswith('총 글자수:') or line.strip().startswith('주요 키워드'):
                skip_section = True
                continue
            
            # 빈 줄을 만나면 스킵 상태 초기화
            if skip_section and not line.strip():
                skip_section = False
                continue
                
            # 필터링된 라인 추가
            if not skip_section:
                filtered_lines.append(line)
        
        # 정리된 본문 콘텐츠
        cleaned_main_content = '\n'.join(filtered_lines)
        
        # 참고자료 섹션 작성
        references_html = ""
        
        # 참고자료 섹션 추가 - 복사시 제외되도록 특정 ID/클래스를 사용
        if research_data or ContentFormatter.extract_references(content):
            references_html = """\n\n<!-- 참고자료 섹션 시작 -->\n
<hr id="references-divider" class="references-divider" data-section="references" />\n
<div id="references-section" class="references-section" data-content="references">\n
<h2 id="references-title" class="references-title">참고자료</h2>\n"""
            
            # 참고자료 추출
            references = []
            
            # 1. 콘텐츠에서 자동 추출
            extracted_refs = ContentFormatter.extract_references(content)
            if extracted_refs:
                references_html += "<h3 class='ref-subtitle'>콘텐츠에서 추출한 참고자료</h3>\n<ul class='ref-list'>\n"
                for idx, ref in enumerate(extracted_refs, start=1):
                    references_html += f"<li class='ref-item'>{idx}. <a href='{ref['url']}' class='ref-link' target='_blank'>{ref['title']}</a></li>\n"
                references_html += "</ul>\n"
            
            # 2. 연구 데이터에서 추출 (있는 경우)
            if research_data:
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
                            
                        # 모든 자료 목록에 추가
                        all_sources.append(source_info)
                    
                # 분류된 자료 목록 추가
                
                # 2-1. 인용된 자료
                if used_sources:
                    references_html += "<h3 class='ref-subtitle'>인용된 자료</h3>\n<ul class='ref-list'>\n"
                    for idx, source in enumerate(used_sources, start=1):
                        source_text = f"{source['title']}"
                        if source['source']:
                            source_text += f" - {source['source']}"
                        references_html += f"<li class='ref-item'>{idx}. <a href='{source['url']}' class='ref-link' target='_blank'>{source_text}</a></li>\n"
                    references_html += "</ul>\n"
                
                # 자료 유형별 분류
                official_sources = [s for s in all_sources if s['type'] in ['government', 'official', 'research']]
                academic_sources = [s for s in all_sources if s['type'] in ['academic', 'paper']]
                general_sources = [s for s in all_sources if s['type'] not in ['government', 'official', 'research', 'academic', 'paper']]
                
                # 2-2. 공식/정부 자료
                if official_sources:
                    references_html += "<h3 class='ref-subtitle'>공식/정부 자료</h3>\n<ul class='ref-list'>\n"
                    for idx, source in enumerate(official_sources[:5], start=1):
                        references_html += f"<li class='ref-item'>{idx}. <a href='{source['url']}' class='ref-link' target='_blank'>{source['title']}</a></li>\n"
                    references_html += "</ul>\n"
                
                # 2-3. 학술/연구 자료
                if academic_sources:
                    references_html += "<h3 class='ref-subtitle'>학술/연구 자료</h3>\n<ul class='ref-list'>\n"
                    for idx, source in enumerate(academic_sources, start=1):
                        references_html += f"<li class='ref-item'>{idx}. <a href='{source['url']}' class='ref-link' target='_blank'>{source['title']}</a></li>\n"
                    references_html += "</ul>\n"
                
                # 2-4. 일반 자료
                if general_sources:
                    references_html += "<h3 class='ref-subtitle'>일반 검색 결과</h3>\n<ul class='ref-list'>\n"
                    for idx, source in enumerate(general_sources, start=1):
                        references_html += f"<li class='ref-item'>{idx}. <a href='{source['url']}' class='ref-link' target='_blank'>{source['title']}</a></li>\n"
                    references_html += "</ul>\n"
            
            # 참고자료 섹션 마무리 태그 추가
            references_html += "</div>\n<!-- 참고자료 섹션 끝 -->\n"       
        # 5. 복사 버튼 및 스크립트 추가 - 완전히 새로운 접근법으로 참고자료 제외
        copy_script = """
        <script>
        // 순수 본문만 복사하는 기능 - 완전히 새로운 접근방식 사용
        function copyTextWithoutReferences() {
            try {
                alert('본문만 복사중... 참고자료 및 링크는 제외합니다.');
                
                // 본문 영역만 명확히 선택하여 복사
                const mainContentElem = document.querySelector('#main-content');
                
                // 메인 콘텐츠가 없으면 기본 요소 활용
                if (!mainContentElem) {
                    console.log('본문 요소를 찾을 수 없어 대체 방법 사용');
                    return copyFallback();
                }
                
                // 순수 본문만 선택하여 복사
                const range = document.createRange();
                range.selectNodeContents(mainContentElem);
                
                // 현재 선택된 내용 있으면 제거
                const selection = window.getSelection();
                selection.removeAllRanges();
                selection.addRange(range);
                
                // 복사 실행
                document.execCommand('copy');
                
                // 선택 해제
                selection.removeAllRanges();
                
                alert('본문만 성공적으로 복사되었습니다.');
                return true;
            } catch (error) {
                console.error('본문 복사 중 오류:', error);
                return copyFallback();
            }
        }
        
        // 기본 복사 방법 - #main-content가 없을 경우 사용
        function copyFallback() {
            try {
                console.log('대체 복사 방법 실행');
                
                let mainContent = document.querySelector('main') || document.querySelector('article') || document.querySelector('.content') || document.body;
                let clonedContent = mainContent.cloneNode(true);
                
                // 1. 참고자료 섹션 완전 제거
                // 1-1. ID나 클래스로 참고자료 영역 찾기
                const refSections = clonedContent.querySelectorAll('#references-section, .references-section, [data-section="references"], [id*="reference"], [class*="reference"]');
                refSections.forEach(section => section.remove());
                
                // 1-2. 태그로 참고자료 영역 찾기
                const refTitles = clonedContent.querySelectorAll('h2, h3, h4, h5');
                refTitles.forEach(title => {
                    if (title.textContent.includes('참고자료') || 
                        title.textContent.toLowerCase().includes('reference')) {
                        // 제목 잠시 저장
                        const refTitle = title;
                        
                        // 해당 제목 아래 모든 요소 제거
                        let nextSibling = refTitle.nextElementSibling;
                        while (nextSibling) {
                            const temp = nextSibling;
                            nextSibling = nextSibling.nextElementSibling;
                            temp.remove();
                        }
                        
                        // 제목 제거
                        refTitle.remove();
                    }
                });
                
                // 1-3. 링크 바로가기 버튼 및 영역 제거
                const linkButtons = clonedContent.querySelectorAll('a[href], a.btn, button');
                linkButtons.forEach(button => {
                    if ((button.textContent.includes('링크') || 
                         button.textContent.includes('바로가기') || 
                         button.textContent.toLowerCase().includes('link')) &&
                        button.closest('a[href]')) {
                        
                        // 버튼이 포함된 섹션 찾기
                        const container = button.closest('div, p, li, section');
                        if (container) {
                            container.remove();
                        } else {
                            button.remove();
                        }
                    }
                });
                
                // 1-4. URL 포함된 마지막 단락 제거
                const paragraphs = clonedContent.querySelectorAll('p');
                paragraphs.forEach(p => {
                    if (p.textContent.includes('http://') || 
                        p.textContent.includes('https://')) {
                        p.remove();
                    }
                });
                
                // 2. 추가 시례 파악을 위한 로직
                // 2-1. --- 표시(구분선) 후의 모든 콘텐츠 삭제 (참고자료 섹션 시작 표시)
                const hrElements = clonedContent.querySelectorAll('hr');
                hrElements.forEach(hr => {
                    // 구분선 후의 모든 요소 제거 (참고자료 후에 표시되는 구분선)
                    let nextElement = hr.nextElementSibling;
                    while (nextElement) {
                        const temp = nextElement;
                        nextElement = nextElement.nextElementSibling;
                        temp.remove();
                    }
                    hr.remove(); // 구분선도 제거
                });
                
                // 2-2. "참고자료:" 텝스트로 시작하는 요소의 다음 요소들 제거
                const allElements = clonedContent.querySelectorAll('*');
                for (let i = 0; i < allElements.length; i++) {
                    if (allElements[i].textContent.trim().startsWith('참고자료:')) {
                        // 해당 요소와 그 다음 요소들 모두 제거
                        let current = allElements[i];
                        while (current) {
                            const next = current.nextElementSibling;
                            current.remove();
                            current = next;
                        }
                        break; // 처리 완료 후 중단
                    }
                }
                
                // 2. h2-h4 태그 중 참고자료 관련 요소 및 그 하위 모든 요소 제거
                const headings = clonedContent.querySelectorAll('h2, h3, h4');
                headings.forEach(heading => {
                    const headingText = heading.textContent.toLowerCase();
                    if (refKeywords.some(kw => headingText.includes(kw.toLowerCase()))) {
                        // 해당 제목 아래의 모든 요소 제거 (형제 요소)
                        let nextElement = heading.nextElementSibling;
                        while (nextElement) {
                            const nextHeadingLevel = nextElement.tagName ? parseInt(nextElement.tagName.substring(1)) : 0;
                            const currentHeadingLevel = parseInt(heading.tagName.substring(1));
                            
                            // 다음 요소가 같거나 더 낮은 레벨의 제목이면 중지
                            if (nextElement.tagName && nextElement.tagName.match(/^H\d$/) && nextHeadingLevel <= currentHeadingLevel) {
                                break;
                            }
                            
                            const temp = nextElement.nextElementSibling;
                            nextElement.remove();
                            nextElement = temp;
                        }
                        // 제목도 제거
                        heading.remove();
                    }
                });
                
                // 2-1. "링크 바로가기" 버튼이 포함된 요소 제거 (강화된 방식)
                // a. 모든 버튼 검색
                const allButtons = clonedContent.querySelectorAll('button, a.btn, .button, [class*="btn"], [role="button"]');
                allButtons.forEach(button => {
                    // 링크 바로가기 관련 텍스트가 포함된 버튼 및 요소 찾기 (강화된 방식)
                    if (button.textContent.includes('링크 바로가기') || 
                        button.textContent.includes('바로가기') || 
                        button.textContent.includes('링크') || 
                        button.textContent.toLowerCase().includes('link') ||
                        (button.getAttribute('href') && button.getAttribute('href').includes('http')) ||
                        button.classList.contains('ref-link')) {
                        
                        // 버튼이 있는 전체 섹션/항목 제거
                        let parent = button.parentNode;
                        
                        // 버튼이 있는 섹션을 찾아 올라가기 (li, div, section, article, p 등)
                        while (parent && !['LI', 'DIV', 'P', 'SECTION', 'ARTICLE', 'UL', 'OL'].includes(parent.tagName)) {
                            parent = parent.parentNode;
                        }
                        
                        // 참고자료 섹션 이름이 포함된 상위 섹션 찾기
                        let refSection = parent;
                        while (refSection) {
                            // 섹션 제목이나 텍스트에 참고자료 관련 키워드가 있는지 확인
                            const sectionText = refSection.textContent.toLowerCase();
                            if (refKeywords.some(kw => sectionText.includes(kw.toLowerCase()))) {
                                // 참고자료 섹션 전체 제거
                                refSection.remove();
                                return; // 이 버튼 처리 완료
                            }
                            refSection = refSection.parentNode;
                        }
                        
                        // 상위 참고자료 섹션을 찾지 못한 경우
                        if (parent) {
                            // 현재 버튼의 부모 요소와 그 형제 요소들 제거
                            const grandParent = parent.parentNode;
                            if (grandParent) {
                                // 같은 레벨의 링크 바로가기 관련 항목들 모두 제거
                                Array.from(grandParent.children).forEach(child => {
                                    if (child.textContent.includes('링크') || 
                                        child.textContent.includes('바로가기') || 
                                        child.textContent.toLowerCase().includes('link')) {
                                        child.remove();
                                    }
                                });
                            }
                            parent.remove(); // 버튼의 직접적인 부모 요소 제거
                        } else {
                            button.remove(); // 적절한 부모를 찾지 못한 경우 버튼만 제거
                        }
                    }
                });
                
                // b. 전체 "참고자료" 섹션 제거 - 링크 바로가기 버튼이 있는 부분 포함
                const refSections = clonedContent.querySelectorAll('section, div, article, aside');
                refSections.forEach(section => {
                    // 섹션 내용에 참고자료 관련 키워드가 있거나, 링크 바로가기 버튼이 포함되어 있는지 확인
                    const sectionText = section.textContent.toLowerCase();
                    const hasRefKeyword = refKeywords.some(kw => sectionText.includes(kw.toLowerCase()));
                    const hasLinkButton = section.querySelector('a[href], button') &&
                                        (sectionText.includes('링크 바로가기') || 
                                        sectionText.includes('바로가기'));
                    
                    if (hasRefKeyword || hasLinkButton) {
                        // 해당 섹션의 부모가 있는 경우, 전체 섹션 제거
                        if (section.tagName === 'SECTION' || section.tagName === 'ARTICLE' || 
                            (section.className && (section.className.includes('section') || 
                                                section.className.includes('reference') || 
                                                section.className.includes('footer')))) {
                            section.remove(); // 전체 섹션 제거
                        }
                        // 만약 class나 id에 참고자료 관련 키워드가 있는 경우도 제거
                        else if ((section.className && refKeywords.some(kw => section.className.toLowerCase().includes(kw.toLowerCase()))) ||
                                (section.id && refKeywords.some(kw => section.id.toLowerCase().includes(kw.toLowerCase())))) {
                            section.remove();
                        }
                    }
                });
                
                // 2-2. 참고자료 관련 모든 주석 및 메타데이터 제거
                const allElements = clonedContent.querySelectorAll('*');
                allElements.forEach(el => {
                    // data-* 속성에 참고자료 관련 문자열이 있는지 확인
                    for (const attr of el.attributes) {
                        if (attr.name.startsWith('data-') && 
                            refKeywords.some(kw => attr.value.toLowerCase().includes(kw.toLowerCase()))) {
                            el.remove();
                            break;
                        }
                    }
                    
                    // 요소의 클래스나 ID에 참고자료 관련 키워드가 포함되어 있는지 확인
                    if (el.id && refKeywords.some(kw => el.id.toLowerCase().includes(kw.toLowerCase()))) {
                        el.remove();
                    }
                    
                    if (el.className && typeof el.className === 'string' && 
                        refKeywords.some(kw => el.className.toLowerCase().includes(kw.toLowerCase()))) {
                        el.remove();
                    }
                });
                
                // 3. 링크 요소 제거 (a 태그) - 참고자료 링크 포함
                const links = clonedContent.querySelectorAll('a');
                links.forEach(link => {
                    const linkText = link.textContent.trim();
                    const linkHref = link.getAttribute('href') || '';
                    const parentText = link.parentNode ? link.parentNode.textContent.trim() : '';
                    
                    // 참고자료와 관련된 링크인지 확인 - 더 강화된 조건
                    const isRefLink = 
                        // 키워드 검사 (link 태그 텍스트)
                        refKeywords.some(kw => linkText.toLowerCase().includes(kw.toLowerCase())) ||
                        refKeywords.some(kw => linkText.toLowerCase().includes(kw)) ||
                        // 키워드 검사 (부모 요소 텍스트)
                        refKeywords.some(kw => parentText.toLowerCase().includes(kw)) ||
                        // 외부 URL 포함 여부
                        linkHref.includes('http://') || linkHref.includes('https://') ||
                        linkHref.includes('www.') ||
                        // 링크 종류 확인 (외부 링크 포함)
                        link.classList.contains('reference') ||
                        link.classList.contains('external') ||
                        // .com, .kr 등 도메인 연결 포함
                        ['.com', '.kr', '.net', '.org', '.go.kr', '.co.kr'].some(domain => linkHref.includes(domain));
                    
                    if (isRefLink) {
                        // 참고자료 링크는 완전히 제거
                        link.remove();
                    } else {
                        // 일반 링크는 텍스트만 남기고 a 태그 제거
                        const textNode = document.createTextNode(linkText);
                        link.parentNode.replaceChild(textNode, link);
                    }
                });
                
                // 4. 링크 관련 단락 제거
                const paragraphs = clonedContent.querySelectorAll('p');
                paragraphs.forEach(p => {
                    if (refKeywords.some(kw => p.textContent.toLowerCase().includes(kw))) {
                        p.remove();
                    }
                });
                
                // 5. 분리자(hr) 와 그 아래 콘텐츠 제거
                const dividers = clonedContent.querySelectorAll('hr');
                dividers.forEach(hr => {
                    let current = hr;
                    while (current.nextSibling) {
                        current.nextSibling.remove();
                    }
                    hr.remove();
                });
                
                // 6. 추가 검색 선택자
                const additionalElements = clonedContent.querySelectorAll(
                    'button, script, style, footer, nav, [class*="reference"], [class*="footer"], ' +
                    '[class*="cite"], .mt-6, .p-4, .bg-gray-50, .rounded-lg, ' + 
                    '[class*="tag"], [class*="meta"], [class*="author"], [id*="reference"]'
                );
                additionalElements.forEach(el => el.remove());
                
                // 7. 텍스트 추출 - 참고자료 및 링크 바로가기 관련 모든 내용 필터링 (강화)
                
                // 추가 삭제 - 'https://' 와 '참고자료', '링크 바로가기' 키워드가 포함된 섹션 제거
                const finalParagraphs = clonedContent.querySelectorAll('p, div, section');
                const referenceSectionStartKeywords = ['https://', 'http://', '참고자료', '참고'];
                
                // 마지막 부분에 있는 참고자료 섹션 찾기
                let lastReferenceIndex = -1;
                finalParagraphs.forEach((para, index) => {
                    // 참고자료 키워드나 URL이 포함된 단락 감지
                    if (referenceSectionStartKeywords.some(keyword => para.textContent.includes(keyword))) {
                        lastReferenceIndex = index;
                    }
                });
                
                // 마지막 참고자료 섹션부터 끝까지 부분 제거
                if (lastReferenceIndex >= 0) {
                    for (let i = lastReferenceIndex; i < finalParagraphs.length; i++) {
                        finalParagraphs[i].remove();
                    }
                }
                
                // 텍스트 추출
                let textContent = '';
                
                function extractText(node) {
                    // 텍스트 노드인 경우
                    if (node.nodeType === Node.TEXT_NODE) {
                        const text = node.textContent.trim();
                        // 참고자료 관련 키워드가 없는 경우만 추가
                        if (text && !refKeywords.some(kw => text.toLowerCase().includes(kw)) && 
                            !text.includes('function') && !text.includes('글자수:') && 
                            !text.includes('키워드:')) {
                            textContent += text + ' ';
                        }
                    } 
                    // 요소 노드인 경우 자식 탐색
                    else if (node.nodeType === Node.ELEMENT_NODE) {
                        // 제외할 태그 유형
                        const excludeTags = ['SCRIPT', 'STYLE', 'BUTTON', 'A', 'FOOTER', 'NAV', 'ASIDE', 'CITE'];
                        
                        // 참고자료 관련 키워드 포함 여부 확인
                        const hasRefKeyword = refKeywords.some(kw => {
                            return node.textContent.toLowerCase().includes(kw);
                        });
                        
                        if (!excludeTags.includes(node.tagName) && !hasRefKeyword) {
                            // 자식 노드 처리
                            node.childNodes.forEach(child => extractText(child));
                            
                            // 단락 구분
                            if (['P', 'DIV', 'H1', 'H2', 'H3', 'LI', 'BR', 'TR'].includes(node.tagName)) {
                                textContent += '\n\n';
                            }
                        }
                    }
                }
                
                // 텍스트 추출 실행
                extractText(clonedContent);
                
                // 4. 텍스트 정리
                // 개행 처리
                let cleanText = textContent.replace(/\n{3,}/g, '\n\n').trim();
                
                // 불필요한 타이틀 및 정보 제거
                cleanText = cleanText.replace(/\s*총\s*글자수.*?\n/g, '');
                cleanText = cleanText.replace(/\s*주요\s*키워드.*?\n/g, '');
                
                // 링크 표기 제거
                cleanText = cleanText.replace(/\[.*?\]\(.*?\)/g, '');
                cleanText = cleanText.replace(/https?:\/\/\S+/g, '');
                
                // HTML 태그 제거
                cleanText = cleanText.replace(/<[^>]*>/g, '');
                
                // 참고자료 관련 문구/섹션 완전히 제거
                refKeywords.forEach(keyword => {
                    // 각 줄의 시작부터 키워드가 있는 줄과 그 뒤 내용 제거
                    const regex = new RegExp(`\s*${keyword}.*$`, 'gim');
                    cleanText = cleanText.replace(regex, '');
                    
                    // 키워드가 포함된 전체 문장 제거 (색상응용)
                    const sentenceRegex = new RegExp(`[^.!?\n]*${keyword}[^.!?\n]*[.!?\n]`, 'gim');
                    cleanText = cleanText.replace(sentenceRegex, '');
                });
                
                // 참고자료 관련 완전한 문장 필터링
                const complexRefPatterns = [
                    /[^.!?\n]*(?:참고|참조|출처|출연)[^.!?\n]*[.!?\n]/gi,
                    /[^.!?\n]*(?:사용된 자료|참고 자료|참고문헌)[^.!?\n]*[.!?\n]/gi,
                    /[^.!?\n]*(?:http|www|\.[a-z]{2,})[^.!?\n]*[.!?\n]/gi,
                    /[^.!?\n]*(?:연구에 따르면|조사에 따르면)[^.!?\n]*(?:https?|www)[^.!?\n]*[.!?\n]/gi
                ];
                
                complexRefPatterns.forEach(pattern => {
                    cleanText = cleanText.replace(pattern, '');
                });
                
                // 링크 형태 파터도 한 번 더 검색
                cleanText = cleanText.replace(/\[.*?\]\(.*?\)/g, '');
                cleanText = cleanText.replace(/https?:\/\/\S+/g, '');
                cleanText = cleanText.replace(/www\.\S+/g, '');
                
                // 불필요한 공백 정리 (연속 공백을 하나로 통합)
                cleanText = cleanText.replace(/\s+/g, ' ').trim();
                
                // 임시 textarea 생성 및 복사
                const tempTextarea = document.createElement('textarea');
                tempTextarea.value = cleanText;
                document.body.appendChild(tempTextarea);
                tempTextarea.select();
                document.execCommand('copy');
                document.body.removeChild(tempTextarea);
                
                // 사용자에게 알림
                alert('순수 본문만 복사되었습니다! 참고자료, 링크, 통계 정보가 제거되었습니다.');
            } catch (error) {
                console.error('텍스트 복사 중 오류:', error);
                alert('텍스트 복사 중 오류가 발생했습니다. 다시 시도해주세요.');
            }
        }
        </script>
        
        <button onclick="copyTextWithoutReferences()" style="display: block; margin: 20px auto; padding: 10px 15px; background-color: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">순수 본문만 복사하기</button>
        """
        
        # 참고자료 섹션을 추가하여 포맷팅된 콘텐츠 생성
        # 본문과 참고자료를 모두 HTML로 변환
        html_main_content = markdown.markdown(cleaned_main_content)
        
        # 최종 형태의 콘텐츠 구성 - 본문과 참고자료 구분
        formatted_content = f"""
        <div class="blog-content" id="main-content">
            {html_main_content}
        </div>
        
        {references_html}
        
        {copy_script}
        """
        
        return formatted_content
        
    @staticmethod
    def extract_references(content):
        """
        콘텐츠에서 참고 자료 목록 추출 - 다양한 형태의 링크 및 참고문헌 인식
        
        Args:
            content (str): 콘텐츠
            
        Returns:
            list: 참고 자료 목록
        """
        references = []
        
        try:
            # 참고자료 추출에 사용할 다양한 방법 정의
            url_pattern = r'(https?:\/\/[^\s\)\]"]+)'
            link_pattern = r'\[(.*?)\]\((https?:\/\/[^\s\)"]*)\)'
            ref_keywords = [
                '참고자료', '참고 자료', '참고문헌', '참고',
                '출처', '참조', '연구에 따르면', '조사에 따르면',
                '공식 사이트', '공식사이트', '웹사이트', '자료출처',
                '공식 자료', '공식자료'
            ]
            
            # 1. 전체 콘텐츠에서 일반 URL 추출 (통합 방식)
            # 모든 URL 추출
            all_urls = re.findall(url_pattern, content)
            
            # 2. 모든 마크다운 링크 추출
            md_links = re.findall(link_pattern, content)
            
            # 링크 제목과 URL 저장
            markdown_refs = {}
            for title, url in md_links:
                if url and title and 'http' in url:
                    markdown_refs[url.strip()] = title.strip()
            
            # 3. 참고자료 섹션 찾기 및 추출
            ref_section = ""
            ref_headers = [
                "## 참고자료", "## 참고 자료", "## 참고", "## 참조문헌", 
                "### 참고자료", "### 참고 자료", "### 참고", "# 참고자료",
                "참고자료", "참고 자료", "참조문헌"
            ]
            
            for header in ref_headers:
                if header in content:
                    parts = content.split(header, 1)
                    if len(parts) > 1:
                        ref_section = header + parts[1].split("##", 1)[0] if "##" in parts[1] else header + parts[1]
                        logger.info(f"참고자료 섹션 출처 발견: {header}")
                        break
            
            # 4. 문장 단위로 상통성 있는 자료 찾기
            reference_lines = []
            if ref_section:
                # 섹션을 줄 단위로 분리
                lines = ref_section.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and len(line) > 3 and not line.startswith("#") and any(kw in line.lower() for kw in ["http", "www", ".com", ".kr", ".org"]):
                        reference_lines.append(line)
            
            # 5. URL을 포함하는 참고문구 찾기
            ref_sentences = []
            sentences = re.split(r'[.!?\n]+', content)
            for sentence in sentences:
                if any(kw in sentence for kw in ref_keywords) and any(url_trigger in sentence.lower() for url_trigger in ["http", "www", ".com", ".kr", ".org"]):
                    ref_sentences.append(sentence.strip())
            
            # 6. 추출된 자료들을 처리하여 레퍼런스 목록 생성
            
            # 참고자료 섹션에서 링크 처리
            if reference_lines:
                for line in reference_lines:
                    url_matches = re.findall(url_pattern, line)
                    if url_matches:
                        for url in url_matches:
                            # 이미 마크다운 링크로 알고 있는 제목 사용
                            if url in markdown_refs:
                                title = markdown_refs[url]
                            else:
                                # 제목 추출 시도
                                title = line.replace(url, "").strip()
                                # 정제 - 참고자료 키워드 제거
                                for kw in ref_keywords:
                                    if kw in title:
                                        title = title.replace(kw, "").strip()
                                        
                                # 부적절한 제목은 치환
                                if not title or len(title) < 3 or (title and title[0] in ".-:,;" and len(title) < 5):
                                    title = f"참고자료"
                            
                            references.append({'title': title, 'url': url.strip()})
            
            # 참고 문장에서 추출
            for sentence in ref_sentences:
                url_matches = re.findall(url_pattern, sentence)
                if url_matches:
                    for url in url_matches:
                        # 이미 처리한 URL은 건너뚼
                        if any(ref['url'] == url for ref in references):
                            continue
                            
                        # 제목 확인
                        if url in markdown_refs:
                            title = markdown_refs[url]
                        else:
                            # 제목 추출 시도
                            title = sentence.replace(url, "").strip()
                            # 정제 - 참고자료 키워드 제거
                            for kw in ref_keywords:
                                if kw in title:
                                    title = title.replace(kw, "").strip()
                            
                            # 부적절한 제목은 치환
                            if not title or len(title) < 3 or title.isdigit():
                                title = f"참고자료"
                        
                        references.append({'title': title, 'url': url.strip()})
            
            # 마크다운 링크에서 추가 처리 (아직 추가되지 않은 경우)
            for title, url in md_links:
                if url and title and 'http' in url and not any(ref['url'] == url.strip() for ref in references):
                    references.append({'title': title.strip(), 'url': url.strip()})
            
            # 마지막으로 단순 URL 추출
            if len(references) < 2:  # 참고자료가 2개 미만인 경우 모든 URL 사용
                for i, url in enumerate(all_urls):
                    if url and 'http' in url and not any(ref['url'] == url.strip() for ref in references):
                        references.append({'title': f"참고자료 {len(references)+1}", 'url': url.strip()})
            
            # 중복 URL 제거 및 정리
            unique_refs = []
            unique_urls = set()
            for ref in references:
                url = ref['url'].rstrip('.,;:"\'').strip()  # URL의 끝에 붙은 문장부호 제거
                if url not in unique_urls and len(url) > 8:  # 유효한 URL인지 확인
                    unique_urls.add(url)
                    unique_refs.append({'title': ref['title'], 'url': url})
            
            # 참고자료가 없으면 비어있음
            if not unique_refs:
                logger.warning("추출된 참고자료가 없습니다. 전체 콘텐츠에서 URL 추출 시도")
                # 전체 콘텐츠에서 모든 URL 추출
                all_urls = re.findall(url_pattern, content)
                for i, url in enumerate(all_urls[:5]):  # 최대 5개만 사용
                    url = url.rstrip('.,;:"\'').strip()
                    if url and len(url) > 8 and 'http' in url:
                        unique_refs.append({'title': f"참고자료 {i+1}", 'url': url})
            
            # 결과 로깅
            logger.info(f"추출된 참고자료 {len(unique_refs)}개: {json.dumps(unique_refs, ensure_ascii=False)}")
            return unique_refs
        
        except Exception as e:
            logger.error(f"참고자료 추출 중 오류: {str(e)}")
            traceback.print_exc()  # 오류 세부 정보 출력
            return []
    
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
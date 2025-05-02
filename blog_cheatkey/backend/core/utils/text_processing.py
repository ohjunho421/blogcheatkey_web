"""텍스트 처리 관련 유틸리티"""
import re
from concurrent.futures import ThreadPoolExecutor

def split_into_paragraphs(text):
    """텍스트를 문단으로 분리"""
    return re.split(r'\n\n+', text)

def split_into_sentences(text):
    """텍스트를 문장으로 분리"""
    return re.split(r'(?<=[.!?])\s+', text)

def split_into_sections(text):
    """텍스트를 소제목 기준으로 섹션 분리"""
    return re.split(r'(###\s+.*?\n)', text)

def is_heading(text):
    """텍스트가 제목인지 확인"""
    return bool(re.match(r'^#+\s+', text.strip()))

def format_for_mobile(content, max_char_per_line=23):
    """모바일 화면에 최적화된 포맷으로 변환"""
    lines = content.split('\n')
    formatted_lines = []
    
    for line in lines:
        # 마크다운 제목이나 빈 줄, 목록은 그대로 유지
        if (not line.strip() or 
            line.strip().startswith('#') or 
            line.strip().startswith(('- ', '* ', '1. ', '2. ', '3. '))):
            formatted_lines.append(line)
            continue
        
        # 일반 텍스트는 지정된 글자 수로 분리
        words = line.split()
        current_line = ""
        
        for word in words:
            if len((current_line + " " + word).replace(" ", "")) > max_char_per_line and current_line:
                formatted_lines.append(current_line)
                current_line = word
            else:
                current_line = (current_line + " " + word).strip()
        
        # 마지막 줄 추가
        if current_line:
            formatted_lines.append(current_line)
    
    return '\n'.join(formatted_lines)

def extract_references(content):
    """콘텐츠에서 참고자료 링크 추출"""
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

def process_content_in_chunks(content, chunk_size=5000, process_func=None):
    """대용량 콘텐츠를 청크 단위로 처리"""
    if not process_func:
        return content
        
    # 콘텐츠가 충분히 작으면 전체 처리
    if len(content) <= chunk_size:
        return process_func(content)
    
    # 섹션 기준으로 분할
    sections = split_into_sections(content)
    
    # 섹션 그룹화 (chunk_size 이내)
    chunks = []
    current_chunk = ""
    
    for section in sections:
        # 현재 청크가 이미 한계에 가까우면 새 청크 시작
        if len(current_chunk) + len(section) > chunk_size and current_chunk:
            chunks.append(current_chunk)
            current_chunk = section
        else:
            current_chunk += section
    
    # 마지막 청크 추가
    if current_chunk:
        chunks.append(current_chunk)
    
    # 병렬로 청크 처리
    with ThreadPoolExecutor() as executor:
        processed_chunks = list(executor.map(process_func, chunks))
    
    # 처리된 청크 결합
    return "".join(processed_chunks)
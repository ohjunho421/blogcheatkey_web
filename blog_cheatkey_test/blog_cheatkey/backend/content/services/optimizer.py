import re
import json
import logging
import time
import random
import traceback
from django.conf import settings
from konlpy.tag import Okt
from anthropic import Anthropic
from content.models import BlogContent, MorphemeAnalysis
from .formatter import ContentFormatter
from .substitution_generator import SubstitutionGenerator

logger = logging.getLogger(__name__)

class ContentOptimizer:
    """
    Claude API를 사용한 블로그 콘텐츠 최적화 클래스
    주요 기능: 글자수, 키워드 출현 횟수 확인 및 최적화
    """
    
    def __init__(self):
        self.anthropic_api_key = settings.ANTHROPIC_API_KEY
        self.model = "claude-3-7-sonnet-20250219"
        self.client = Anthropic(api_key=self.anthropic_api_key)
        self.okt = Okt()
        self.substitution_generator = SubstitutionGenerator()
    
    def optimize_existing_content_v3(self, content_id):
        """
        기존 콘텐츠를 SEO 친화적으로 최적화
        
        Args:
            content_id (int): BlogContent 모델의 ID
                    
        Returns:
            dict: 최적화 결과
        """
        try:
            # 콘텐츠 가져오기
            blog_content = BlogContent.objects.get(id=content_id)
            content = blog_content.content
            keyword = blog_content.keyword.keyword
            
            # 로깅
            logger.info(f"콘텐츠 SEO 최적화 시작 (V3): content_id={content_id}, 키워드={keyword}")
            
            # 1. API 기반 최적화 시도 (최대 3회)
            api_result = None
            best_api_analysis = None
            
            for attempt in range(3):
                try:
                    # 점진적으로 더 엄격한 프롬프트 사용
                    if attempt == 0:
                        prompt = self._create_seo_optimization_prompt(content, keyword, self.analyze_content(content, keyword))
                        temp = 0.7
                    elif attempt == 1:
                        prompt = self._create_seo_readability_prompt(content, keyword, self.analyze_content(content, keyword))
                        temp = 0.5
                    else:
                        prompt = self._create_ultra_seo_prompt(content, keyword, self.analyze_content(content, keyword))
                        temp = 0.3
                    
                    # API 호출
                    logger.info(f"API 최적화 시도 #{attempt+1}/3, temperature={temp}")
                    
                    response = self.client.messages.create(
                        model=self.model,
                        max_tokens=4096,
                        temperature=temp,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    
                    # 결과 분석
                    optimized_content = response.content[0].text
                    analysis = self.analyze_content(optimized_content, keyword)
                    
                    logger.info(f"API 시도 #{attempt+1} 결과: 글자수={analysis['char_count']}, 형태소 유효={analysis['is_valid_morphemes']}")
                    
                    # 현재 최상의 결과보다 나은지 확인
                    if best_api_analysis is None or self._is_seo_result_better(analysis, best_api_analysis):
                        api_result = optimized_content
                        best_api_analysis = analysis
                        logger.info(f"새로운 최상의 API 결과 발견: 글자수={analysis['char_count']}, 형태소 유효={analysis['is_valid_morphemes']}")
                    
                    # 모든 조건 만족 시 중단
                    if analysis['is_valid_char_count'] and analysis['is_valid_morphemes']:
                        logger.info("API 최적화 성공: 모든 조건 충족")
                        break
                        
                except Exception as e:
                    logger.error(f"API 최적화 시도 #{attempt+1} 오류: {str(e)}")
                    logger.error(traceback.format_exc())
                    time.sleep(5)  # 오류 시 잠시 대기
            
            # 2. 강제 최적화 실행 (API 결과 또는 원본 콘텐츠 사용)
            content_to_optimize = api_result if api_result else content
            
            # 강제 최적화 실행
            logger.info("SEO 강제 최적화 시작")
            optimized_content = self.enforce_seo_optimization(content_to_optimize, keyword)
            
            # 최종 분석
            final_analysis = self.analyze_content(optimized_content, keyword)
            logger.info(f"최종 결과: 글자수={final_analysis['char_count']}, 형태소 유효={final_analysis['is_valid_morphemes']}")
            
            # 모바일 최적화 포맷 생성 - formatter 사용
            formatter = ContentFormatter()
            mobile_formatted_content = formatter.format_for_mobile(optimized_content)
            
            # 콘텐츠 업데이트
            blog_content.content = optimized_content
            blog_content.mobile_formatted_content = mobile_formatted_content
            blog_content.char_count = final_analysis['char_count']
            blog_content.is_optimized = True
            
            # 최적화 메타데이터 저장
            meta_data = {
                'original_char_count': len(content.replace(" ", "")),
                'final_char_count': final_analysis['char_count'],
                'is_valid_char_count': final_analysis['is_valid_char_count'],
                'is_valid_morphemes': final_analysis['is_valid_morphemes'],
                'optimization_date': time.strftime("%Y-%m-%d %H:%M:%S"),
                'algorithm_version': 'v3',
                'attempts': 3
            }
            blog_content.meta_data = meta_data
            blog_content.save()
            
            # 기존 형태소 분석 결과 삭제
            blog_content.morpheme_analyses.all().delete()
            
            # 새로운 형태소 분석 결과 저장
            morpheme_analysis = final_analysis['morpheme_analysis']
            for morpheme, info in morpheme_analysis.get('morpheme_analysis', {}).items():
                if len(morpheme) >= 2:  # 2글자 이상만 저장
                    MorphemeAnalysis.objects.create(
                        content=blog_content,
                        morpheme=morpheme,
                        count=info.get('count', 0),
                        is_valid=info.get('is_valid', False)
                    )
            
            # 결과 메시지 생성
            success_message = "콘텐츠가 성공적으로 SEO 최적화되었습니다."
            if not final_analysis['is_valid_char_count'] or not final_analysis['is_valid_morphemes']:
                success_message += " (일부 조건 미달성)"
            
            logger.info(f"콘텐츠 SEO 최적화 완료: content_id={content_id}, 글자수={final_analysis['char_count']}, 모든 형태소 유효={final_analysis['is_valid_morphemes']}")
                
            return {
                'success': True,
                'message': success_message,
                'content_id': content_id,
                'is_valid_char_count': final_analysis['is_valid_char_count'],
                'is_valid_morphemes': final_analysis['is_valid_morphemes'],
                'char_count': final_analysis['char_count'],
                'attempts': 3,
                'algorithm_version': 'v3'
            }
                
        except BlogContent.DoesNotExist:
            return {
                'success': False,
                'message': f"ID {content_id}에 해당하는 콘텐츠를 찾을 수 없습니다.",
                'content_id': content_id
            }
        except Exception as e:
            logger.error(f"콘텐츠 최적화 중 오류 발생: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f"콘텐츠 최적화 중 오류 발생: {str(e)}",
                'content_id': content_id
            }

    def force_limit_char_count(self, content, target_min=1700, target_max=2000):
        """
        글자수를 강제로 범위 내로 제한
        
        Args:
            content (str): 콘텐츠
            target_min (int): 최소 글자수
            target_max (int): 최대 글자수
                
        Returns:
            str: 글자수가 조정된 콘텐츠
        """
        # 현재 글자수
        current_chars = len(content.replace(" ", ""))
        
        if current_chars <= target_max and current_chars >= target_min:
            return content
        
        # 목표 글자수 (범위 중간값)
        target_chars = (target_min + target_max) // 2
        
        if current_chars > target_max:
            # 1. 줄여야 할 글자 수 계산
            excess_chars = current_chars - target_chars
            logger.info(f"글자수 초과: {current_chars}자 -> {excess_chars}자 감소 필요")
            
            # 2. 문단 분리
            paragraphs = re.split(r'\n\n+', content)
            
            # 3. 제목과 일반 문단 구분
            headings = []
            normal_paragraphs = []
            
            for p in paragraphs:
                if p.strip().startswith(('#', '##', '###')):
                    headings.append(p)
                else:
                    normal_paragraphs.append(p)
            
            # 4. 가장 긴 문단 식별
            paragraph_lengths = [(i, len(p.replace(" ", ""))) for i, p in enumerate(normal_paragraphs)]
            paragraph_lengths.sort(key=lambda x: x[1], reverse=True)
            
            # 5. 남은 문단이 있고 줄여야 할 글자 수가 있는 한 문단 제거
            removed_chars = 0
            for idx, length in paragraph_lengths:
                if removed_chars >= excess_chars or len(normal_paragraphs) <= 3:  # 최소 3개의 문단은 유지
                    break
                    
                # 문단 제거
                normal_paragraphs[idx] = ""
                removed_chars += length
                logger.info(f"문단 제거: {length}자 감소")
            
            # 6. 빈 문단 필터링
            normal_paragraphs = [p for p in normal_paragraphs if p]
            
            # 7. 문단 제거로 충분하지 않을 경우, 각 문단에서 문장 축소
            if removed_chars < excess_chars:
                remaining_excess = excess_chars - removed_chars
                for i in range(len(normal_paragraphs)):
                    if remaining_excess <= 0:
                        break
                    
                    # 문단 길이가 긴 순서대로 처리
                    paragraph_idx = sorted(range(len(normal_paragraphs)), 
                                        key=lambda j: len(normal_paragraphs[j].replace(" ", "")), 
                                        reverse=True)[i % len(normal_paragraphs)]
                                        
                    paragraph = normal_paragraphs[paragraph_idx]
                    
                    # 문장 분리
                    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                    
                    # 각 문장 길이 계산
                    sentence_lengths = [(j, len(s.replace(" ", ""))) for j, s in enumerate(sentences)]
                    sentence_lengths.sort(key=lambda x: x[1], reverse=True)
                    
                    # 긴 문장부터 제거
                    for sent_idx, sent_length in sentence_lengths:
                        if remaining_excess <= 0 or len(sentences) <= 2:  # 최소 2개 문장 유지
                            break
                        
                        # 가장 긴 문장 제거
                        sentences[sent_idx] = ""
                        remaining_excess -= sent_length
                        logger.info(f"문장 제거: {sent_length}자 감소")
                    
                    # 빈 문장 필터링하고 문단 재구성
                    normal_paragraphs[paragraph_idx] = " ".join([s for s in sentences if s])
            
            # 8. 제목과 본문 재결합
            result_paragraphs = []
            heading_idx = 0
            normal_idx = 0
            
            for p in paragraphs:
                if p.strip().startswith(('#', '##', '###')):
                    if heading_idx < len(headings):
                        result_paragraphs.append(headings[heading_idx])
                        heading_idx += 1
                else:
                    if normal_idx < len(normal_paragraphs):
                        if normal_paragraphs[normal_idx]:  # 비어있지 않은 문단만 추가
                            result_paragraphs.append(normal_paragraphs[normal_idx])
                        normal_idx += 1
            
            # 최종 콘텐츠 생성
            modified_content = "\n\n".join(result_paragraphs)
            current_chars = len(modified_content.replace(" ", ""))
            logger.info(f"글자수 조정 후: {current_chars}자")
            
            return modified_content
        
        elif current_chars < target_min:
            # 글자수 확장은 좀 더 복잡할 수 있으므로 기존 _expand_paragraph 메서드 활용
            # 현재는 범위 내 조정이 우선이므로 확장 로직은 간단하게 구현
            
            # 1. 늘려야 할 글자 수 계산
            shortage = target_min - current_chars
            logger.info(f"글자수 부족: {current_chars}자 -> {shortage}자 추가 필요")
            
            # 2. 문단 분리
            paragraphs = re.split(r'\n\n+', content)
            
            # 3. 마지막 비제목 문단 찾기
            for i in range(len(paragraphs) - 1, -1, -1):
                if not paragraphs[i].strip().startswith(('#', '##', '###')):
                    # 키워드나 관련 용어 추출
                    nouns = self.okt.nouns(paragraphs[i])
                    
                    # 2글자 이상 명사 필터링
                    significant_nouns = [noun for noun in nouns if len(noun) >= 2]
                    
                    # 의미 있는 명사가 없으면 기본값 사용
                    if not significant_nouns:
                        significant_nouns = ["이것", "활용", "방법", "정보"]
                    
                    # 약 20자 길이의 문장 여러 개 생성
                    sentences_to_add = max(1, shortage // 20)
                    additional_content = ""
                    
                    for _ in range(sentences_to_add):
                        noun = random.choice(significant_nouns)
                        templates = [
                            f"이는 {noun}에 있어 중요한 요소입니다. ",
                            f"{noun}는 효과적으로 활용하는 것이 좋습니다. ",
                            f"많은 사람들이 {noun}의 중요성을 간과하곤 합니다. ",
                            f"{noun}에 대한 이해는 핵심적인 부분입니다. ",
                            f"전문가들은 {noun}에 주목할 것을 권장합니다. ",
                            f"실제로 {noun}가 큰 차이를 만들어냅니다. ",
                            f"{noun}에 관한 정보를 충분히 활용해보세요. ",
                            f"이러한 {noun}의 특성을 잘 파악하는 것이 중요합니다. "
                        ]
                        additional_content += random.choice(templates)
                    
                    # 확장된 내용 추가
                    paragraphs[i] += " " + additional_content
                    break
            
            # 최종 콘텐츠 생성
            modified_content = "\n\n".join(paragraphs)
            current_chars = len(modified_content.replace(" ", ""))
            logger.info(f"글자수 확장 후: {current_chars}자")
            
            return modified_content
        
        return content

    def force_limit_word_occurrences(self, content, max_occurrences=20):
        """
        모든 단어의 출현 횟수를 강제로 제한하는 메서드
        
        Args:
            content (str): 콘텐츠
            max_occurrences (int): 최대 허용 출현 횟수
                
        Returns:
            str: 단어 출현 횟수가 제한된 콘텐츠
        """
        # 모든 단어 추출
        words = re.findall(r'\b\w+\b', content)
        word_counts = {}
        
        # 단어 횟수 카운트
        for word in words:
            if len(word) >= 2:  # 2글자 이상 단어만 고려
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # 과다 출현 단어 식별
        excess_words = {word: count for word, count in word_counts.items() 
                        if count > max_occurrences}
        
        # 내용 복사
        modified_content = content
        
        # 과다 출현 단어 처리
        for word, count in excess_words.items():
            # 초과 횟수
            excess = count - max_occurrences
            
            # 간단한 대체어
            replacements = ["이것", "그것", "해당", "관련"]
            
            # 정규식 패턴
            pattern = rf'\b{word}\b'
            
            # 모든 일치 항목 찾기
            matches = list(re.finditer(pattern, modified_content))
            
            # 제거할 인덱스 선택 (마지막부터 시작)
            indices = list(range(len(matches)))
            indices_to_replace = indices[-excess:]
            
            # 역순으로 대체 (인덱스 변경 방지)
            for idx in sorted(indices_to_replace, reverse=True):
                match = matches[idx]
                replacement = random.choice(replacements)
                
                modified_content = (
                    modified_content[:match.start()] + 
                    replacement + 
                    modified_content[match.end():]
                )
        
        return modified_content

    def enforce_seo_optimization(self, content, keyword):
        """
        SEO 최적화를 위한 강제 변환
        
        Args:
            content (str): 최적화할 콘텐츠
            keyword (str): 주요 키워드
                
        Returns:
            str: SEO 최적화된 콘텐츠
        """
        # 참고자료 분리
        content_parts = self.separate_content_and_refs(content)
        content_without_refs = content_parts['content_without_refs']
        refs_section = content_parts['refs_section']
        
        # 초기 상태 분석
        initial_analysis = self.analyze_content(content_without_refs, keyword)
        logger.info(f"SEO 최적화 시작: 글자수={initial_analysis['char_count']}, 형태소 유효={initial_analysis['is_valid_morphemes']}")
        
        # 이미 최적화된 상태면 그대로 반환
        if initial_analysis['is_valid_char_count'] and initial_analysis['is_valid_morphemes']:
            logger.info("이미 SEO 최적화된 상태입니다.")
            return content
        
        # 최적화된 콘텐츠
        optimized_content = content_without_refs
        
        # 1. 내용 구조화 및 가독성 개선
        optimized_content = self._improve_content_structure(optimized_content, keyword)
        
        # 2. SEO를 위한 제목 최적화
        optimized_content = self._optimize_headings(optimized_content, keyword)
        
        # 3. 글자수 범위 내로 조정
        if not initial_analysis['is_valid_char_count']:
            target_chars = 1850  # 목표 범위(1700-2000) 내의 중간값
            optimized_content = self._enforce_exact_char_count_v2(optimized_content, target_chars, tolerance=50)
            
            # 글자수 조정 후 분석
            char_analysis = self.analyze_content(optimized_content, keyword)
            logger.info(f"글자수 조정 후: {char_analysis['char_count']}자 (유효: {char_analysis['is_valid_char_count']})")
        
        # 4. 형태소 출현 횟수 조정
        # 여러 번 시도하여 점진적으로 개선
        max_morpheme_attempts = 3
        for attempt in range(max_morpheme_attempts):
            morpheme_analysis = self.analyze_content(optimized_content, keyword)
            
            if morpheme_analysis['is_valid_morphemes']:
                logger.info(f"형태소 최적화 완료 (시도 #{attempt+1}/{max_morpheme_attempts})")
                break
            
            logger.info(f"형태소 최적화 시도 #{attempt+1}/{max_morpheme_attempts}")
            optimized_content = self._enforce_exact_morpheme_count(optimized_content, keyword, 18)
            
            # 형태소 조정 후 글자수가 범위를 벗어났는지 확인
            current_analysis = self.analyze_content(optimized_content, keyword)
            
            if not current_analysis['is_valid_char_count']:
                logger.info(f"형태소 조정 후 글자수 재조정 필요: {current_analysis['char_count']}자")
                optimized_content = self._enforce_exact_char_count_v2(optimized_content, target_chars, tolerance=150)
        
        # 5. 최종 검증 및 강제 조정
        final_analysis = self.analyze_content(optimized_content, keyword)
        logger.info(f"최종 검증: 글자수={final_analysis['char_count']} (유효: {final_analysis['is_valid_char_count']}), " + 
                f"형태소 유효={final_analysis['is_valid_morphemes']}")
        
        # 여전히 형태소 최적화가 안 된 경우 마지막 수단 사용
        if not final_analysis['is_valid_morphemes']:
            logger.warning("최종 형태소 강제 조정 실행")
            optimized_content = self._force_adjust_morphemes_extreme(optimized_content, keyword, final_analysis['morpheme_analysis'])
        
        # 추가: 모든 형태소 20회 이하로 제한
        optimized_content = self._limit_all_morphemes(optimized_content, keyword, max_occurrences=20)
        
        # 6. SEO 최적화를 위한 문단 간격 및 줄바꿈 최적화
        optimized_content = self._optimize_paragraph_breaks(optimized_content)
        
        # 참고자료 다시 추가
        if refs_section and "## 참고자료" not in optimized_content:
            optimized_content = optimized_content + "\n\n" + refs_section
        
        return optimized_content

    def _improve_content_structure(self, content, keyword):
        """
        내용 구조화 및 가독성 개선
        
        Args:
            content (str): 원본 콘텐츠
            keyword (str): 주요 키워드
            
        Returns:
            str: 구조화된 콘텐츠
        """
        # 1. 문단 분리
        paragraphs = re.split(r'\n\n+', content)
        
        # 2. 제목과 내용 구분
        headers = []
        content_paragraphs = []
        
        for p in paragraphs:
            if p.strip().startswith(('#', '##', '###')):
                headers.append(p)
            else:
                content_paragraphs.append(p)
        
        # 3. 존재하는 소제목 확인 및 필요한 경우 소제목 추가
        if len(headers) < 3 and len(content_paragraphs) > 3:
            # 소제목 수가 적으면 새로운 소제목 생성
            sections = []
            current_section = []
            
            # 기존 제목 유지
            if headers and content_paragraphs:
                sections.append(headers[0])  # 메인 제목
                current_section = [content_paragraphs[0]]  # 첫 문단은 서론
                
                for p in content_paragraphs[1:]:
                    if len(current_section) >= 2:  # 각 섹션 2-3개 문단으로 제한
                        section_title = f"## {keyword} 관련 중요 정보"
                        sections.append(section_title)
                        sections.extend(current_section)
                        current_section = [p]
                    else:
                        current_section.append(p)
                
                # 마지막 섹션 추가
                if current_section:
                    section_title = f"## {keyword} 활용 방법"
                    sections.append(section_title)
                    sections.extend(current_section)
                
                return "\n\n".join(sections)
            
        # 4. 이미 구조화가 잘 되어 있으면 그대로 반환
        return content

    def _optimize_headings(self, content, keyword):
        """
        SEO를 위한 제목 최적화
        
        Args:
            content (str): 원본 콘텐츠
            keyword (str): 주요 키워드
            
        Returns:
            str: 제목이 최적화된 콘텐츠
        """
        # 1. 첫 번째 제목에 키워드가 포함되어 있는지 확인
        paragraphs = re.split(r'\n\n+', content)
        
        # 2. 첫 번째 제목 찾기
        first_heading = None
        for p in paragraphs:
            if p.strip().startswith(('#', '##', '###')):
                first_heading = p
                break
        
        # 3. 첫 번째 제목에 키워드가 없으면 추가
        if first_heading and keyword.lower() not in first_heading.lower():
            # 원래 제목 형식 유지하면서 키워드 추가
            heading_level = len(re.match(r'^(#+)', first_heading).group(1))
            heading_text = re.sub(r'^#+ ', '', first_heading).strip()
            
            # 제목에 키워드 자연스럽게 통합
            if ',' in heading_text:
                parts = heading_text.split(',', 1)
                new_heading = f"{parts[0]}, {keyword}{parts[1]}"
            else:
                new_heading = f"{heading_text} - {keyword}"
            
            # 새 제목 생성 및 콘텐츠 업데이트
            new_first_heading = '#' * heading_level + ' ' + new_heading
            content = content.replace(first_heading, new_first_heading)
        
        # 4. 주요 섹션 제목 최적화
        # 각 제목에 키워드 관련 문구 포함시키기
        headings = re.findall(r'^#{2,3}\s+(.+)$', content, re.MULTILINE)
        for heading in headings:
            if keyword.lower() not in heading.lower():
                # 원본 제목
                original_heading = heading.strip()
                heading_pattern = re.compile(r'^(#{2,3}\s+)' + re.escape(original_heading), re.MULTILINE)
                
                # 키워드를 포함한 새 제목
                new_heading = f"{original_heading}와 {keyword}"
                
                # 제목 대체
                content = heading_pattern.sub(r'\1' + new_heading, content)
        
        return content

    def _optimize_paragraph_breaks(self, content):
        """
        SEO 최적화를 위한 문단 간격 및 줄바꿈 최적화
        
        Args:
            content (str): 원본 콘텐츠
            
        Returns:
            str: 최적화된 콘텐츠
        """
        # 1. 문단 분리
        paragraphs = re.split(r'\n\n+', content)
        
        # 2. 긴 문단 분리
        optimized_paragraphs = []
        
        for p in paragraphs:
            if p.strip().startswith(('#', '##', '###')):
                # 제목은 그대로 유지
                optimized_paragraphs.append(p)
            elif len(p) > 300:  # 긴 문단은 분리
                sentences = re.split(r'(?<=[.!?])\s+', p)
                
                # 문장을 2-3개씩 그룹화하여 새 문단 생성
                sentence_groups = []
                current_group = []
                
                for sentence in sentences:
                    current_group.append(sentence)
                    if len(current_group) >= 3:
                        sentence_groups.append(" ".join(current_group))
                        current_group = []
                
                # 남은 문장 처리
                if current_group:
                    sentence_groups.append(" ".join(current_group))
                
                # 최적화된 문단 추가
                optimized_paragraphs.extend(sentence_groups)
            else:
                # 짧은 문단은 그대로 유지
                optimized_paragraphs.append(p)
        
        # 3. 최적화된 문단 결합
        return "\n\n".join(optimized_paragraphs)

    def _force_adjust_morphemes_extreme(self, content, keyword, morpheme_analysis):
        """
        형태소 출현 횟수를 마지막 수단으로 강제 조정하는 메서드
        
        Args:
            content (str): 콘텐츠
            keyword (str): 키워드
            morpheme_analysis (dict): 형태소 분석 결과
                    
        Returns:
            str: 형태소 출현 횟수가 강제 조정된 콘텐츠
        """
        logger.warning("극단적 형태소 조정 시작")
        adjusted_content = content
        
        # 키워드 구성 형태소 추출 및 분석
        keyword_morphemes = self.okt.morphs(keyword)
        
        # 유의미한 형태소만 필터링 (2글자 이상)
        significant_morphemes = [m for m in keyword_morphemes if len(m) >= 2]
        
        # 형태소 조정 순서 결정 - 출현 횟수가 많은 순서로 정렬
        morpheme_count_tuples = []
        for morpheme, info in morpheme_analysis.get('morpheme_analysis', {}).items():
            current_count = info.get('count', 0)
            # 형태소와 해당 출현 횟수를 저장
            morpheme_count_tuples.append((morpheme, current_count))
        
        # 출현 횟수가 많은 순서로 정렬
        morpheme_count_tuples.sort(key=lambda x: x[1], reverse=True)
        
        # 목표 범위
        target_min, target_max = 17, 20
        
        # 단계 1: 과도하게 많은 형태소부터 조정 (많이 나온 순서대로)
        for morpheme, current_count in morpheme_count_tuples:
            if current_count <= target_max:
                continue  # 이미 목표 범위 내에 있으면 건너뜀
                
            # 과다한 경우 - 과감하게 대체어로 교체
            excess = current_count - target_max
            logger.warning(f"형태소 '{morpheme}' 과다 출현: {current_count}회 -> 목표 17-20회 (제거량: {excess}회)")
            adjusted_content = self._reduce_morpheme_aggressively(adjusted_content, morpheme, excess)
            
            # 조정 후 다시 확인
            new_count = self._count_exact_word(morpheme, adjusted_content)
            logger.warning(f"형태소 '{morpheme}' 조정 후: {new_count}회")
        
        # 조정 후 분석 업데이트
        interim_analysis = self.analyze_content(adjusted_content, keyword)
        
        # 단계 2: 부족한 형태소 조정
        for morpheme, info in interim_analysis['morpheme_analysis'].get('morpheme_analysis', {}).items():
            current_count = info.get('count', 0)
            
            if current_count < target_min:
                # 부족한 경우 - 형태소 추가
                shortage = target_min - current_count
                logger.warning(f"형태소 '{morpheme}' 부족: {current_count}회 -> 목표 17-20회 (추가량: {shortage}회)")
                adjusted_content = self._add_morpheme_strategically(adjusted_content, morpheme, shortage)
                
                # 조정 후 다시 확인
                new_count = self._count_exact_word(morpheme, adjusted_content)
                logger.warning(f"형태소 '{morpheme}' 조정 후: {new_count}회")
        
        # 최종 검증
        final_analysis = self.analyze_content(adjusted_content, keyword)
        logger.warning("형태소 최종 조정 결과:")
        for morpheme, info in final_analysis['morpheme_analysis'].get('morpheme_analysis', {}).items():
            final_count = info.get('count', 0)
            status = "적정" if target_min <= final_count <= target_max else "부적정"
            logger.warning(f"- '{morpheme}': {final_count}회 ({status})")
        
        return adjusted_content
    
    def _add_morpheme_strategically(self, content, morpheme, count_to_add):
        """
        형태소를 전략적으로 추가
        
        Args:
            content (str): 콘텐츠
            morpheme (str): 추가할 형태소
            count_to_add (int): 추가할 횟수
                
        Returns:
            str: 형태소가 추가된 콘텐츠
        """
        # 문단 분리
        paragraphs = content.split("\n\n")
        
        # 일반 문단만 선택 (제목 제외)
        normal_paragraphs = [i for i, p in enumerate(paragraphs) 
                        if not p.strip().startswith(('#', '##', '###'))]
        
        # 추가할 수 있는 문단이 없으면 마지막에 새 문단 추가
        if not normal_paragraphs:
            new_paragraph = self._generate_paragraph_with_morpheme(morpheme, count_to_add)
            paragraphs.append(new_paragraph)
            return "\n\n".join(paragraphs)
        
        # 추가 위치 분산 (고르게 분포)
        selected_indices = []
        
        # 전체 문단에 고르게 분산
        for i in range(count_to_add):
            # 순환 인덱스 사용
            idx = normal_paragraphs[i % len(normal_paragraphs)]
            selected_indices.append(idx)
        
        # 문단별 추가 횟수 집계
        add_counts = {}
        for idx in selected_indices:
            add_counts[idx] = add_counts.get(idx, 0) + 1
        
        # 형태소 추가 실행
        for idx, add_count in add_counts.items():
            original = paragraphs[idx]
            
            # 더 자연스러운 문장 생성 패턴
            templates = [
                f"이는 {morpheme}의 주요 특징입니다. ",
                f"{morpheme}는 이런 상황에서 효과적입니다. ",
                f"전문가들이 추천하는 {morpheme} 활용법이 있습니다. ",
                f"{morpheme}의 품질이 중요한 이유가 여기에 있습니다. ",
                f"많은 사람들이 {morpheme}의 장점을 높이 평가합니다. "
            ]
            
            # 추가할 문장 생성 (자연스러운 분포를 위해 문단 내 다른 위치에 삽입)
            sentences = re.split(r'(?<=[.!?])\s+', original)
            
            if len(sentences) <= 1:
                # 문장이 하나뿐인 경우 끝에 추가
                additions = ""
                for _ in range(add_count):
                    additions += random.choice(templates)
                paragraphs[idx] = original + " " + additions
            else:
                # 문장이 여러 개인 경우 중간에 분산 삽입
                for _ in range(add_count):
                    # 첫 문장과 마지막 문장은 제외하고 중간에만 삽입
                    if len(sentences) > 2:
                        insert_pos = random.randint(1, len(sentences) - 1)
                    else:
                        insert_pos = 1
                        
                    sentences.insert(insert_pos, random.choice(templates))
                
                paragraphs[idx] = " ".join(sentences)
        
        return "\n\n".join(paragraphs)

    def _reduce_morpheme_aggressively(self, content, morpheme, count_to_remove):
        """
        형태소를 과감하게 줄이는 메서드
        
        Args:
            content (str): 콘텐츠
            morpheme (str): 제거할 형태소
            count_to_remove (int): 제거할 횟수
                
        Returns:
            str: 형태소가 줄어든 콘텐츠
        """
        logger.warning(f"형태소 '{morpheme}' {count_to_remove}회 과감하게 줄이기")
        
        # 형태소 패턴 (한글 경계 고려)
        if re.search(r'[가-힣]', morpheme):
            pattern = rf'(?<![가-힣]){re.escape(morpheme)}(?![가-힣])'
        else:
            pattern = rf'\b{re.escape(morpheme)}\b'
        
        # 모든 일치 항목 찾기
        matches = list(re.finditer(pattern, content))
        total_matches = len(matches)
        
        # 남겨둘 최소 개수 (17개)
        min_keep = 17
        
        # 제거할 수 있는 최대 개수
        max_removable = max(0, total_matches - min_keep)
        actual_remove = min(count_to_remove, max_removable)
        
        if actual_remove <= 0:
            logger.warning(f"제거 가능한 '{morpheme}' 인스턴스가 없습니다.")
            return content
        
        # 제거 대상 선택 (첫 번째 출현은 유지, 마지막 출현도 가능하면 유지)
        # 중간 부분의 형태소를 주로 제거
        available_indices = list(range(1, total_matches))
        
        if len(available_indices) <= actual_remove:
            # 충분한 인덱스가 없으면 첫 번째만 제외하고 나머지 모두 선택
            indices_to_remove = available_indices
        else:
            # 충분한 인덱스가 있으면 전략적으로 선택
            # 문서 전체에 걸쳐 고르게 제거
            step = len(available_indices) / actual_remove
            indices_to_remove = [available_indices[int(i * step)] for i in range(actual_remove)]
        
        # 대체어 확보 - 다양한 대체어 사용
        replacements = self._get_enhanced_substitutions(morpheme)
        
        # 역순으로 제거 (인덱스 변경 방지)
        result = content
        for idx in sorted(indices_to_remove, reverse=True):
            match = matches[idx]
            
            # 랜덤 대체어 선택 (매번 다른 대체어 사용)
            replacement = random.choice(replacements)
            
            # 형태소 대체
            result = result[:match.start()] + replacement + result[match.end():]
        
        return result

    def _get_enhanced_substitutions(self, morpheme):
        """
        형태소에 대한 향상된 대체어 목록 생성 - 동적 접근 방식
        
        Args:
            morpheme (str): 대체할 형태소
                
        Returns:
            list: 대체어 목록
        """
        # SubstitutionGenerator를 통해 대체어 가져오기
        # 이미 self.substitution_generator 인스턴스가 초기화되어 있음
        substitutions = self.substitution_generator.get_substitutions(morpheme)
        
        # 충분한 대체어가 없으면 기본 지시어 추가
        if len(substitutions) < 5:
            default_subs = ["이것", "해당 항목", "이 요소", "관련 사항", "이 부분"]
            substitutions.extend(default_subs)
        
        # 중복 제거
        substitutions = list(set(substitutions))
        
        return substitutions

    def _identify_morpheme_type(self, morpheme):
        """
        형태소의 의미적 유형 식별
        
        Args:
            morpheme (str): 분석할 형태소
                
        Returns:
            str: 형태소 유형 (material, product, component 등)
        """
        # 단어 끝 기준 형태소 유형 추정
        if morpheme.endswith(('재', '료', '질', '체')):
            return "material"  # 재료, 소재 유형
        elif morpheme.endswith(('품', '재', '구', '물', '기')):
            return "product"   # 제품 유형
        elif morpheme.endswith(('부', '판', '보드', '판넬', '장', '체')):
            return "component" # 부품, 구성요소 유형
        elif morpheme.endswith(('법', '식', '략', '술')):
            return "method"    # 방법, 기술 유형
        elif morpheme.endswith(('성', '능', '과', '치')):
            return "property"  # 속성, 특성 유형
        else:
            # 명확한 유형이 없을 경우 형태소 자체의 특성 분석
            if len(morpheme) >= 4 and '석고' in morpheme:  # 예시: 특정 도메인 지식 활용
                if '천장' in morpheme or '벽' in morpheme:
                    return "component"
                return "material"
            
            # 기본값: 일반 명사로 취급
            return "general"

    def _generate_generic_substitutions(self, morpheme, morpheme_type):
        """
        형태소 유형에 따른 범용 대체어 생성
        
        Args:
            morpheme (str): 원본 형태소
            morpheme_type (str): 형태소 유형
                
        Returns:
            list: 생성된 대체어 목록
        """
        # 형태소 유형별 범용 대체어 템플릿
        type_templates = {
            "material": [
                "이 소재", "해당 재료", "이 자재", "건축 재료", "내장재", 
                "마감 재료", "이 원료", "해당 물질", "소재", "자재"
            ],
            "product": [
                "이 제품", "해당 상품", "이 물품", "해당 제품", "이것", 
                "관련 제품", "이 아이템", "해당 물건", "제품", "상품"
            ],
            "component": [
                "이 부품", "해당 구성품", "이 요소", "이 부분", "이 컴포넌트", 
                "해당 부분", "구성 요소", "부품", "요소", "이 자재"
            ],
            "method": [
                "이 방식", "해당 방법", "이 기법", "이런 접근법", "이 전략", 
                "해당 기술", "이 프로세스", "방법", "절차", "기법"
            ],
            "property": [
                "이 특성", "해당 속성", "이 성질", "이런 특징", "이 성능", 
                "해당 품질", "이런 면", "특성", "속성", "성질"
            ],
            "general": [
                "이것", "해당 항목", "이 요소", "관련 사항", "이 부분", 
                "해당 내용", "이런 측면", "이", "해당", "관련"
            ]
        }
        
        # 기본 대체어 목록
        substitutions = type_templates.get(morpheme_type, type_templates["general"])
        
        # 추가적으로 문맥 인식 대체어 생성
        # 예: 형태소가 '천장석고보드'인 경우, '천장'+'재', '천장'+'자재' 등의 조합 생성
        contextual_subs = []
        
        # 복합어 분석 및 문맥 인식 대체어 생성
        if len(morpheme) > 2:
            # 가능한 접두어 추출 (예: '천장석고보드'에서 '천장')
            for i in range(2, min(len(morpheme), 5)):
                prefix = morpheme[:i]
                if prefix in ["천장", "벽", "바닥", "주방", "욕실", "실내", "외부"]:
                    # 접두어 + 범용 단어 조합
                    for generic_term in ["재", "자재", "패널", "마감재", "구성품", "부품"]:
                        contextual_subs.append(f"{prefix} {generic_term}")
                        contextual_subs.append(f"{prefix}{generic_term}")
        
        # 형태소가 '보드'를 포함하는 경우 관련 대체어 추가
        if "보드" in morpheme:
            contextual_subs.extend(["패널", "판넬", "보드류", "판재", "마감재", "건축자재"])
        
        # 모든 대체어 결합
        return substitutions + contextual_subs

    def _limit_all_morphemes(self, content, keyword, max_occurrences=20):
        """
        모든 형태소의 출현 횟수를 제한하는 메서드
        
        Args:
            content (str): 콘텐츠
            keyword (str): 주요 키워드 (로깅 및 우선순위 결정용)
            max_occurrences (int): 최대 허용 출현 횟수
                
        Returns:
            str: 형태소 출현 횟수가 제한된 콘텐츠
        """
        logger.info(f"모든 형태소 출현 횟수 {max_occurrences}회 이하로 제한 시작")
        adjusted_content = content
        
        # 1. 모든 명사 추출 (의미 있는 형태소)
        try:
            all_nouns = self.okt.nouns(content)
        except Exception as e:
            logger.error(f"명사 추출 오류: {str(e)}")
            all_nouns = []
        
        # 2. 2글자 이상 형태소만 필터링 및 중복 제거
        significant_morphemes = set()
        for noun in all_nouns:
            if len(noun) >= 2:
                significant_morphemes.add(noun)
        
        # 3. 키워드 관련 형태소 추가 (이미 포함되어 있을 수 있음)
        keyword_morphemes = self.okt.morphs(keyword)
        for morpheme in keyword_morphemes:
            if len(morpheme) >= 2:
                significant_morphemes.add(morpheme)
        
        # 4. 추가로 동사, 형용사 등 주요 형태소도 고려
        try:
            all_morphs = self.okt.pos(content)
            for morph, pos in all_morphs:
                # 주요 형태소(명사, 동사, 형용사, 부사)만 고려하고 2글자 이상인 경우만 포함
                if (pos.startswith('N') or pos.startswith('V') or 
                    pos.startswith('XR') or pos.startswith('M')) and len(morph) >= 2:
                    significant_morphemes.add(morph)
        except Exception as e:
            logger.error(f"형태소 분석 오류: {str(e)}")
        
        # 5. 출현 횟수 계산 및 정렬
        morpheme_counts = []
        for morpheme in significant_morphemes:
            count = self._count_exact_word(morpheme, adjusted_content)
            if count > max_occurrences:
                morpheme_counts.append((morpheme, count))
        
        # 6. 출현 횟수가 많은 순서대로 정렬
        morpheme_counts.sort(key=lambda x: x[1], reverse=True)
        
        # 7. 과다 출현 형태소 처리
        for morpheme, count in morpheme_counts:
            if count > max_occurrences:
                excess = count - max_occurrences
                logger.info(f"형태소 '{morpheme}' 과다 출현: {count}회 -> 목표 {max_occurrences}회 이하 (제거량: {excess}회)")
                
                # 핵심 키워드의 일부인 경우 주의하여 처리
                is_part_of_keyword = morpheme in keyword or keyword in morpheme
                
                if is_part_of_keyword:
                    # 키워드 관련 형태소는 정확히 목표치로 조정
                    adjusted_content = self._reduce_morpheme_aggressively(adjusted_content, morpheme, excess)
                else:
                    # 기타 형태소는 더 과감하게 대체 가능
                    adjusted_content = self._reduce_general_morpheme(adjusted_content, morpheme, excess)
                
                # 조정 후 다시 확인
                new_count = self._count_exact_word(morpheme, adjusted_content)
                logger.info(f"형태소 '{morpheme}' 조정 후: {new_count}회")
        
        return adjusted_content

    def _reduce_general_morpheme(self, content, morpheme, count_to_remove):
        """
        일반 형태소(키워드가 아닌)의 출현 횟수를 과감하게 줄이는 메서드
        
        Args:
            content (str): 콘텐츠
            morpheme (str): 제거할 형태소
            count_to_remove (int): 제거할 횟수
                
        Returns:
            str: 형태소가 줄어든 콘텐츠
        """
        # 형태소 패턴 (한글 경계 고려)
        if re.search(r'[가-힣]', morpheme):
            pattern = rf'(?<![가-힣]){re.escape(morpheme)}(?![가-힣])'
        else:
            pattern = rf'\b{re.escape(morpheme)}\b'
        
        # 모든 일치 항목 찾기
        matches = list(re.finditer(pattern, content))
        total_matches = len(matches)
        
        # 제거할 수 있는 최대 개수 (최소 5개는 유지 - 일반 형태소는 더 과감하게 제거)
        min_keep = 5
        max_removable = max(0, total_matches - min_keep)
        actual_remove = min(count_to_remove, max_removable)
        
        if actual_remove <= 0:
            return content
        
        # 일반 형태소에 대한 다양한 대체어 생성
        replacements = self._generate_simple_substitutions(morpheme)
        
        # 문서 전체에 걸쳐 고르게 제거
        # 먼저 제거할 인덱스 선택 (첫 번째 출현은 유지)
        if len(matches) <= actual_remove + 1:
            # 첫 번째 출현만 보존
            indices_to_remove = list(range(1, len(matches)))
        else:
            # 고르게 분포하여 제거
            step = (len(matches) - 1) / actual_remove
            indices_to_remove = [1 + int(i * step) for i in range(actual_remove)]
        
        # 역순으로 제거 (인덱스 변경 방지)
        result = content
        for idx in sorted(indices_to_remove, reverse=True):
            match = matches[idx]
            
            # 랜덤 대체어 선택
            replacement = random.choice(replacements)
            
            # 형태소 대체
            result = result[:match.start()] + replacement + result[match.end():]
        
        return result

    def _generate_simple_substitutions(self, morpheme):
        """
        일반 형태소에 대한 간단한 대체어 생성
        
        Args:
            morpheme (str): 원본 형태소
                
        Returns:
            list: 대체어 목록
        """
        # 기본 대체어
        basic_subs = ["이", "그", "해당", "이것", "그것", "이런", "저런", "관련"]
        
        # 더 과감한 처리를 위해 빈 문자열도 포함
        if len(morpheme) > 3:  # 긴 형태소만 빈 문자열로 대체 가능
            basic_subs.append("")
        
        return basic_subs
    
    def _enforce_exact_char_count_v2(self, content, target_char_count, tolerance=50):
        """
        콘텐츠의 글자 수를 목표 범위 내로 조정하는 개선된 메서드
        
        Args:
            content (str): 콘텐츠
            target_char_count (int): 목표 글자 수
            tolerance (int): 허용 오차 범위
                
        Returns:
            str: 글자 수가 조정된 콘텐츠
        """
        # 현재 글자 수 (공백 제외)
        current_char_count = len(content.replace(" ", ""))
        
        # 목표 범위
        min_chars = target_char_count - tolerance
        max_chars = target_char_count + tolerance
        
        # 이미 범위 내에 있으면 그대로 반환
        if min_chars <= current_char_count <= max_chars:
            return content
            
        # 문단 분리 (개행으로 구분)
        paragraphs = re.split(r'\n\n+', content)
        
        # 제목과 일반 문단 분리
        headings = []
        normal_paragraphs = []
        
        for p in paragraphs:
            if p.strip().startswith(('#', '##', '###')):
                headings.append(p)
            else:
                normal_paragraphs.append(p)
        
        # 1. 확장이 필요한 경우
        if current_char_count < min_chars:
            chars_to_add = min_chars - current_char_count
            logger.info(f"{chars_to_add}자 추가 필요")
            
            # 마지막 비제목 문단을 찾아 확장
            for i in range(len(paragraphs) - 1, -1, -1):
                if not paragraphs[i].strip().startswith(('#', '##', '###')):
                    # 해당 문단 확장
                    expanded_paragraph = self._expand_paragraph(paragraphs[i], chars_to_add)
                    paragraphs[i] = expanded_paragraph
                    break
                    
            return "\n\n".join(paragraphs)
            
        # 2. 축소가 필요한 경우
        elif current_char_count > max_chars:
            chars_to_remove = current_char_count - max_chars
            logger.info(f"{chars_to_remove}자 제거 필요")
            
            # 점진적 축소
            remaining_chars = chars_to_remove
            
            # 가장 긴 문단부터 축소 (제목은 제외)
            paragraph_lengths = [(i, len(p.replace(" ", ""))) for i, p in enumerate(paragraphs) 
                                if not p.strip().startswith(('#', '##', '###'))]
            paragraph_lengths.sort(key=lambda x: x[1], reverse=True)
            
            for idx, length in paragraph_lengths:
                if remaining_chars <= 0:
                    break
                    
                # 해당 문단에서 제거할 문자 수 결정
                chars_for_this_paragraph = min(remaining_chars, length // 3)  # 최대 1/3만 제거
                
                if chars_for_this_paragraph > 0:
                    # 문단 축소
                    paragraphs[idx] = self._reduce_paragraph(paragraphs[idx], chars_for_this_paragraph)
                    remaining_chars -= chars_for_this_paragraph
                    
            return "\n\n".join(paragraphs)
            
        return content

    def _expand_paragraph(self, paragraph, chars_to_add):
        """
        문단을 자연스럽게 확장
        
        Args:
            paragraph (str): 확장할 문단
            chars_to_add (int): 추가할 글자 수
                
        Returns:
            str: 확장된 문단
        """
        # 문장으로 분리
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        
        # 확장 문장 수 결정 (평균 20자 기준)
        sentences_to_add = max(1, chars_to_add // 20)
        
        # 주요 문구 추출 (명사 위주)
        words = self.okt.nouns(paragraph)
        key_words = [w for w in words if len(w) > 1]
        
        if not key_words:
            key_words = ["이", "활용", "방법", "정보"]
        
        # 확장 문장 생성
        expansion = []
        templates = [
            "이는 {word}에 있어 중요한 요소입니다.",
            "{word}는 효과적으로 활용하는 것이 좋습니다.",
            "많은 사람들이 {word}의 중요성을 간과하곤 합니다.",
            "{word}에 대한 이해는 핵심적인 부분입니다.",
            "전문가들은 {word}에 주목할 것을 권장합니다.",
            "실제로 {word}가 큰 차이를 만들어냅니다.",
            "{word}에 관한 정보를 충분히 활용해보세요.",
            "이러한 {word}의 특성을 잘 파악하는 것이 중요합니다."
        ]
        
        for _ in range(sentences_to_add):
            word = random.choice(key_words)
            template = random.choice(templates)
            expansion.append(template.format(word=word))
        
        # 확장 문장을 기존 문단 끝에 추가
        expanded_paragraph = paragraph + " " + " ".join(expansion)
        
        return expanded_paragraph

    def _reduce_paragraph(self, paragraph, chars_to_remove):
        """
        문단을 자연스럽게 축소
        
        Args:
            paragraph (str): 축소할 문단
            chars_to_remove (int): 제거할 글자 수
                
        Returns:
            str: 축소된 문단
        """
        # 문장으로 분리
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        
        # 이미 짧은 문단은 그대로 반환
        if len(sentences) <= 1:
            return paragraph
        
        # 각 문장의 중요도 평가 (길이와 위치 기반)
        sentence_importance = []
        for i, sentence in enumerate(sentences):
            # 첫 문장과 마지막 문장은 중요도 높게 설정
            position_factor = 3 if i == 0 or i == len(sentences) - 1 else 1
            # 긴 문장이 더 많은 정보를 담고 있을 가능성이 높음
            length_factor = len(sentence) / 30  # 평균 문장 길이 기준
            
            importance = position_factor * length_factor
            sentence_importance.append((i, importance, len(sentence.replace(" ", ""))))
        
        # 중요도 낮은 순으로 정렬
        sentence_importance.sort(key=lambda x: x[1])
        
        # 필요한 만큼 문장 제거
        removed_chars = 0
        sentences_to_remove = []
        
        for idx, _, char_count in sentence_importance:
            if removed_chars >= chars_to_remove:
                break
                
            sentences_to_remove.append(idx)
            removed_chars += char_count
        
        # 남은 문장들로 새 문단 구성
        reduced_sentences = [s for i, s in enumerate(sentences) if i not in sentences_to_remove]
        reduced_paragraph = " ".join(reduced_sentences)
        
        return reduced_paragraph

    def _enforce_exact_morpheme_count(self, content, keyword, target_count):
        """
        형태소 출현 횟수를 목표 범위 내로 조정
        
        Args:
            content (str): 콘텐츠
            keyword (str): 키워드
            target_count (int): 목표 출현 횟수
                
        Returns:
            str: 형태소 출현 횟수가 조정된 콘텐츠
        """
        # 현재 형태소 분석
        analysis = self.analyze_content(content, keyword)
        morpheme_analysis = analysis['morpheme_analysis'].get('morpheme_analysis', {})
        
        # 조정이 필요한 형태소 식별
        needs_adjustment = {}
        for morpheme, info in morpheme_analysis.items():
            count = info.get('count', 0)
            if count < 17:
                needs_adjustment[morpheme] = {'current': count, 'target': target_count, 'action': 'add'}
            elif count > 20:
                needs_adjustment[morpheme] = {'current': count, 'target': target_count, 'action': 'remove'}
        
        # 조정 불필요시 반환
        if not needs_adjustment:
            return content
        
        # 조정 실행
        adjusted_content = content
        
        for morpheme, adjustment_info in needs_adjustment.items():
            action = adjustment_info['action']
            current = adjustment_info['current']
            target = adjustment_info['target']
            
            if action == 'add':
                # 추가 필요
                to_add = target - current
                logger.info(f"형태소 '{morpheme}' {to_add}회 추가")
                
                # 자연스러운 문장 생성 및 추가
                adjusted_content = self._add_morpheme_naturally(adjusted_content, morpheme, to_add)
                
            elif action == 'remove':
                # 제거 필요
                to_remove = current - target
                logger.info(f"형태소 '{morpheme}' {to_remove}회 제거")
                
                # 선택적 제거 실행
                adjusted_content = self._remove_morpheme_selectively(adjusted_content, morpheme, to_remove)
        
        return adjusted_content

    def _count_exact_word(self, word, text):
        """
        텍스트에서 단어의 정확한 출현 횟수 계산
        
        Args:
            word (str): 검색할 단어
            text (str): 검색 대상 텍스트
                
        Returns:
            int: 출현 횟수
        """
        # 한글 경계 고려
        if re.search(r'[가-힣]', word):
            pattern = rf'(?<![가-힣]){re.escape(word)}(?![가-힣])'
        else:
            pattern = rf'\b{re.escape(word)}\b'
        
        return len(re.findall(pattern, text))

    def _is_seo_result_better(self, new_analysis, current_analysis):
        """
        SEO 결과가 더 나은지 비교
        
        Args:
            new_analysis (dict): 새 분석 결과
            current_analysis (dict): 현재 분석 결과
                
        Returns:
            bool: 새 결과가 더 나은지 여부
        """
        # 1. 글자수 유효성 비교
        new_valid_chars = new_analysis['is_valid_char_count']
        current_valid_chars = current_analysis['is_valid_char_count']
        
        if new_valid_chars and not current_valid_chars:
            return True
        if not new_valid_chars and current_valid_chars:
            return False
        
        # 2. 형태소 유효성 비교
        new_valid_morphemes = new_analysis['is_valid_morphemes']
        current_valid_morphemes = current_analysis['is_valid_morphemes']
        
        if new_valid_morphemes and not current_valid_morphemes:
            return True
        if not new_valid_morphemes and current_valid_morphemes:
            return False
        
        # 3. 글자수가 목표 범위(1700-2000)에 얼마나 가까운지
        target_chars = 1850  # 범위 중간값
        new_char_distance = abs(new_analysis['char_count'] - target_chars)
        current_char_distance = abs(current_analysis['char_count'] - target_chars)
        
        if new_char_distance < current_char_distance:
            return True
        
        # 4. 형태소 출현 횟수가 목표 범위(17-20)에 얼마나 가까운지
        new_morpheme_score = 0
        current_morpheme_score = 0
        
        target_morpheme_count = 18.5  # 범위 중간값
        
        for morpheme, info in new_analysis['morpheme_analysis'].get('morpheme_analysis', {}).items():
            new_morpheme_score += abs(info.get('count', 0) - target_morpheme_count)
        
        for morpheme, info in current_analysis['morpheme_analysis'].get('morpheme_analysis', {}).items():
            current_morpheme_score += abs(info.get('count', 0) - target_morpheme_count)
        
        return new_morpheme_score < current_morpheme_score

    def separate_content_and_refs(self, content):
        """
        콘텐츠와 참고자료 부분 분리
        
        Args:
            content (str): 콘텐츠
                
        Returns:
            dict: 분리된 콘텐츠와 참고자료
        """
        # 참고자료 섹션 찾기
        refs_pattern = r"(## 참고자료.*$)"
        refs_match = re.search(refs_pattern, content, re.DOTALL | re.MULTILINE)
        
        if refs_match:
            refs_section = refs_match.group(1)
            content_without_refs = content[:refs_match.start()].strip()
            return {
                'content_without_refs': content_without_refs,
                'refs_section': refs_section
            }
        else:
            return {
                'content_without_refs': content,
                'refs_section': None
            }
    
    def analyze_content(self, content, keyword):
        """
        콘텐츠 분석: 글자수, 형태소 분석 (개선된 버전)
        
        Args:
            content (str): 분석할 콘텐츠
            keyword (str): 주요 키워드
                
        Returns:
            dict: 분석 결과
        """
        # 글자수 계산 (공백 제외)
        char_count = len(content.replace(" ", ""))
        is_valid_char_count = 1700 <= char_count <= 2000
        
        # 정확한 단어 단위 카운팅 함수
        def count_exact_word(word, text):
            # 한글 경계 고려
            if re.search(r'[가-힣]', word):
                pattern = rf'(?<![가-힣]){re.escape(word)}(?![가-힣])'
            else:
                pattern = rf'\b{re.escape(word)}\b'
            
            return len(re.findall(pattern, text))
        
        # 키워드 자체를 하나의 형태소로 추가
        morpheme_counts = {}
        keyword_count = count_exact_word(keyword, content)
        morpheme_counts[keyword] = {
            'count': keyword_count,
            'is_valid': 17 <= keyword_count <= 20
        }
        
        # 키워드에서 형태소 추출
        keyword_morphemes = self.okt.morphs(keyword)
        
        # 2글자 이상의 의미 있는 형태소만 필터링
        significant_morphemes = [m for m in keyword_morphemes if len(m) >= 2]
        
        # 복합 키워드 처리 (예: "자동차 부동액")
        is_compound_keyword = ' ' in keyword
        keyword_parts = []
        if is_compound_keyword:
            keyword_parts = [part for part in keyword.split() if len(part) >= 2]
            
            # 복합 키워드 구성 요소의 출현 횟수 분석
            for part in keyword_parts:
                # 구성 요소의 출현 횟수 계산
                part_count = count_exact_word(part, content)
                
                # 복합 키워드에서의 포함 횟수를 고려
                # 키워드가 X번 사용되면, 각 구성 요소는 이미 X번 포함되어 있음
                # 총 출현 횟수 = 단독 출현 + 복합 키워드 내 출현
                total_count = part_count
                
                morpheme_counts[part] = {
                    'count': total_count,
                    'is_valid': 17 <= total_count <= 20
                }
        
        # 나머지 키워드의 일부분도 형태소로 고려
        for morpheme in significant_morphemes:
            # 이미 처리된 복합 키워드 구성 요소는 건너뜀
            if morpheme in keyword_parts or morpheme == keyword:
                continue
                
            count = count_exact_word(morpheme, content)
            is_valid = 17 <= count <= 20
            
            morpheme_counts[morpheme] = {
                'count': count,
                'is_valid': is_valid
            }
        
        # 모든 형태소가 유효한지 확인
        all_morphemes_valid = all(info['is_valid'] for info in morpheme_counts.values())
        
        # 분석 결과 구성
        morpheme_analysis = {
            'keyword': keyword,
            'is_compound': is_compound_keyword,
            'morpheme_analysis': morpheme_counts
        }
        
        return {
            'char_count': char_count,
            'is_valid_char_count': is_valid_char_count,
            'morpheme_analysis': morpheme_analysis,
            'is_valid_morphemes': all_morphemes_valid
        }

    def _create_seo_optimization_prompt(self, content, keyword, analysis):
        """
        SEO 최적화를 위한 첫 번째 프롬프트
        
        Args:
            content (str): 콘텐츠
            keyword (str): 키워드
            analysis (dict): 분석 결과
            
        Returns:
            str: 프롬프트
        """
        # 글자수 정보
        char_count = analysis['char_count']
        char_count_direction = ""
        if char_count < 1700:
            char_count_direction = f"현재 {char_count}자에서 1700-2000자 범위로 확장 필요 (+{1700 - char_count}자)"
        elif char_count > 2000:
            char_count_direction = f"현재 {char_count}자에서 1700-2000자 범위로 축소 필요 (-{char_count - 2000}자)"
        else:
            char_count_direction = f"현재 {char_count}자로 적정 범위 내 유지"
        
        # 형태소 분석
        morpheme_analysis = analysis['morpheme_analysis'].get('morpheme_analysis', {})
        morpheme_issues = []
        
        for morpheme, info in morpheme_analysis.items():
            count = info.get('count', 0)
            if count < 17:
                morpheme_issues.append(f"• '{morpheme}': 현재 {count}회 → 17-20회로 증가 (+{17-count}회)")
            elif count > 20:
                morpheme_issues.append(f"• '{morpheme}': 현재 {count}회 → 17-20회로 감소 (-{count-20}회)")
        
        morpheme_text = "\n".join(morpheme_issues) if morpheme_issues else "모든 형태소가 적정 범위 내에 있습니다."
        
        return f"""
        이 블로그 콘텐츠를 SEO와 가독성 측면에서 최적화해주세요. 아래 요구사항을 충족하면서 사용자 경험을 개선해야 합니다:

        1️⃣ 글자수 요구사항: 1700-2000자 (공백 제외)
        {char_count_direction}

        2️⃣ 키워드 및 형태소 최적화: 
        '{keyword}'와 관련 형태소가 각각 17-20회 출현하도록 조정
        {morpheme_text}

        3️⃣ SEO 최적화 전략:
        • 첫 번째 문단에 핵심 키워드 자연스럽게 포함
        • 주요 소제목에 키워드 관련 문구 포함
        • 짧고 간결한 문단 사용 (2-3문장 권장)
        • 핵심 키워드의 자연스러운 분포
        • 명확한 문단 구분과 소제목 활용
        • 모바일 친화적인 짧은 문장 사용

        4️⃣ 사용자 경험 개선:
        • 글머리 기호나 번호 매기기로 내용 구조화
        • 핵심 정보를 먼저 제시하는 역피라미드 구조
        • 전문 용어는 적절한 설명과 함께 사용
        • 직관적이고 명확한 표현 사용

        원본 콘텐츠:
        {content}

        최적화된 내용만 제공해 주세요. 설명이나 메모는 포함하지 마세요.
        """
    
    def _create_seo_readability_prompt(self, content, keyword, analysis):
        """
        가독성 중심의 SEO 최적화 프롬프트
        
        Args:
            content (str): 콘텐츠
            keyword (str): 키워드
            analysis (dict): 분석 결과
            
        Returns:
            str: 프롬프트
        """
        return f"""
        이 블로그 콘텐츠를 사용자 친화적이고 SEO에 최적화된 형태로 개선해주세요. 최신 SEO 트렌드에 맞춰 다음 요소들에 집중하세요:

        1️⃣ 가독성 최적화:
        • 긴 문단을 2-3문장의 짧은 문단으로 분리
        • 복잡한 문장을 간결하게 재구성
        • 핵심 정보는 굵은 글씨나 강조 표시 활용
        • 명확한 소제목으로 콘텐츠 구조화
        • 모바일에서 읽기 쉬운 형식 적용

        2️⃣ 키워드 및 형태소 최적화:
        • '{keyword}'와 관련 형태소가 각각 17-20회 출현하도록 조정
        • 키워드 변형을 자연스럽게 배치
        • 키워드 스터핑(과도한 반복) 방지

        3️⃣ 구조적 최적화:
        • 주요 소제목(H2, H3)에 키워드 포함
        • 첫 문단에 핵심 키워드와 주제 명확히 제시
        • 글머리 기호와 번호 매기기로 내용 구조화
        • 시각적 여백과 분리를 통한 정보 구분

        4️⃣ 콘텐츠 품질 향상:
        • 전문적이고 신뢰할 수 있는 톤 유지
        • 불필요한 반복 제거
        • 핵심 가치와 중요 정보 강조
        • 행동 유도 문구(CTA) 적절히 배치

        원본 콘텐츠:
        {content}

        최적화된 콘텐츠만 제공해 주세요. 설명이나 메모는 포함하지 마세요.
        """

    def _create_ultra_seo_prompt(self, content, keyword, analysis):
        """
        강화된 SEO 최적화 프롬프트
        
        Args:
            content (str): 콘텐츠
            keyword (str): 키워드
            analysis (dict): 분석 결과
                
        Returns:
            str: 프롬프트
        """
        return f"""
        이 블로그 글을 완전한 최적화 기준에 맞추어 재구성해 주세요. 최고의 SEO 성능을 위한 명확한 지침을 따라주세요:

        1️⃣ 절대적인 글자수 요구사항: 
        • 최종 글자수(공백 제외): 1700-2000자 사이여야 함
        • 현재 글자수: {analysis['char_count']}자

        2️⃣ 엄격한 형태소 출현 빈도:
        • '{keyword}'와 관련된 모든 형태소는 반드시 17-20회 사이로 출현해야 함
        • 현재 형태소 분석:
        {json.dumps(analysis['morpheme_analysis'], ensure_ascii=False, indent=2)}

        3️⃣ 구조 최적화 (정확히 적용):
        • 첫 문단에 반드시 키워드와 그 변형어 포함
        • 모든 H2/H3 제목에 키워드 관련 용어 포함
        • 2-3문장 단위로 문단 분리
        • 중요 정보는 글머리 기호로 강조
        • 숫자는 리스트로 표시

        4️⃣ 모바일 최적화:
        • 4-5줄 이내의 짧은 문단
        • 복잡한 문장 단순화
        • 모바일에서 빠르게 스캔 가능한 형식

        5️⃣ 핵심 콘텐츠 구조:
        • 서론: 핵심 키워드로 시작, 독자 니즈 언급
        • 본론: 문제점과 해결책 제시
        • 결론: 핵심 키워드로 정리, 행동 유도

        원본 콘텐츠:
        {content}

        최적화된 콘텐츠만 제공해 주세요. 설명이나 메모는 포함하지 마세요.
        """
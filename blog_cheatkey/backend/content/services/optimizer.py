# 필요한 임포트
import re
import json
import logging
import time
import traceback
from django.conf import settings
from konlpy.tag import Okt
from anthropic import Anthropic
from content.models import BlogContent, MorphemeAnalysis
from .substitution_generator import SubstitutionGenerator
from core.services.optimization_helpers import MorphemeOptimizer, TextQualityEnsurer
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class ContentOptimizer:
    """개선된 콘텐츠 최적화 클래스"""
    
    def __init__(self):
        self.anthropic_api_key = settings.ANTHROPIC_API_KEY
        self.model = "claude-3-7-sonnet-20250219"
        self.client = Anthropic(api_key=self.anthropic_api_key)
        self.okt = Okt()
        self.substitution_generator = SubstitutionGenerator()
        self.morpheme_optimizer = MorphemeOptimizer()
        self.text_quality_ensurer = TextQualityEnsurer()
        self.max_retries = 3
        self.retry_delay = 2
    
    def optimize_existing_content_v4(self, content_id):
        """
        기존 콘텐츠를 SEO 친화적으로 최적화 - 병렬 처리 도입
        
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
            logger.info(f"콘텐츠 SEO 최적화 v4 시작: content_id={content_id}, 키워드={keyword}")
            
            # 참고자료 분리
            content_parts = self.separate_content_and_refs(content)
            content_without_refs = content_parts['content_without_refs']
            refs_section = content_parts['refs_section']
            
            # 1. 병렬로 콘텐츠 분석 및 초기 최적화 시도
            with ThreadPoolExecutor(max_workers=3) as executor:
                # 초기 분석
                analysis_future = executor.submit(self.analyze_content, content_without_refs, keyword)
                
                # API 기반 최적화 시도 (여러 방식으로 병렬 시도)
                prompt1 = self._create_seo_optimization_prompt(content_without_refs, keyword, {})
                prompt2 = self._create_seo_readability_prompt(content_without_refs, keyword, {})
                prompt3 = self._create_ultra_seo_prompt(content_without_refs, keyword, {})
                
                api_future1 = executor.submit(self._api_optimize_content, prompt1, 0.7)
                api_future2 = executor.submit(self._api_optimize_content, prompt2, 0.5)
                api_future3 = executor.submit(self._api_optimize_content, prompt3, 0.3)
                
                # 결과 수집
                initial_analysis = analysis_future.result()
                api_results = [
                    api_future1.result(),
                    api_future2.result(),
                    api_future3.result()
                ]
            
            # 2. API 결과 중 최상의 결과 선택
            best_api_result = None
            best_api_analysis = None
            
            for result in [r for r in api_results if r]:  # None이 아닌 결과만
                analysis = self.analyze_content(result, keyword)
                
                if best_api_analysis is None or self._is_seo_result_better(analysis, best_api_analysis):
                    best_api_result = result
                    best_api_analysis = analysis
                    logger.info(f"더 나은 API 결과 발견: 글자수={analysis['char_count']}, 형태소 유효={analysis['is_valid_morphemes']}")
                
                # 모든 조건 만족 시 중단
                if analysis['is_valid_char_count'] and analysis['is_valid_morphemes']:
                    logger.info("API 최적화 성공: 모든 조건 충족")
                    break
            
            # 3. 강제 최적화 실행 (API 결과 또는 원본 콘텐츠 사용)
            content_to_optimize = best_api_result if best_api_result else content_without_refs
            
            # 최적화 결과가 충분히 좋지 않은 경우에만 추가 최적화 시도
            needs_further_optimization = (best_api_analysis is None or 
                                        not best_api_analysis['is_fully_optimized'])
            
            if needs_further_optimization:
                # 개선된 강제 최적화 (병렬 처리 활용)
                optimized_content = self._optimized_enforce_seo(content_to_optimize, keyword)
            else:
                optimized_content = content_to_optimize
            
            # 4. 최종 분석
            final_analysis = self.analyze_content(optimized_content, keyword)
            logger.info(f"최종 결과: 글자수={final_analysis['char_count']}, 형태소 유효={final_analysis['is_valid_morphemes']}")
            
            # 5. 텍스트 일관성 확인 및 개선
            optimized_content = self.text_quality_ensurer.ensure_coherence(optimized_content)
            
            # 6. 모바일 최적화 포맷 생성
            mobile_formatted_content = self._format_for_mobile(optimized_content)
            
            # 7. 참고자료 다시 추가
            if refs_section:
                optimized_content = optimized_content + "\n\n" + refs_section
                mobile_formatted_content = mobile_formatted_content + "\n\n" + refs_section
            
            # 8. 콘텐츠 업데이트
            blog_content.content = optimized_content
            blog_content.mobile_formatted_content = mobile_formatted_content
            blog_content.char_count = final_analysis['char_count']
            blog_content.is_optimized = True
            
            # 9. 최적화 메타데이터 저장
            meta_data = {
                'original_char_count': len(content.replace(" ", "")),
                'final_char_count': final_analysis['char_count'],
                'is_valid_char_count': final_analysis['is_valid_char_count'],
                'is_valid_morphemes': final_analysis['is_valid_morphemes'],
                'optimization_date': time.strftime("%Y-%m-%d %H:%M:%S"),
                'algorithm_version': 'v4',
                'attempts': len([r for r in api_results if r])
            }
            blog_content.meta_data = meta_data
            blog_content.save()
            
            # 10. 기존 형태소 분석 결과 삭제
            blog_content.morpheme_analyses.all().delete()
            
            # 11. 새로운 형태소 분석 결과 저장
            self._save_morpheme_analysis(blog_content, final_analysis['morpheme_analysis'])
            
            return {
                'success': True,
                'message': "콘텐츠가 성공적으로 SEO 최적화되었습니다.",
                'content_id': content_id,
                'is_valid_char_count': final_analysis['is_valid_char_count'],
                'is_valid_morphemes': final_analysis['is_valid_morphemes'],
                'char_count': final_analysis['char_count'],
                'algorithm_version': 'v4'
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
    
    def _api_optimize_content(self, prompt, temperature):
        """API를 통한 콘텐츠 최적화 시도"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
        except Exception as e:
            logger.error(f"API 최적화 오류: {str(e)}")
            return None
    
    def _optimized_enforce_seo(self, content, keyword):
        """병렬 처리를 활용한 SEO 강제 최적화"""
        # 1단계: 필요한 모든 분석 수행
        morpheme_analysis = self.analyze_content(content, keyword)
        
        # 개선이 필요한지 확인
        if (morpheme_analysis['is_valid_char_count'] and 
            morpheme_analysis['is_valid_morphemes']):
            return content
        
        # 2단계: 글자 수 조정 (필요한 경우)
        if not morpheme_analysis['is_valid_char_count']:
            # 글자 수 범위의 중간값으로 조정
            target_chars = (1700 + 2000) // 2
            content = self.force_limit_char_count(content, target_chars)
        
        # 3단계: 각 형태소의 출현 빈도 최적화
        morpheme_targets = {}
        for morpheme, info in morpheme_analysis['morpheme_analysis'].get('morpheme_analysis', {}).items():
            if not info.get('is_valid', True):
                # 17-20 범위의 중간값으로 설정
                morpheme_targets[morpheme] = 18
        
        # 최적화가 필요한 경우
        if morpheme_targets:
            # 병렬로 섹션 단위 최적화 실행
            sections = re.split(r'(###\s+.*?\n)', content)
            processed_sections = []
            
            with ThreadPoolExecutor(max_workers=min(4, len(sections))) as executor:
                futures = []
                
                for section in sections:
                    # 제목 섹션은 그대로 유지
                    if section.strip().startswith('###'):
                        processed_sections.append(section)
                        continue
                    
                    # 본문 섹션만 병렬 최적화
                    if section.strip():
                        # 섹션별 목표 분배 (섹션 길이에 비례)
                        section_targets = self._distribute_targets_by_length(
                            morpheme_targets, 
                            section, 
                            content
                        )
                        futures.append(executor.submit(
                            self._optimize_section_morphemes,
                            section,
                            section_targets
                        ))
                
                # 결과 수집
                for future in futures:
                    processed_sections.append(future.result())
            
            # 섹션 재결합
            content = ''.join(processed_sections)
            
            # 최종 일관성 확인
            content = self.text_quality_ensurer.ensure_coherence(content)
        
        return content
    
    def _distribute_targets_by_length(self, morpheme_targets, section, full_content):
        """섹션 길이에 비례하여 형태소 목표치 분배"""
        section_ratio = len(section) / len(full_content)
        section_targets = {}
        
        for morpheme, target in morpheme_targets.items():
            # 현재 섹션의 형태소 출현 횟수
            current_count = self.morpheme_optimizer.count_exact_word(morpheme, section)
            
            # 비율 기반 목표 설정 (최소 1, 최대 target)
            section_target = max(1, min(target, round(target * section_ratio)))
            
            # 현재 값이 이미 목표 범위 내에 있으면 그대로 유지
            if 17 <= current_count <= 20:
                continue
                
            section_targets[morpheme] = section_target
        
        return section_targets
    
    def _optimize_section_morphemes(self, section, morpheme_targets):
        """섹션 단위 형태소 최적화"""
        if not morpheme_targets:
            return section
            
        result = section
        
        # 각 형태소별로 최적화
        for morpheme, target in morpheme_targets.items():
            current_count = self.morpheme_optimizer.count_exact_word(morpheme, result)
            
            # 이미 목표 범위 내에 있으면 건너뛰기
            if 17 <= current_count <= 20:
                continue
                
            # 추가 필요
            if current_count < target:
                result = self._add_morpheme_strategically(result, morpheme, target - current_count)
            # 제거 필요
            elif current_count > target:
                result = self._reduce_morpheme_strategically(result, morpheme, current_count - target)
        
        return result
    
    def _save_morpheme_analysis(self, blog_content, morpheme_analysis):
        """형태소 분석 결과 저장 - 배치 처리 적용"""
        # 배치 처리를 위한 객체 리스트
        morpheme_objects = []
        
        for morpheme, info in morpheme_analysis.get('morpheme_analysis', {}).items():
            if len(morpheme) >= 2:  # 2글자 이상만 저장
                morpheme_objects.append(
                    MorphemeAnalysis(
                        content=blog_content,
                        morpheme=morpheme,
                        count=info.get('count', 0),
                        is_valid=info.get('is_valid', False)
                    )
                )
        
        # 배치 생성 (bulk_create)
        if morpheme_objects:
            MorphemeAnalysis.objects.bulk_create(morpheme_objects)
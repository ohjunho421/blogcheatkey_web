import re
import json
import logging
import time
import asyncio
from django.conf import settings
from konlpy.tag import Okt
from anthropic import Anthropic
from content.models import BlogContent, MorphemeAnalysis
from formatter import ContentFormatter  # formatter.py에서 ContentFormatter 클래스 가져오기

logger = logging.getLogger(__name__)

class ContentOptimizer:
    """
    Claude API를 사용한 블로그 콘텐츠 최적화 클래스
    주요 기능: 글자수, 키워드 출현 횟수 확인 및 최적화
    """
    
    def __init__(self):
        self.anthropic_api_key = settings.ANTHROPIC_API_KEY
        self.model = "claude-3-opus-20240229"  # 최신 모델로 업데이트 필요
        self.client = Anthropic(api_key=self.anthropic_api_key)
        self.okt = Okt()
    
    def optimize_existing_content(self, content_id):
        """
        기존 콘텐츠를 최적화
        
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
            
            # 최적화 결과 가져오기
            result = self.validate_and_optimize_content(content, keyword)
            
            # 최적화된 콘텐츠가 있으면 업데이트
            if not result['is_valid'] and 'optimized_content' in result:
                optimized_content = result['optimized_content']
                
                # 참고 자료 섹션 보존 (최적화된 콘텐츠에 추가)
                if "## 참고자료" in content:
                    if "## 참고자료" not in optimized_content:
                        ref_section = content.split("## 참고자료")[1]
                        optimized_content += "\n\n## 참고자료" + ref_section
                
                # 모바일 최적화 포맷 생성 - formatter 사용
                formatter = ContentFormatter()
                mobile_formatted_content = formatter.format_for_mobile(optimized_content)
                
                # 콘텐츠 업데이트
                blog_content.content = optimized_content
                blog_content.mobile_formatted_content = mobile_formatted_content
                blog_content.char_count = len(optimized_content.replace(" ", ""))
                blog_content.is_optimized = True
                
                # 최적화 메타데이터 저장
                meta_data = {
                    'original_char_count': result.get('validation_details', {}).get('char_count', {}).get('count', 0),
                    'final_char_count': len(optimized_content.replace(" ", "")),
                    'keyword_count': result.get('optimization_validation', {}).get('keyword_count', {}).get('count', 0),
                    'optimization_date': time.strftime("%Y-%m-%d %H:%M:%S")
                }
                blog_content.meta_data = meta_data
                blog_content.save()
                
                # 기존 형태소 분석 결과 삭제
                blog_content.morpheme_analyses.all().delete()
                
                # 새로운 형태소 분석 결과 저장
                morpheme_analysis = self.analyze_morphemes(optimized_content, keyword)
                for morpheme, info in morpheme_analysis.get('morpheme_analysis', {}).items():
                    MorphemeAnalysis.objects.create(
                        content=blog_content,
                        morpheme=morpheme,
                        count=info.get('count', 0),
                        is_valid=info.get('is_valid', False)
                    )
                
                result['success'] = True
                result['message'] = "콘텐츠가 성공적으로 최적화되었습니다."
                result['content_id'] = content_id
            else:
                result['success'] = True
                result['message'] = "이미 최적화된 콘텐츠입니다."
                result['content_id'] = content_id
                
            return result
            
        except BlogContent.DoesNotExist:
            return {
                'success': False,
                'message': f"ID {content_id}에 해당하는 콘텐츠를 찾을 수 없습니다.",
                'content_id': content_id
            }
        except Exception as e:
            logger.error(f"콘텐츠 최적화 중 오류 발생: {str(e)}")
            return {
                'success': False,
                'message': f"콘텐츠 최적화 중 오류 발생: {str(e)}",
                'content_id': content_id
            }
    
    def validate_and_optimize_content(self, content, keyword):
        """
        콘텐츠가 조건을 만족하는지 확인하고, 필요한 경우 최적화합니다.
        
        Args:
            content (str): 검증할 콘텐츠
            keyword (str): 주요 키워드
            
        Returns:
            dict: 검증 결과와 최적화된 콘텐츠(필요한 경우)
        """
        # 참고자료 섹션 제외 (검증 및 최적화시)
        content_without_refs = content
        refs_section = ""
        
        if "## 참고자료" in content:
            content_parts = content.split("## 참고자료", 1)
            content_without_refs = content_parts[0]
            refs_section = "## 참고자료" + content_parts[1]
        
        # 글자수 검증 (공백 제외)
        char_count = len(content_without_refs.replace(" ", ""))
        is_valid_length = 1700 <= char_count <= 2000
        
        # 키워드 출현 횟수 검증
        keyword_count = self._count_exact_word(keyword, content_without_refs)
        is_valid_keyword_count = 17 <= keyword_count <= 20
        
        # 형태소 분석 및 검증
        morpheme_analysis = self.analyze_morphemes(content_without_refs, keyword)
        is_valid_morphemes = morpheme_analysis.get('is_valid', False)
        
        # 종합 검증 결과
        is_valid = is_valid_length and is_valid_keyword_count and is_valid_morphemes
        
        result = {
            'is_valid': is_valid,
            'original_content': content,
            'validation_details': {
                'char_count': {
                    'count': char_count,
                    'is_valid': is_valid_length,
                    'target': '1700-2000자'
                },
                'keyword_count': {
                    'count': keyword_count,
                    'is_valid': is_valid_keyword_count,
                    'target': '17-20회'
                },
                'morpheme_analysis': morpheme_analysis
            }
        }
        
        # 조건을 만족하지 않을 경우 콘텐츠 최적화
        if not is_valid:
            try:
                # 최대 3번까지 최적화 시도
                for attempt in range(3):
                    # 데이터 구성
                    morphemes = self.okt.morphs(keyword)
                    data = {
                        'keyword': keyword,
                        'morphemes': morphemes
                    }
                    
                    # 최적화 프롬프트 생성 및 API 호출
                    optimization_prompt = self._create_optimization_prompt(
                        content_without_refs, 
                        data, 
                        attempt > 0  # 두 번째 이상 시도일 경우 더 엄격한 요구사항
                    )
                    
                    optimization_response = self.client.messages.create(
                        model=self.model,
                        max_tokens=4096,
                        temperature=0.3,  # 더 결정적인 응답을 위해 온도 낮춤
                        messages=[
                            {"role": "user", "content": optimization_prompt}
                        ]
                    )
                    
                    optimized_content = optimization_response.content[0].text
                    
                    # 참고자료 섹션 다시 추가
                    if refs_section and "## 참고자료" not in optimized_content:
                        optimized_content = optimized_content + "\n\n" + refs_section
                    
                    # 최적화 결과 재검증
                    optimized_char_count = len(optimized_content.replace(" ", ""))
                    optimized_keyword_count = self._count_exact_word(keyword, optimized_content)
                    optimized_morpheme_analysis = self.analyze_morphemes(optimized_content, keyword)
                    
                    # 결과 검증
                    is_length_valid = 1700 <= optimized_char_count <= 2000
                    is_keyword_valid = 17 <= optimized_keyword_count <= 20
                    is_morphemes_valid = optimized_morpheme_analysis.get('is_valid', False)
                    
                    # 모든 조건이 만족되면 최적화 종료
                    if is_length_valid and is_keyword_valid and is_morphemes_valid:
                        result['optimized_content'] = optimized_content
                        result['optimization_validation'] = {
                            'char_count': {
                                'count': optimized_char_count,
                                'is_valid': is_length_valid
                            },
                            'keyword_count': {
                                'count': optimized_keyword_count,
                                'is_valid': is_keyword_valid
                            },
                            'morpheme_analysis': optimized_morpheme_analysis,
                            'attempt': attempt + 1
                        }
                        break
                    
                    # 마지막 시도이거나 많이 개선되었으면 그대로 반환
                    if attempt == 2 or (is_length_valid and is_keyword_valid):
                        result['optimized_content'] = optimized_content
                        result['optimization_validation'] = {
                            'char_count': {
                                'count': optimized_char_count,
                                'is_valid': is_length_valid
                            },
                            'keyword_count': {
                                'count': optimized_keyword_count,
                                'is_valid': is_keyword_valid
                            },
                            'morpheme_analysis': optimized_morpheme_analysis,
                            'attempt': attempt + 1,
                            'warning': "모든 조건을 만족하지 않지만 최대한 최적화되었습니다."
                        }
                        break
                
                # 최적화 시도가 끝났으나 결과가 없으면
                if 'optimized_content' not in result:
                    result['optimized_content'] = optimized_content
                    result['optimization_validation'] = {
                        'char_count': {
                            'count': optimized_char_count,
                            'is_valid': is_length_valid
                        },
                        'keyword_count': {
                            'count': optimized_keyword_count,
                            'is_valid': is_keyword_valid
                        },
                        'morpheme_analysis': optimized_morpheme_analysis,
                        'warning': "최적화 시도가 모두 실패했습니다. 마지막 결과를 반환합니다."
                    }
                
            except Exception as e:
                logger.error(f"콘텐츠 최적화 API 호출 중 오류: {str(e)}")
                result['optimization_error'] = str(e)
        
        return result
    
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
            if len(morpheme) < 2:  # 1글자 형태소는 건너뛰기 (의미있는 분석이 어려움)
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
        # 한글의 경우 경계가 명확하지 않아 다른 패턴 필요
        if re.search(r'[가-힣]', word):
            pattern = rf'(?<![가-힣]){re.escape(word)}(?![가-힣])'
        else:
            pattern = rf'\b{re.escape(word)}\b'
        
        return len(re.findall(pattern, text))
    
    def _create_optimization_prompt(self, content, data, strict=False):
        """
        콘텐츠 최적화 프롬프트 생성
        
        Args:
            content (str): 최적화할 콘텐츠
            data (dict): 키워드와 형태소 정보
            strict (bool): 더 엄격한 요구사항 적용 여부
        """
        keyword = data['keyword']
        morphemes = data.get('morphemes', self.okt.morphs(keyword))
        
        # 짧은 형태소 필터링 (의미 있는 분석이 어려움)
        filtered_morphemes = [m for m in morphemes if len(m) >= 2]
        
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
        
        # 각 형태소 최적화 가이드
        morpheme_guides = []
        for morpheme in filtered_morphemes:
            count = current_counts.get(morpheme, 0)
            target = "17-20"
            status = ""
            
            if count < 17:
                status = f"현재 {count}회로 부족함. {17-count}회 이상 추가 필요"
            elif count > 20:
                status = f"현재 {count}회로 과다함. {count-20}회 이상 줄여야 함"
            else:
                status = f"이미 적정 범위({count}회)"
                
            morpheme_guides.append(f"- '{morpheme}': {status}")
        
        morpheme_guide_text = "\n".join(morpheme_guides)
        
        # 더 엄격한 요구사항 적용
        strict_instructions = ""
        if strict:
            strict_instructions = """
            ⚠️ 이전 최적화 시도가 실패했습니다. 이번에는 더 엄격하게 지침을 따라주세요:
            
            1. 각 형태소와 키워드의 출현 횟수를 **정확히** 17-20회 범위로 조정해야 합니다.
            2. 각 형태소를 조정할 때 다른 형태소의 횟수가 함께 변하는 것에 주의하세요.
            3. 필요하다면 문장 구조를 완전히 재구성할 수 있습니다.
            4. 각 형태소의 현재 출현 횟수를 고려하여 과다한 것은 줄이고, 부족한 것은 늘리세요.
            5. 최종 글자수가 정확히 1700-2000자 범위 내에 있어야 합니다.
            6. 처음부터 새로 작성하지 말고, 현재 콘텐츠를 기반으로 수정하세요.
            """

        return f"""
        다음 블로그 글을 최적화해주세요. 다음의 출현 횟수 제한을 반드시 지켜주세요:

        🎯 목표:
        1. 키워드 '{keyword}': 정확히 17-20회 사용
        2. 중요 형태소: 각각 정확히 17-20회 사용
        3. 전체 글자수: 1700-2000자 (공백 제외)
        
        📊 현재 상태:
        - 글자수: {len(content.replace(" ", ""))}자
        - '{keyword}': {current_counts.get(keyword, 0)}회
        
        📋 형태소별 최적화 가이드:
        {morpheme_guide_text}
        
        {strict_instructions}
        
        ✂️ 과다 사용된 단어 최적화 방법 (우선순위 순):
        {example_instructions}

        ⚠️ 중요:
        - 각 형태소와 키워드가 정확히 17-20회 범위 내에서 사용되어야 함
        - 전체 글자수는 1700-2000자 범위 내로 조정(공백 제외)
        - ctrl+f로 검색했을 때의 횟수를 기준으로 함
        - 전체 문맥의 자연스러움을 반드시 유지
        - 전문성과 가독성의 균형 유지
        - 동의어/유의어 사용을 우선으로 하고, 자연스러운 경우에만 생략이나 지시어 사용
        - 내용의 주요 의미는 유지할 것
        - 원본의 주요 내용과 구조를 최대한 유지하되, 형태소 빈도를 조정하세요

       원문:
       {content}

       위 지침에 따라 모든 형태소가 17-20회 범위 내에 들도록 자연스럽게 수정해주세요.
       전문성은 유지하되 읽기 쉽게 수정해주세요.
       수정된 콘텐츠만 제공하고, 설명이나 다른 텍스트는 포함하지 마세요.
       """
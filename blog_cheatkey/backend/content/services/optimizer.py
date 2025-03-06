# optimizier.py
import re
import json
import logging
import time
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
                    ref_section = content.split("## 참고자료")[1]
                    if "## 참고자료" not in optimized_content:
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
    
    def batch_optimize_contents(self, keyword_id=None, user_id=None, limit=10):
        """
        여러 콘텐츠를 일괄 최적화
        
        Args:
            keyword_id (int, optional): 특정 키워드의 콘텐츠만 최적화
            user_id (int, optional): 특정 사용자의 콘텐츠만 최적화
            limit (int): 최대 처리할 콘텐츠 수
            
        Returns:
            dict: 최적화 결과 요약
        """
        # 최적화할 콘텐츠 쿼리
        query = BlogContent.objects.filter(is_optimized=False)
        
        if keyword_id:
            query = query.filter(keyword_id=keyword_id)
        
        if user_id:
            query = query.filter(user_id=user_id)
        
        content_ids = list(query.order_by('-created_at')[:limit].values_list('id', flat=True))
        
        results = {
            'total': len(content_ids),
            'successful': 0,
            'failed': 0,
            'details': []
        }
        
        # 각 콘텐츠 최적화
        for content_id in content_ids:
            result = self.optimize_existing_content(content_id)
            
            if result.get('success', False):
                results['successful'] += 1
            else:
                results['failed'] += 1
            
            results['details'].append({
                'content_id': content_id,
                'success': result.get('success', False),
                'message': result.get('message', '')
            })
        
        return results
    
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
                # 데이터 구성
                morphemes = self.okt.morphs(keyword)
                data = {
                    'keyword': keyword,
                    'morphemes': morphemes
                }
                
                # 최적화 프롬프트 생성 및 API 호출
                optimization_prompt = self._create_optimization_prompt(content_without_refs, data)
                optimization_response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    temperature=0.5,
                    messages=[
                        {"role": "user", "content": optimization_prompt}
                    ]
                )
                
                optimized_content = optimization_response.content[0].text
                
                # 참고자료 섹션 다시 추가
                if refs_section:
                    optimized_content = optimized_content + "\n\n" + refs_section
                
                # 최적화 결과 재검증
                optimized_char_count = len(optimized_content.replace(" ", ""))
                optimized_keyword_count = self._count_exact_word(keyword, optimized_content)
                optimized_morpheme_analysis = self.analyze_morphemes(optimized_content, keyword)
                
                result['optimized_content'] = optimized_content
                result['optimization_validation'] = {
                    'char_count': {
                        'count': optimized_char_count,
                        'is_valid': 1700 <= optimized_char_count <= 2000
                    },
                    'keyword_count': {
                        'count': optimized_keyword_count,
                        'is_valid': 17 <= optimized_keyword_count <= 20
                    },
                    'morpheme_analysis': optimized_morpheme_analysis
                }
            except Exception as e:
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
        3. 전체 글자수: 1700-2000자 (공백 제외)
        
        📊 현재 상태:
        - 글자수: {len(content.replace(" ", ""))}자
        {chr(10).join([f"- '{word}': {count}회" for word, count in current_counts.items()])}

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

       원문:
       {content}

       위 지침에 따라 과다 사용된 형태소들을 최적화하여 모든 형태소가 17-20회 범위 내에 들도록 
       자연스럽게 수정해주세요. 전문성은 유지하되 읽기 쉽게 수정해주세요.
       """


# 유틸리티 함수: CLI에서 실행 가능하도록 명령행 인터페이스 제공
def run_optimizer(content_id=None, keyword_id=None, user_id=None, batch=False, limit=10):
   """
   최적화 실행 유틸리티 함수
   
   Args:
       content_id (int, optional): 최적화할 콘텐츠 ID
       keyword_id (int, optional): 특정 키워드의 콘텐츠만 최적화
       user_id (int, optional): 특정 사용자의 콘텐츠만 최적화
       batch (bool): 일괄 최적화 모드 여부
       limit (int): 일괄 최적화시 최대 처리할 콘텐츠 수
   """
   optimizer = ContentOptimizer()
   
   if batch:
       results = optimizer.batch_optimize_contents(keyword_id, user_id, limit)
       print(f"일괄 최적화 완료: {results['successful']}/{results['total']} 성공")
       return results
   elif content_id:
       result = optimizer.optimize_existing_content(content_id)
       print(f"콘텐츠 {content_id} 최적화 결과: {result['message']}")
       return result
   else:
       print("최적화할 콘텐츠 ID 또는 일괄 최적화 옵션을 지정해주세요.")
       return {"error": "파라미터 오류"}


# 스크립트로 직접 실행될 경우
if __name__ == "__main__":
   import django
   import os
   import sys
   import argparse
   
   # Django 설정 로드
   os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blog_cheatkey.settings')
   django.setup()
   
   # 명령행 인자 파싱
   parser = argparse.ArgumentParser(description='블로그 콘텐츠 최적화 도구')
   parser.add_argument('--content-id', type=int, help='최적화할 콘텐츠 ID')
   parser.add_argument('--keyword-id', type=int, help='특정 키워드 ID의 콘텐츠만 최적화')
   parser.add_argument('--user-id', type=int, help='특정 사용자 ID의 콘텐츠만 최적화')
   parser.add_argument('--batch', action='store_true', help='일괄 최적화 모드')
   parser.add_argument('--limit', type=int, default=10, help='일괄 최적화시 최대 처리할 콘텐츠 수')
   
   args = parser.parse_args()
   
   # 최적화 실행
   run_optimizer(
       content_id=args.content_id,
       keyword_id=args.keyword_id,
       user_id=args.user_id,
       batch=args.batch,
       limit=args.limit
   )
"""형태소 관련 서비스"""
import re
from konlpy.tag import Okt
from concurrent.futures import ThreadPoolExecutor
from core.utils.caching import cache_result

class MorphemeService:
    """형태소 분석 및 처리 서비스"""
    
    def __init__(self):
        self.okt = Okt()
        self._local_cache = {}
    
    @cache_result(ttl=3600)
    def analyze_morphemes(self, text, keyword, custom_morphemes=None):
        """
        형태소 분석 및 출현 횟수 검증 (캐싱 적용)
        
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
        
        # 키워드와 형태소 추출 (병렬 처리 적용)
        keyword_count = self._count_exact_word(keyword, text)
        morphemes = self.okt.morphs(keyword)
        
        # 사용자 지정 형태소 추가
        if custom_morphemes:
            morphemes.extend(custom_morphemes)
        morphemes = list(set(morphemes))  # 중복 제거

        # 중요 형태소만 필터링 (2글자 이상)
        morphemes = [m for m in morphemes if len(m) >= 2]

        # 병렬로 형태소 빈도 계산
        morpheme_counts = self._parallelize_morpheme_counting(morphemes, text)
        
        # 분석 결과 구성
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
            count = morpheme_counts.get(morpheme, 0)
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
        """
        cache_key = f"{word}:{hash(text)}"
        if cache_key in self._local_cache:
            return self._local_cache[cache_key]
        
        # 한글의 경우 경계가 명확하지 않아 다른 패턴 필요
        if re.search(r'[가-힣]', word):
            pattern = rf'(?<![가-힣]){re.escape(word)}(?![가-힣])'
        else:
            pattern = rf'\b{re.escape(word)}\b'
        
        count = len(re.findall(pattern, text))
        self._local_cache[cache_key] = count
        return count
    
    def _parallelize_morpheme_counting(self, morphemes, text, chunks=4):
        """병렬 형태소 카운팅"""
        if len(morphemes) <= 1:
            return {m: self._count_exact_word(m, text) for m in morphemes}
        
        # 형태소를 청크로 분할
        chunk_size = max(1, len(morphemes) // chunks)
        morpheme_chunks = [morphemes[i:i + chunk_size] for i in range(0, len(morphemes), chunk_size)]
        
        results = {}
        with ThreadPoolExecutor(max_workers=min(chunks, len(morpheme_chunks))) as executor:
            # 각 청크에 대한 처리 함수
            def process_chunk(mlist):
                return {m: self._count_exact_word(m, text) for m in mlist}
            
            # 병렬 실행
            futures = [executor.submit(process_chunk, chunk) for chunk in morpheme_chunks]
            
            # 결과 수집
            for future in futures:
                results.update(future.result())
        
        return results
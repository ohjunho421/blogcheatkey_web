"""형태소 최적화를 위한 유틸리티 클래스"""
import re
from konlpy.tag import Okt
from multiprocessing import Pool

class MorphemeOptimizer:
    def __init__(self):
        self.okt = Okt()
        self.local_cache = {}
    
    def count_exact_word(self, word, text):
        """최적화된 단어 카운팅 함수"""
        cache_key = f"{word}:{hash(text)}"
        if cache_key in self.local_cache:
            return self.local_cache[cache_key]
        
        # 한글의 경우 경계가 명확하지 않아 다른 패턴 필요
        if re.search(r'[가-힣]', word):
            pattern = rf'(?<![가-힣]){re.escape(word)}(?![가-힣])'
        else:
            pattern = rf'\b{re.escape(word)}\b'
        
        count = len(re.findall(pattern, text))
        self.local_cache[cache_key] = count
        return count
    
    def parallelize_morpheme_counting(self, morphemes, text, chunks=4):
        """병렬 형태소 카운팅"""
        if len(morphemes) <= 1:
            return {m: self.count_exact_word(m, text) for m in morphemes}
        
        # 형태소를 청크로 분할
        chunk_size = max(1, len(morphemes) // chunks)
        morpheme_chunks = [morphemes[i:i + chunk_size] for i in range(0, len(morphemes), chunk_size)]
        
        # 병렬 처리 함수
        def count_chunk(chunk):
            return {m: self.count_exact_word(m, text) for m in chunk}
        
        # 병렬 실행
        with Pool(processes=min(chunks, len(morpheme_chunks))) as pool:
            results = pool.map(count_chunk, morpheme_chunks)
        
        # 결과 병합
        final_counts = {}
        for result in results:
            final_counts.update(result)
        
        return final_counts
    
    def find_best_substitution_points(self, text, morpheme, current_count, target_count):
        """최적의 대체 지점 찾기"""
        if current_count == target_count:
            return []
        
        # 문단 분리
        paragraphs = re.split(r'\n\n+', text)
        
        # 각 문단의 형태소 출현 분석
        paragraph_stats = []
        for i, para in enumerate(paragraphs):
            count = self.count_exact_word(morpheme, para)
            if count > 0:
                # 문단 길이에 따른 정규화된 형태소 밀도 계산
                density = count / len(para)
                paragraph_stats.append({
                    'index': i,
                    'count': count,
                    'density': density,
                    'text': para
                })
        
        # 형태소 추가 필요
        if current_count < target_count:
            # 형태소 밀도가 낮은 문단 선택 (밀도 오름차순)
            paragraph_stats.sort(key=lambda x: x['density'])
            return paragraph_stats[:target_count - current_count]
        
        # 형태소 제거 필요
        else:
            # 형태소 밀도가 높은 문단 선택 (밀도 내림차순)
            paragraph_stats.sort(key=lambda x: x['density'], reverse=True)
            return paragraph_stats[:current_count - target_count]

class TextQualityEnsurer:
    """텍스트 품질 보장 유틸리티"""
    
    @staticmethod
    def ensure_coherence(text):
        """텍스트 일관성 확인 및 개선"""
        # 문단 간 연결 확인
        paragraphs = re.split(r'\n\n+', text)
        if len(paragraphs) <= 1:
            return text
            
        # 연결어 패턴 확인
        connectors = ['그러나', '하지만', '또한', '따라서', '그리고', '그래서', '게다가', '반면에']
        for i in range(1, len(paragraphs)):
            first_sentence = re.split(r'[.!?]\s+', paragraphs[i])[0]
            has_connector = any(first_sentence.startswith(conn) for conn in connectors)
            
            # 연결어가 없으면 문맥에 맞는 연결어 추가
            if not has_connector and len(first_sentence.split()) > 3:
                prev_last_sentence = re.split(r'[.!?]\s+', paragraphs[i-1])[-1]
                appropriate_connector = TextQualityEnsurer._select_connector(prev_last_sentence, first_sentence)
                
                if appropriate_connector:
                    paragraphs[i] = appropriate_connector + " " + paragraphs[i]
        
        return "\n\n".join(paragraphs)
    
    @staticmethod
    def _select_connector(prev_sentence, next_sentence):
        """문맥에 맞는 연결어 선택"""
        # 간단한 구현 - 실제로는 더 복잡한 NLP 로직 필요
        if '문제' in prev_sentence or '단점' in prev_sentence or '어려움' in prev_sentence:
            return '하지만'
        elif '장점' in prev_sentence or '이점' in prev_sentence:
            return '또한'
        elif '이유' in prev_sentence or '원인' in prev_sentence:
            return '따라서'
        else:
            return '그리고'
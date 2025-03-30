// src/api/keywordService.js
import client from './client';

// 재시도 로직을 가진 요청 함수 (contentService.js와 동일)
const requestWithRetry = async (requestFn, retryConfig = {}) => {
  const { 
    maxRetries = 3, 
    retryDelay = 1000, 
    timeout = 30000 
  } = retryConfig;
  
  let retries = 0;
  
  while (retries <= maxRetries) {
    try {
      // 타임아웃 설정
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);
      
      const response = await requestFn({
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      retries++;
      
      // 최대 재시도 횟수 초과 시 에러 throw
      if (retries > maxRetries) {
        throw error;
      }
      
      // 서버에서 실제 오류가 반환된 경우(400, 500 등) 재시도하지 않음
      if (error.response) {
        throw error;
      }
      
      console.log(`키워드 요청 실패, 재시도 중... (${retries}/${maxRetries})`);
      
      // 지수 백오프: 점점 더 길게 기다림
      const delay = retryDelay * Math.pow(2, retries - 1);
      await new Promise(r => setTimeout(r, delay));
    }
  }
};

export const keywordService = {
  // 키워드 목록 조회
  getKeywords: () => requestWithRetry(
    (config) => client.get('/key-word/', config),  // key_word/ -> key-word/
    { maxRetries: 3, retryDelay: 1000, timeout: 30000 }
  ),
  
  // 분석된 키워드 목록만 조회
  getAnalyzedKeywords: () => requestWithRetry(
    (config) => client.get('/key-word/?analyzed=true', config),  // key_word/ -> key-word/
    { maxRetries: 3, retryDelay: 1000, timeout: 30000 }
  ),
  
  // 특정 키워드 조회
  getKeyword: (id) => requestWithRetry(
    (config) => client.get(`/key-word/${id}/`, config),  // key_word/ -> key-word/
    { maxRetries: 2, retryDelay: 1000, timeout: 20000 }
  ),
  
  // 키워드 추가
  addKeyword: (data) => requestWithRetry(
    (config) => client.post('/key-word/', data, config),  // key_word/ -> key-word/
    { maxRetries: 2, retryDelay: 2000, timeout: 30000 }
  ),
  
  // createKeyword를 addKeyword의 별칭으로 추가
  createKeyword: (data) => requestWithRetry(
    (config) => client.post('/key-word/', data, config),  // key_word/ -> key-word/
    { maxRetries: 2, retryDelay: 2000, timeout: 30000 }
  ),
  
  // 키워드 분석 요청
  analyzeKeyword: (id) => requestWithRetry(
    (config) => client.post(`/key-word/${id}/analyze/`, {}, config),  // key_word/ -> key-word/
    { maxRetries: 2, retryDelay: 2000, timeout: 60000 }
  ),
  
  // 키워드 상태 확인
  getKeywordStatus: (id) => requestWithRetry(
    (config) => client.get(`/key-word/${id}/status/`, config),  // key_word/ -> key-word/
    { maxRetries: 4, retryDelay: 1000, timeout: 20000 }
  ),
  
  // 키워드 업데이트
  updateKeyword: (id, data) => requestWithRetry(
    (config) => client.put(`/key-word/${id}/`, data, config),  // key_word/ -> key-word/
    { maxRetries: 2, retryDelay: 1000, timeout: 30000 }
  ),
  
  updateSubtopics: (id, subtopics) => requestWithRetry(
    (config) => client.post(`/key-word/${id}/update_subtopics/`, { subtopics }, config),
    { maxRetries: 2, retryDelay: 1000, timeout: 30000 }
  ),

  // 키워드 삭제
  deleteKeyword: (id) => requestWithRetry(
    (config) => client.delete(`/key-word/${id}/`, config),  // key_word/ -> key-word/
    { maxRetries: 2, retryDelay: 1000, timeout: 20000 }
  )
};

// 키워드 캐싱 서비스
export const keywordCacheService = {
  // 캐시에서 키워드 데이터 가져오기
  getCachedKeywords: () => {
    try {
      const cachedData = localStorage.getItem('cachedKeywordData');
      return cachedData ? JSON.parse(cachedData) : null;
    } catch (err) {
      console.error('캐시된 키워드 데이터 조회 실패:', err);
      return null;
    }
  },
  
  // 키워드 데이터 캐싱
  cacheKeywords: (data) => {
    try {
      localStorage.setItem('cachedKeywordData', JSON.stringify(data));
      return true;
    } catch (err) {
      console.error('키워드 데이터 캐싱 실패:', err);
      return false;
    }
  },
  
  // 캐시 지우기
  clearCache: () => {
    try {
      localStorage.removeItem('cachedKeywordData');
      return true;
    } catch (err) {
      console.error('캐시 삭제 실패:', err);
      return false;
    }
  }
};

export default keywordService;
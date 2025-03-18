// src/api/researchService.js
import client from './client';

// 재시도 로직을 가진 요청 함수
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
      
      console.log(`연구 자료 요청 실패, 재시도 중... (${retries}/${maxRetries})`);
      
      // 지수 백오프: 점점 더 길게 기다림
      const delay = retryDelay * Math.pow(2, retries - 1);
      await new Promise(r => setTimeout(r, delay));
    }
  }
};

export const researchService = {
  // 연구 자료 수집 요청
  collectResearch: (keywordId) => requestWithRetry(
    (config) => client.post('/research/collect/', { keyword_id: keywordId }, config),
    { maxRetries: 3, retryDelay: 2000, timeout: 60000 } // 60초 타임아웃
  ),
  
  // 연구 자료 수집 상태 확인
  checkResearchStatus: (keywordId) => requestWithRetry(
    (config) => client.get(`/research/sources/status/?keyword_id=${keywordId}`, config),
    { maxRetries: 5, retryDelay: 1000, timeout: 20000 }
  ),
  
  // 특정 키워드의 연구 자료 목록 조회
  getResearchByKeyword: (keywordId) => requestWithRetry(
    (config) => client.get(`/research/sources/?keyword=${keywordId}`, config),
    { maxRetries: 2, retryDelay: 1000, timeout: 30000 }
  ),
  
  // 특정 키워드의 통계 데이터 조회
  getStatisticsByKeyword: (keywordId) => requestWithRetry(
    (config) => client.get(`/research/statistics/?keyword=${keywordId}`, config),
    { maxRetries: 2, retryDelay: 1000, timeout: 30000 }
  ),
  
  // 텍스트에서 통계 데이터 추출
  extractStatistics: (text) => requestWithRetry(
    (config) => client.post('/research/extract-statistics/', { text }, config),
    { maxRetries: 2, retryDelay: 1000, timeout: 30000 }
  ),
  
  // DuckDuckGo 검색
  searchDuckDuckGo: (query, searchType = 'general', maxResults = 5) => requestWithRetry(
    (config) => client.post('/research/sources/duckduckgo/', { 
      query,
      search_type: searchType,
      max_results: maxResults
    }, config),
    { maxRetries: 3, retryDelay: 2000, timeout: 45000 }
  )
};

export default researchService;
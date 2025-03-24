// src/api/contentService.js
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
      
      console.log(`요청 실패, 재시도 중... (${retries}/${maxRetries})`);
      
      // 지수 백오프: 점점 더 길게 기다림
      const delay = retryDelay * Math.pow(2, retries - 1);
      await new Promise(r => setTimeout(r, delay));
    }
  }
};

export const contentService = {
  // 콘텐츠 목록 조회
  getContents: () => requestWithRetry(
    (config) => client.get('/content/', config),
    { maxRetries: 3, retryDelay: 1000, timeout: 30000 }
  ),
  
  // 특정 콘텐츠 조회
  getContent: (id) => requestWithRetry(
    (config) => client.get(`/content/${id}/`, config),
    { maxRetries: 2, retryDelay: 1000, timeout: 20000 }
  ),
  
  // 키워드별 콘텐츠 조회
  getContentsByKeyword: (keywordId) => requestWithRetry(
    (config) => client.get(`/content/?keyword=${keywordId}`, config),
    { maxRetries: 3, retryDelay: 1000, timeout: 30000 }
  ),
  
  // 콘텐츠 생성 (백그라운드 처리 대응)
  createContent: (data) => requestWithRetry(
    (config) => client.post('/content/generate/', data, config),
    { maxRetries: 2, retryDelay: 2000, timeout: 30000 } // 짧은 타임아웃으로 변경
  ),
  
  // 콘텐츠 생성 상태 확인 메서드 추가
  getContentGenerationStatus: (keywordId) => requestWithRetry(
    (config) => client.get(`/content/status/?keyword_id=${keywordId}`, config),
    { maxRetries: 5, retryDelay: 1000, timeout: 20000 }
  ),
  
  // 콘텐츠 최적화 상태 확인 메서드 추가
  getOptimizationStatus: (contentId) => requestWithRetry(
    (config) => client.get(`/content/${contentId}/optimize_status/`, config),
    { maxRetries: 5, retryDelay: 1000, timeout: 20000 }
  ),
  
  // 콘텐츠 상태 확인 (기존 메서드는 유지)
  getContentStatusByKeyword: (keywordId) => requestWithRetry(
    (config) => client.get(`/content/status/${keywordId}/`, config),
    { maxRetries: 5, retryDelay: 1000, timeout: 20000 }
  ),
  
  // 콘텐츠 업데이트
  updateContent: (id, data) => requestWithRetry(
    (config) => client.put(`/content/${id}/`, data, config),
    { maxRetries: 2, retryDelay: 1000, timeout: 60000 }
  ),
  
  // 콘텐츠 삭제
  deleteContent: (id) => requestWithRetry(
    (config) => client.delete(`/content/${id}/`, config),
    { maxRetries: 2, retryDelay: 1000, timeout: 20000 }
  )
};

// 캐싱 관련 함수들
export const contentCacheService = {
  // 캐시에서 콘텐츠 데이터 가져오기
  getCachedContents: () => {
    try {
      const cachedData = localStorage.getItem('cachedContentData');
      return cachedData ? JSON.parse(cachedData) : null;
    } catch (err) {
      console.error('캐시된 콘텐츠 데이터 조회 실패:', err);
      return null;
    }
  },
  
  // 콘텐츠 데이터 캐싱
  cacheContents: (data) => {
    try {
      localStorage.setItem('cachedContentData', JSON.stringify(data));
      return true;
    } catch (err) {
      console.error('콘텐츠 데이터 캐싱 실패:', err);
      return false;
    }
  },
  
  // 캐시 지우기
  clearCache: () => {
    try {
      localStorage.removeItem('cachedContentData');
      return true;
    } catch (err) {
      console.error('캐시 삭제 실패:', err);
      return false;
    }
  }
};

export default contentService;
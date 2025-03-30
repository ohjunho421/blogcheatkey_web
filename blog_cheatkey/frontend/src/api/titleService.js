// src/api/titleService.js
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
      
      console.log(`제목 생성 요청 실패, 재시도 중... (${retries}/${maxRetries})`);
      
      // 지수 백오프: 점점 더 길게 기다림
      const delay = retryDelay * Math.pow(2, retries - 1);
      await new Promise(r => setTimeout(r, delay));
    }
  }
};

export const titleService = {
  // 제목 생성 - 타임아웃 설정 및 재시도 로직 추가
  generateTitles: (data) => requestWithRetry(
    (config) => client.post('/title/generate/', data, config),
    { maxRetries: 2, retryDelay: 2000, timeout: 60000 } // 60초 타임아웃
  ),
  
  // 제목 상태 확인 API 추가
  getStatus: (contentId) => requestWithRetry(
    (config) => client.get(`/title/status/?content_id=${contentId}`, config),
    { maxRetries: 3, retryDelay: 1000, timeout: 20000 }
  ),
  
  // 제목 목록 조회
  getTitles: () => requestWithRetry(
    (config) => client.get('/title/', config),
    { maxRetries: 2, retryDelay: 1000, timeout: 30000 }
  ),
  
  // 특정 제목 조회
  getTitle: (id) => requestWithRetry(
    (config) => client.get(`/title/${id}/`, config),
    { maxRetries: 2, retryDelay: 1000, timeout: 20000 }
  ),
  
  // 제목 저장
  saveTitle: (data) => requestWithRetry(
    (config) => client.post(`/title/${data.id || 0}/select/`, data, config),
    { maxRetries: 2, retryDelay: 1000, timeout: 30000 }
  ),
  
  // 콘텐츠 요약
  summarize: (data) => requestWithRetry(
    (config) => client.post('/title/summarize/', data, config),
    { maxRetries: 2, retryDelay: 2000, timeout: 60000 } // 60초 타임아웃
  )
};
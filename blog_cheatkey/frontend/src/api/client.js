// src/api/client.js
import axios from 'axios';

// API 기본 URL 환경 변수에서 가져오기 (기본값으로 로컬호스트 사용)
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// CSRF 토큰 가져오기 함수
function getCsrfToken() {
  const cookieValue = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
  return cookieValue;
}

// axios 인스턴스 생성
const client = axios.create({
  baseURL: `${API_BASE_URL}/api`, // 환경 변수 사용
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // 쿠키를 포함한 요청 활성화
  timeout: 30000, // 30초 타임아웃 설정
});

// 요청 인터셉터 - 인증 토큰 및 CSRF 토큰 추가
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    
    // 개발 환경에서만 로깅
    if (process.env.NODE_ENV === 'development') {
      console.log('API 요청 URL:', config.url);
      console.log('토큰 존재 여부:', token ? '있음' : '없음');
    }
    
    // 인증 토큰 추가
    if (token) {
      // 토큰 앞에 'Token '을 추가하여 Django REST Framework 형식에 맞춤
      config.headers.Authorization = token.startsWith('Token ') 
        ? token 
        : `Token ${token}`;
      
      if (process.env.NODE_ENV === 'development') {
        console.log('설정된 Authorization 헤더:', config.headers.Authorization);
      }
    }
    
    // CSRF 토큰 추가 (POST, PUT, DELETE, PATCH 요청에만)
    if (['post', 'put', 'delete', 'patch'].includes(config.method?.toLowerCase())) {
      const csrfToken = getCsrfToken();
      if (csrfToken) {
        config.headers['X-CSRFToken'] = csrfToken;
      }
    }
    
    return config;
  },
  (error) => {
    console.error('API 요청 인터셉터 오류:', error);
    return Promise.reject(error);
  }
);

// 응답 인터셉터 - 에러 처리 및 로깅
client.interceptors.response.use(
  (response) => {
    // 개발 환경에서만 성공 응답 로깅 (선택 사항)
    if (process.env.NODE_ENV === 'development') {
      console.log('API 응답 성공:', {
        url: response.config.url,
        status: response.status,
        statusText: response.statusText
      });
    }
    return response;
  },
  (error) => {
    // 상세 에러 로깅
    if (error.response) {
      // 서버가 응답을 반환한 경우
      console.error('API 오류 응답:', {
        url: error.config.url,
        status: error.response.status,
        statusText: error.response.statusText,
        data: error.response.data
      });
    } else if (error.request) {
      // 요청은 보냈지만 응답을 받지 못한 경우
      console.error('API 요청 후 응답 없음:', error.request);
    } else {
      // 요청 설정 중 오류가 발생한 경우
      console.error('API 요청 설정 중 오류:', error.message);
    }

    // 401 에러 (인증 실패) 처리 - 자동 로그아웃
    if (error.response && error.response.status === 401) {
      // 이미 로그인 페이지가 아닌 경우에만 리디렉션
      if (!window.location.pathname.includes('/login')) {
        localStorage.removeItem('token');
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);

export default client;
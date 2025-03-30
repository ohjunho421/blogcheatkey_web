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

// 응답 인터셉터 수정 - 자동 새로고침 제거
client.interceptors.response.use(
  response => response,
  error => {
    // 네트워크 오류 또는 타임아웃 발생 시 로그만 남기고, 자동 새로고침은 하지 않음
    if (!error.response || error.code === 'ECONNABORTED') {
      console.log('네트워크 오류가 발생했습니다.');
      
      // 개발 환경에서만 상세 로그 출력
      if (process.env.NODE_ENV === 'development') {
        console.error('오류 상세 정보:', error);
      }
    }
    
    // 오류를 그대로 전파하여 각 컴포넌트에서 처리할 수 있도록 함
    return Promise.reject(error);
  }
);


export default client;
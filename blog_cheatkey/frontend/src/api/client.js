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

// src/api/client.js 파일에 인터셉터 추가
client.interceptors.response.use(
  response => response,
  error => {
    // 네트워크 오류 또는 타임아웃 확인
    if (!error.response || error.code === 'ECONNABORTED') {
      console.log('네트워크 오류가 발생했습니다. 페이지를 새로고침합니다.');
      
      // 사용자에게 알림 표시 (선택 사항)
      const notification = document.createElement('div');
      notification.textContent = '연결이 끊겼습니다. 3초 후 페이지가 새로고침됩니다...';
      notification.style = 'position:fixed; top:0; left:0; right:0; background:red; color:white; padding:10px; text-align:center; z-index:9999;';
      document.body.appendChild(notification);
      
      // 3초 후 새로고침
      setTimeout(() => {
        window.location.reload();
      }, 3000);
    }
    
    return Promise.reject(error);
  }
);

export default client;
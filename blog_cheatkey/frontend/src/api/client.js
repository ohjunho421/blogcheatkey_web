// src/api/client.js
import axios from 'axios';

// 전체 URL을 직접 사용하도록 수정
const client = axios.create({
  baseURL: 'http://localhost:8000/api', // 백엔드 서버 URL + API 경로
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // 쿠키를 포함한 요청 활성화
});

// 요청 인터셉터 - 인증 토큰 추가
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    console.log('API 요청 URL:', config.url);
    console.log('토큰 존재 여부:', token ? '있음' : '없음');
    
    if (token) {
      // 토큰 앞에 'Token '을 추가하여 Django REST Framework 형식에 맞춤
      config.headers.Authorization = token.startsWith('Token ') 
        ? token 
        : `Token ${token}`;
      console.log('설정된 Authorization 헤더:', config.headers.Authorization);
    }
    
    return config;
  },
  (error) => Promise.reject(error)
);

// 응답 인터셉터 - 에러 처리
client.interceptors.response.use(
  (response) => response,
  (error) => {
    // 401 에러 (인증 실패) 처리
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default client;
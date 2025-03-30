// src/api/authService.js
import client from './client';

const API_BASE_URL = 'http://localhost:8000/api';

export const authService = {
  login: async (credentials) => {
    // client 사용하도록 수정
    const response = await client.post('/auth/login/', credentials);
    
    if (response.data.token) {
      localStorage.setItem('token', response.data.token);
      // 토큰 저장 후 axios 헤더 즉시 업데이트
      client.defaults.headers.common['Authorization'] = `Token ${response.data.token}`;
      console.log('토큰 저장됨:', response.data.token);
    }
    return response.data;
  },
  
  register: async (userData) => {
    return await client.post('/auth/register/', userData);
  },
  
  logout: async () => {
    await client.post('/auth/logout/');
    localStorage.removeItem('token');
    // 헤더에서도 토큰 제거
    delete client.defaults.headers.common['Authorization'];
  },
  
  getProfile: async () => {
    return await client.get('/auth/profile/');
  },
  
  // 소셜 로그인 토큰 요청 함수
  socialLoginToken: async (data) => {
    const response = await client.post('/auth/social/token/', data);
    if (response.data.token) {
      localStorage.setItem('token', response.data.token);
      // 토큰 저장 후 axios 헤더 즉시 업데이트
      client.defaults.headers.common['Authorization'] = `Token ${response.data.token}`;
    }
    return response;
  },
  
  // 소셜 로그인 URL 얻기
  getSocialLoginUrl: (provider) => {
    return `${API_BASE_URL}/auth/social/${provider}/login/`;
  }
};
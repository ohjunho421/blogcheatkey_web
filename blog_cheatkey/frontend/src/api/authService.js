// src/api/authService.js
import client from './client';

export const authService = {
  login: async (credentials) => {
    const response = await client.post('/api/auth/login/', credentials);
    if (response.data.token) {
      localStorage.setItem('token', response.data.token);
    }
    return response.data;
  },
  
  register: async (userData) => {
    return await client.post('/api/auth/register/', userData);
  },
  
  logout: async () => {
    await client.post('/api/auth/logout/');
    localStorage.removeItem('token');
  },
  
  getProfile: async () => {
    return await client.get('/api/auth/profile/');
  },
  
  // 소셜 로그인 토큰 요청 함수 추가
  socialLoginToken: async (data) => {
    const response = await client.post('/api/auth/social/token/', data);
    if (response.data.token) {
      localStorage.setItem('token', response.data.token);
    }
    return response;
  },
  
  // 소셜 로그인 URL 얻기 (필요시 사용)
  getSocialLoginUrl: (provider) => {
    return `/api/auth/social/${provider}/login/`;
  }
};
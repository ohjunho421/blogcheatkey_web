// src/api/authService.js
import axios from 'axios';
import client from './client';

const API_BASE_URL = 'http://localhost:8000/api';

export const authService = {
  login: async (credentials) => {
    // 전체 URL 직접 지정
    const response = await axios.post(`${API_BASE_URL}/auth/login/`, credentials, {
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    if (response.data.token) {
      localStorage.setItem('token', response.data.token);
    }
    return response.data;
  },
  
  register: async (userData) => {
    return await client.post('/auth/register/', userData);
  },
  
  logout: async () => {
    await client.post('/auth/logout/');
    localStorage.removeItem('token');
  },
  
  getProfile: async () => {
    return await client.get('/auth/profile/');
  },
  
  // 소셜 로그인 토큰 요청 함수
  socialLoginToken: async (data) => {
    const response = await client.post('/auth/social/token/', data);
    if (response.data.token) {
      localStorage.setItem('token', response.data.token);
    }
    return response;
  },
  
  // 소셜 로그인 URL 얻기
  getSocialLoginUrl: (provider) => {
    return `${API_BASE_URL}/auth/social/${provider}/login/`;
  }
};
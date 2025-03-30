import React, { createContext, useState, useEffect, useContext } from 'react';
import { authService } from '../api/authService';
import client from '../api/client'; 

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // 페이지 로드시 사용자 정보 가져오기
    const loadUser = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          const response = await authService.getProfile();
          setUser(response.data);
        } catch (err) {
          console.error('Failed to load user:', err);
          localStorage.removeItem('token');
        }
      }
      setLoading(false);
    };

    loadUser();
  }, []);

  const login = async (credentials) => {
    try {
      setLoading(true);
      const data = await authService.login(credentials);
      
      // 사용자 정보 가져오기
      const userResponse = await authService.getProfile();
      setUser(userResponse.data);
      setError(null);
      return data;
    } catch (err) {
      setError(err.response?.data || { detail: '로그인에 실패했습니다.' });
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      await authService.logout();
      setUser(null);
      setError(null);
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  // 회원가입 기능 추가
  const register = async (userData) => {
    try {
      setLoading(true);
      const response = await authService.register(userData);
      setError(null);
      return response;
    } catch (err) {
      setError(err.response?.data || { detail: '회원가입에 실패했습니다.' });
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // 소셜 로그인 시작 함수 추가
  const socialLogin = (provider) => {
    const baseUrl = 'http://localhost:8000'; // 개발 환경 주소
    window.location.href = `${baseUrl}/api/auth/social/${provider}/login/`;
  };

  // 소셜 로그인 콜백 처리 함수 추가
  const handleSocialLoginCallback = async (code, provider) => {
    try {
      setLoading(true);
      const response = await authService.socialLoginToken({
        code,
        provider
      });
      
      localStorage.setItem('token', response.data.token);
      
      // 사용자 정보 설정
      setUser(response.data.user);
      setError(null);
      return true;
    } catch (err) {
      console.error('Social login failed:', err);
      setError({ detail: '소셜 로그인에 실패했습니다.' });
      return false;
    } finally {
      setLoading(false);
    }
  };

  const value = {
    user,
    loading,
    error,
    login,
    logout,
    register,
    socialLogin, // 소셜 로그인 함수 추가
    handleSocialLoginCallback, // 소셜 로그인 콜백 처리 함수 추가
    isAuthenticated: !!user
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
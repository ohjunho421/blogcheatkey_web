// components/SocialLoginCallback.js
import React, { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const SocialLoginCallback = () => {
  const { handleSocialLoginCallback } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  useEffect(() => {
    const handleCallback = async () => {
      // URL에서 code와 provider 파라미터 추출
      const params = new URLSearchParams(location.search);
      const code = params.get('code');
      const provider = params.get('provider');
      
      if (code && provider) {
        const success = await handleSocialLoginCallback(code, provider);
        if (success) {
          // 로그인 성공 시 대시보드로 이동
          navigate('/dashboard');
        } else {
          // 실패 시 로그인 페이지로 이동
          navigate('/login');
        }
      } else {
        navigate('/login');
      }
    };
    
    handleCallback();
  }, [location, handleSocialLoginCallback, navigate]);
  
  return <div className="text-center my-5">소셜 로그인 처리 중...</div>;
};

export default SocialLoginCallback;
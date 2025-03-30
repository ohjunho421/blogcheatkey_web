// src/routes/index.js
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import ContentDetail from '../pages/ContentDetail';

// 레이아웃 컴포넌트
import Layout from '../components/layout/Layout';

// 페이지 컴포넌트
import Login from '../pages/Login';
import Register from '../pages/Register';
import Dashboard from '../pages/Dashboard';
import NotFound from '../pages/NotFound';
import KeywordManagement from '../pages/KeywordManagement';
import ContentManagement from '../pages/ContentManagement';
import TitleGenerator from '../pages/TitleGenerator';
import SocialLoginCallback from '../components/layout/SocialLoginCallback';

// 인증이 필요한 라우트 래퍼
const PrivateRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return <div>Loading...</div>;
  }
  
  
  
  return isAuthenticated ? children : <Navigate to="/login" />;
};

const AppRouter = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* 공개 라우트 */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        
        {/* 소셜 로그인 콜백 라우트 추가 */}
        <Route path="/auth/callback" element={<SocialLoginCallback />} />
        
        {/* 인증이 필요한 라우트 */}
        <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
          <Route index element={<Dashboard />} />
          <Route path="keywords" element={<KeywordManagement />} />
          <Route path="contents" element={<ContentManagement />} />
          <Route path="content/:id" element={<ContentDetail />} />
          <Route path="titles" element={<TitleGenerator />} />
        </Route>
        
        {/* 404 페이지 */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
};

export default AppRouter;
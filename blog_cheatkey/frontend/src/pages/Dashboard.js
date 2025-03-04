// src/pages/Dashboard.js
import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Dashboard = () => {
  const { user } = useAuth();

  return (
    <div className="p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-4">환영합니다, {user?.username}님!</h1>
        <p className="text-gray-600">AI 블로그 치트키로 블로그 콘텐츠를 쉽게 관리하세요.</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">빠른 시작하기</h2>
          <div className="space-y-4">
            <Link to="/keywords/create" className="block p-4 bg-blue-50 hover:bg-blue-100 rounded-lg">
              <h3 className="font-medium text-blue-600">새 키워드 분석하기</h3>
              <p className="text-sm text-gray-600 mt-1">키워드를 입력하여 SEO 분석을 시작하세요.</p>
            </Link>
            
            <div className="block p-4 bg-gray-50 rounded-lg">
              <h3 className="font-medium text-gray-600">최근 작업 없음</h3>
              <p className="text-sm text-gray-500 mt-1">키워드를 분석하여 콘텐츠 작성을 시작하세요.</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">기능 살펴보기</h2>
          <ul className="space-y-3">
            <li className="flex items-start">
              <div className="flex-shrink-0 h-5 w-5 text-blue-500">✓</div>
              <p className="ml-3 text-gray-600">SEO에 최적화된 블로그 콘텐츠 생성</p>
            </li>
            <li className="flex items-start">
              <div className="flex-shrink-0 h-5 w-5 text-blue-500">✓</div>
              <p className="ml-3 text-gray-600">클릭을 유도하는 매력적인 제목 생성</p>
            </li>
            <li className="flex items-start">
              <div className="flex-shrink-0 h-5 w-5 text-blue-500">✓</div>
              <p className="ml-3 text-gray-600">모바일 최적화된 콘텐츠 포맷</p>
            </li>
            <li className="flex items-start">
              <div className="flex-shrink-0 h-5 w-5 text-blue-500">✓</div>
              <p className="ml-3 text-gray-600">관련 통계 및 연구 자료 자동 수집</p>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
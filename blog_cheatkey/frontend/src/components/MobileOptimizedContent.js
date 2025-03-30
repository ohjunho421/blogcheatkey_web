import React, { useState, useEffect } from 'react';
import MobileFormatter from '../utils/MobileFormatter';

const MobileOptimizedContent = ({ content }) => {
  const [viewMode, setViewMode] = useState('original'); // 'original', 'mobile', 'split'
  const [formattedContent, setFormattedContent] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  
  useEffect(() => {
    if (!content) return;
    
    // 원본 콘텐츠 저장
    setOriginalContent(content);
    
    // 모바일 최적화 콘텐츠 생성
    const mobileContent = MobileFormatter.formatHtmlForMobile(content);
    setFormattedContent(mobileContent);
    
  }, [content]);
  
  return (
    <div className="content-container">
      {/* 뷰 모드 선택 버튼 그룹 */}
      <div className="flex justify-end mb-3 gap-2">
        <button 
          onClick={() => setViewMode('original')}
          className={`px-3 py-1 text-sm rounded ${
            viewMode === 'original' 
              ? 'bg-blue-500 text-white' 
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          원본 보기
        </button>
        <button 
          onClick={() => setViewMode('mobile')}
          className={`px-3 py-1 text-sm rounded ${
            viewMode === 'mobile' 
              ? 'bg-blue-500 text-white' 
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          모바일 최적화
        </button>
        <button 
          onClick={() => setViewMode('split')}
          className={`px-3 py-1 text-sm rounded ${
            viewMode === 'split' 
              ? 'bg-blue-500 text-white' 
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          비교 보기
        </button>
      </div>
      
      {/* 콘텐츠 표시 영역 */}
      {viewMode === 'original' && (
        <div className="prose max-w-none">
          <div dangerouslySetInnerHTML={{ __html: originalContent }} />
        </div>
      )}
      
      {viewMode === 'mobile' && (
        <div className="prose max-w-none">
          {/* 모바일 화면 시뮬레이션 */}
          <div className="mx-auto border border-gray-300 rounded-lg shadow-md p-4" style={{ maxWidth: '375px' }}>
            <div dangerouslySetInnerHTML={{ __html: formattedContent }} />
          </div>
        </div>
      )}
      
      {viewMode === 'split' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="prose max-w-none">
            <h3 className="text-lg font-medium mb-2">원본</h3>
            <div className="border p-4 rounded">
              <div dangerouslySetInnerHTML={{ __html: originalContent }} />
            </div>
          </div>
          
          <div className="prose max-w-none">
            <h3 className="text-lg font-medium mb-2">모바일 최적화</h3>
            <div className="border p-4 rounded">
              <div dangerouslySetInnerHTML={{ __html: formattedContent }} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MobileOptimizedContent;
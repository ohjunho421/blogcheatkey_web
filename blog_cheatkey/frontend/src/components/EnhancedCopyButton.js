import React, { useState, useEffect } from 'react';
import MobileFormatter from '../utils/MobileFormatter';

const EnhancedCopyButton = ({ originalText }) => {
  const [copied, setCopied] = useState(false);
  const [copyMode, setCopyMode] = useState('original'); // 'original' 또는 'mobile'
  const [mobileText, setMobileText] = useState('');
  
  useEffect(() => {
    if (originalText) {
      // 모바일 최적화된 텍스트 생성 (HTML 태그 없이 순수 텍스트로)
      const plainText = originalText.replace(/<br\s*\/?>/gi, '\n');
      const formatted = MobileFormatter.formatForMobile(plainText);
      setMobileText(formatted);
    }
  }, [originalText]);
  
  const handleCopy = async () => {
    try {
      // 선택된 모드에 따라 복사할 텍스트 결정
      const textToCopy = copyMode === 'original' ? originalText : mobileText;
      
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      
      // 3초 후 복사 상태 초기화
      setTimeout(() => {
        setCopied(false);
      }, 3000);
    } catch (err) {
      console.error('클립보드 복사 실패:', err);
    }
  };
  
  return (
    <div className="flex flex-col space-y-2">
      <div className="flex items-center space-x-4">
        <span className="text-sm font-medium">복사 형식:</span>
        <div className="flex rounded-md shadow-sm" role="group">
          <button
            type="button"
            onClick={() => setCopyMode('original')}
            className={`px-4 py-2 text-sm font-medium rounded-l-lg ${
              copyMode === 'original'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100'
            } border border-gray-300`}
          >
            원본
          </button>
          <button
            type="button"
            onClick={() => setCopyMode('mobile')}
            className={`px-4 py-2 text-sm font-medium rounded-r-lg ${
              copyMode === 'mobile'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100'
            } border border-gray-300 border-l-0`}
          >
            모바일 최적화
          </button>
        </div>
      </div>
      
      <button
        onClick={handleCopy}
        className={`flex items-center justify-center gap-2 py-2 px-4 rounded transition-all ${
          copied 
            ? 'bg-green-500 text-white' 
            : 'bg-blue-500 hover:bg-blue-600 text-white'
        }`}
      >
        {copied ? '✓ 복사 완료!' : '📋 텍스트 복사하기'}
      </button>
      
      {copyMode === 'mobile' && (
        <div className="text-xs text-gray-500 mt-1">
          * 모바일 최적화 형식으로 복사됩니다. 줄바꿈이 최적화된 상태로 붙여넣기 됩니다.
        </div>
      )}
    </div>
  );
};

export default EnhancedCopyButton;
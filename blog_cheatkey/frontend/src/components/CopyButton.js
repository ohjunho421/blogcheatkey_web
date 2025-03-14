import React, { useState } from 'react';
import { ClipboardCopy } from 'lucide-react';

// props로 textToCopy를 받도록 수정
const CopyButtonComponent = ({ textToCopy }) => {
  const [copied, setCopied] = useState(false);
  
  // 하드코딩된 textToCopy 제거 (props로 받음)
  
  const handleCopy = async () => {
    try {
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
    <div className="w-full mx-auto bg-white rounded-lg">
      {/* 상세보기 내용 div 제거 - 이미 ContentDetail.js에서 표시됨 */}
      
      {/* 복사 버튼만 남김 */}
      <button
        onClick={handleCopy}
        className={`flex items-center justify-center gap-2 py-2 px-4 rounded transition-all ${
          copied 
            ? 'bg-green-500 text-white' 
            : 'bg-blue-500 hover:bg-blue-600 text-white'
        }`}
      >
        <ClipboardCopy size={18} />
        {copied ? '복사 완료!' : '텍스트 복사하기'}
      </button>
    </div>
  );
};

export default CopyButtonComponent;
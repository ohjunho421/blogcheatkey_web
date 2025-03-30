import React, { useState, useEffect } from 'react';

const VideoPromptGenerator = ({ content }) => {
  const [prompt, setPrompt] = useState('');
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);

  // 콘텐츠 내용을 요약하여 프롬프트 생성 함수
  const generatePrompt = (contentText) => {
    if (!contentText) return '';
    
    // HTML 태그 제거
    const plainText = contentText.replace(/<[^>]*>/g, '');
    
    // 기본 문장 구조 생성
    const title = contentText.substring(0, 50) + '...';
    const keyPoints = extractKeyPoints(plainText);
    
    return `# ${title}\n\n## 주요 내용:\n${keyPoints.join('\n')}\n\n## 영상 스타일:\n- 설명형 콘텐츠\n- 화면에 주요 키워드 강조\n- 자막 포함\n- 배경 음악: 가볍고 집중할 수 있는 BGM`;
  };
  
  // 주요 포인트 추출 (간단한 구현, 실제로는 더 복잡한 알고리즘 필요)
  const extractKeyPoints = (text) => {
    // 텍스트를 문장으로 나누기
    const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 20);
    
    // 최대 5개 문장 선택
    const selectedSentences = sentences.slice(0, 5).map(s => `- ${s.trim()}`);
    
    return selectedSentences.length ? selectedSentences : ['- 주요 내용을 요약하여 이곳에 넣으세요'];
  };

  // 콘텐츠가 변경될 때 프롬프트 업데이트
  useEffect(() => {
    if (content) {
      setLoading(true);
      // 실제 환경에서는 비동기로 처리할 수 있음
      setTimeout(() => {
        setPrompt(generatePrompt(content));
        setLoading(false);
      }, 500);
    }
  }, [content]);

  // 클립보드 복사 함수
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(prompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('클립보드 복사 실패:', err);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-4 mt-6">
      <h3 className="text-lg font-medium mb-3">영상 생성 프롬프트</h3>
      
      {loading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      ) : (
        <>
          <div className="bg-gray-50 p-4 rounded border mb-3">
            <pre className="whitespace-pre-wrap text-sm">{prompt}</pre>
          </div>
          
          <div className="flex justify-between">
            <button
              onClick={handleCopy}
              className={`flex items-center gap-2 py-2 px-4 rounded transition-all ${
                copied ? 'bg-green-500 text-white' : 'bg-blue-500 hover:bg-blue-600 text-white'
              }`}
            >
              {copied ? '✓ 복사 완료!' : '📋 프롬프트 복사'}
            </button>
            
            <a
              href={`https://vrew.voyagerx.com/ko?prompt=${encodeURIComponent(prompt)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="py-2 px-4 bg-purple-600 text-white rounded hover:bg-purple-700"
            >
              Vrew에서 열기
            </a>
          </div>
        </>
      )}
    </div>
  );
};

// 예시 콘텐츠로 컴포넌트 렌더링 (실제로는 ContentDetail에서 props로 전달)
const ExampleApp = () => {
  const exampleContent = "이곳에 상세보기의 내용이 표시됩니다. 실제 구현 시에는 content.content 값을 전달해주세요.";
  
  return <VideoPromptGenerator content={exampleContent} />;
};

export default ExampleApp;
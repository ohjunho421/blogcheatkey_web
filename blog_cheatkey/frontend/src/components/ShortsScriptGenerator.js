import React, { useState, useEffect } from 'react';

const ShortsScriptGenerator = ({ content }) => {
  const [script, setScript] = useState('');
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);

  // HTML 태그 제거 함수
  const stripHtml = (html) => {
    const tmp = document.createElement('DIV');
    tmp.innerHTML = html;
    return tmp.textContent || tmp.innerText || '';
  };

  // 온전한 문장으로 만들기 (마침표 있으면 유지, 없으면 추가)
  const completeEndingSentence = (sentence) => {
    const trimmed = sentence.trim();
    if (trimmed.length === 0) return '';
    
    const lastChar = trimmed[trimmed.length - 1];
    if (['.', '!', '?'].includes(lastChar)) {
      return trimmed;
    }
    
    // 문장이 질문처럼 보이면 물음표, 아니면 마침표 추가
    if (trimmed.includes('가요') || trimmed.includes('까요') || 
        trimmed.includes('나요') || trimmed.includes('ㄴ가요')) {
      return trimmed + '?';
    }
    return trimmed + '.';
  };

  // 콘텐츠 내용을 짧은 스크립트로 요약하는 함수
  const generateScript = (contentText) => {
    if (!contentText) return '';
    
    // HTML 태그 제거
    const plainText = stripHtml(contentText);
    
    // 문장 분리
    const sentences = plainText
      .replace(/\s+/g, ' ')
      .split(/(?<=[.!?])\s+/)
      .filter(s => s.trim().length > 5); // 더 짧은 문장도 포함
    
    // 제목/주제 추출
    let topic = '';
    if (sentences.length > 0) {
      const firstSentence = sentences[0].trim();
      
      // 특정 패턴 감지 (예: "안녕하세요, 다올모터스입니다")
      if (firstSentence.includes('안녕하세요') && firstSentence.includes('입니다')) {
        // "안녕하세요, XXX입니다" 형식에서 XXX 추출
        const match = firstSentence.match(/안녕하세요[,\s]*(.*?)입니다/);
        if (match && match[1]) {
          topic = match[1].trim();
        } else {
          // 매칭 실패 시 일반적인 방법으로 추출
          topic = firstSentence.split(',')[0].split('입니다')[0];
        }
      } else {
        // 일반적인 제목/주제 추출
        topic = firstSentence.split('.')[0].substring(0, 20);
      }
    }
    
    if (!topic || topic.length < 2) {
      topic = "오늘의 주제";
    }
    
    // 스크립트 생성
    let shortsScript = '';
    
    // 인트로
    shortsScript += `안녕하세요! 오늘은 ${topic}에 관한 중요한 정보를 알려드릴게요.\n\n`;
    
    // 본문 내용 구성 - 완전한 문장으로
    const contentSentences = sentences.slice(1).filter(s => s.length > 0);
    
    // 소개글 다음부터 핵심 문장 4개 정도 선택 (너무 길지 않은 문장)
    const selectedSentences = contentSentences
      .filter(s => s.length < 100 && s.length > 10)
      .slice(0, 4);
    
    // 선택된 문장이 없으면 원본에서 적당히 추출
    if (selectedSentences.length === 0 && contentSentences.length > 0) {
      for (let i = 0; i < Math.min(4, contentSentences.length); i++) {
        const sent = contentSentences[i];
        // 문장이 너무 길면 앞부분만 사용하고 적절히 마무리
        if (sent.length > 100) {
          const words = sent.split(' ').slice(0, 15);
          selectedSentences.push(words.join(' ') + '...');
        } else {
          selectedSentences.push(sent);
        }
      }
    }
    
    // 연결어와 함께 문장 추가
    const connectors = ['먼저', '또한', '그리고', '마지막으로'];
    
    selectedSentences.forEach((sentence, index) => {
      const connector = index < connectors.length ? connectors[index] : '그리고';
      const completeSentence = completeEndingSentence(sentence);
      shortsScript += `${connector}, ${completeSentence}\n\n`;
    });
    
    // 아웃트로
    shortsScript += '자세한 내용이 궁금하시다면 전체 게시글을 확인해주세요! 좋아요와 구독으로 더 많은 정보를 받아보세요.';
    
    return shortsScript;
  };

  // 콘텐츠가 변경될 때 스크립트 업데이트
  useEffect(() => {
    if (content) {
      setLoading(true);
      setTimeout(() => {
        setScript(generateScript(content));
        setLoading(false);
      }, 500);
    }
  }, [content]);

  // 클립보드 복사 함수
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(script);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('클립보드 복사 실패:', err);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-4 mt-6">
      <h3 className="text-lg font-medium mb-3">쇼츠/릴스용 TTS 스크립트</h3>
      
      {loading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      ) : (
        <>
          <div className="bg-gray-50 p-4 rounded border mb-3">
            <pre className="whitespace-pre-wrap text-sm">{script}</pre>
          </div>
          
          <div className="flex justify-between">
            <button
              onClick={handleCopy}
              className={`flex items-center gap-2 py-2 px-4 rounded transition-all ${
                copied ? 'bg-green-500 text-white' : 'bg-blue-500 hover:bg-blue-600 text-white'
              }`}
            >
              {copied ? '✓ 복사 완료!' : '📋 스크립트 복사'}
            </button>
            
            <a
              href={`https://vrew.voyagerx.com/ko?text=${encodeURIComponent(script)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="py-2 px-4 bg-purple-600 text-white rounded hover:bg-purple-700"
            >
              Vrew에서 TTS 생성
            </a>
          </div>
        </>
      )}
    </div>
  );
};

export default ShortsScriptGenerator;
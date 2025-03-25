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

  // 주요 키워드 추출 함수
  const extractKeywords = (text, count = 3) => {
    // 간단한 키워드 추출 로직 (빈도수 기반)
    const words = text.split(/\s+/).filter(word => word.length > 1);
    const wordCounts = {};
    
    words.forEach(word => {
      // 한글 단어만 추출 (특수문자, 숫자 제외)
      const cleanWord = word.replace(/[^\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]/g, '');
      if (cleanWord.length > 1) {
        wordCounts[cleanWord] = (wordCounts[cleanWord] || 0) + 1;
      }
    });
    
    // 빈도수 기준 상위 키워드 추출
    return Object.entries(wordCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, count)
      .map(entry => entry[0]);
  };

  // 흥미로운 질문 생성 함수
  const generateHookQuestion = (topic, keywords) => {
    const questions = [
      `${topic}에서 가장 중요한 점이 뭔지 아시나요?`,
      `${topic}에 대해 이것만큼은 꼭 알아야 합니다!`,
      `${topic}, 제대로 이해하고 계셨나요?`,
      `많은 분들이 ${topic}에 대해 이것을 놓치고 있어요!`,
      `${keywords[0]}와 ${keywords[1] || keywords[0]}의 관계, 알고 계셨나요?`,
      `${topic}에 대한 숨겨진 진실을 알려드립니다!`,
      `${topic}에 관한 놀라운 사실 TOP 3!`,
      `${topic}, 이렇게 하면 실패합니다!`,
      `${topic}의 성공 비결은 따로 있었습니다!`,
      `당신이 ${topic}에 대해 몰랐던 충격적인 사실!`
    ];
    
    // 랜덤하게 질문 선택
    return questions[Math.floor(Math.random() * questions.length)];
  };

  // 핵심 포인트 추출 함수
  const extractKeyPoints = (sentences, count = 3) => {
    // 간단한 중요도 계산 (문장 길이, 키워드 포함 여부 등 고려)
    const keyPoints = [];
    const midIndex = Math.floor(sentences.length / 2);
    
    // 첫 부분, 중간 부분, 마지막 부분에서 골고루 선택
    if (sentences.length > 0) {
      const firstSection = sentences.slice(0, midIndex);
      const lastSection = sentences.slice(midIndex);
      
      // 첫 섹션에서 1개
      if (firstSection.length > 0) {
        const selected = firstSection.find(s => s.length > 15 && s.length < 100) || firstSection[0];
        keyPoints.push(selected);
      }
      
      // 마지막 섹션에서 나머지
      let remainingCount = count - keyPoints.length;
      for (let i = 0; i < remainingCount && i < lastSection.length; i++) {
        const goodSentence = lastSection.find(s => 
          s.length > 15 && s.length < 100 && !keyPoints.includes(s)
        );
        if (goodSentence) {
          keyPoints.push(goodSentence);
        } else if (lastSection[i] && !keyPoints.includes(lastSection[i])) {
          keyPoints.push(lastSection[i]);
        }
      }
    }
    
    return keyPoints;
  };

  // 유입 유도 문구 생성
  const generateCTA = (topic) => {
    const ctas = [
      `더 자세한 내용이 궁금하다면? 지금 바로 프로필 링크에서 전체 게시글을 확인하세요!`,
      `이건 빙산의 일각일 뿐! ${topic}에 관한 모든 지식은 프로필의 블로그에서 확인하세요.`,
      `${topic}의 모든 비밀, 놓치지 마세요! 프로필 링크에서 확인하세요.`,
      `${topic}에 관한 더 많은 팁이 궁금하다면? 프로필 링크를 클릭하세요.`,
      `지금 바로 프로필 링크를 눌러 ${topic}의 모든 것을 알아보세요!`,
      `좋아요와 팔로우로 ${topic}에 관한 더 많은 꿀팁을 받아보세요!`,
      `이 정보가 도움이 되셨나요? 프로필에서 더 많은 유용한 정보를 확인하세요!`
    ];
    
    return ctas[Math.floor(Math.random() * ctas.length)];
  };

  // 콘텐츠 내용을 쇼츠 스크립트로 변환하는 함수 (유입 유도 최적화)
  const generateScript = (contentText) => {
    if (!contentText) return '';
    
    // HTML 태그 제거
    const plainText = stripHtml(contentText);
    
    // 문장 분리
    const sentences = plainText
      .replace(/\s+/g, ' ')
      .split(/(?<=[.!?])\s+/)
      .map(s => s.trim())
      .filter(s => s.length > 5);
    
    // 주제 추출
    let topic = '';
    if (sentences.length > 0) {
      // 첫 문장이 제목일 가능성이 높음
      const firstSentence = sentences[0];
      
      if (firstSentence.includes('안녕하세요') && firstSentence.includes('입니다')) {
        const match = firstSentence.match(/안녕하세요[,\s]*(.*?)입니다/);
        if (match && match[1]) {
          topic = match[1].trim();
        } else {
          topic = firstSentence.split(',')[0].split('입니다')[0];
        }
      } else {
        // 첫 문장에서 주요 단어 추출
        const words = firstSentence.split(' ').filter(w => w.length > 1);
        if (words.length > 2) {
          topic = words.slice(0, 3).join(' ');
        } else {
          topic = firstSentence.split('.')[0];
        }
      }
    }
    
    if (!topic || topic.length < 2) {
      topic = "오늘의 주제";
    }
    
    // 주요 키워드 추출
    const keywords = extractKeywords(plainText);
    
    // 핵심 포인트 추출 (흥미로운 내용 위주)
    const keyPoints = extractKeyPoints(sentences.slice(1), 3);
    
    // 스크립트 생성
    let shortsScript = '';
    
    // 1. 시선을 끄는 인트로 (질문이나 충격적인 문장)
    const hookQuestion = generateHookQuestion(topic, keywords);
    shortsScript += `${hookQuestion}\n\n`;
    
    // 2. 짧은 소개
    shortsScript += `안녕하세요! 오늘은 ${topic}에 관한 정말 중요한 정보를 공유해드릴게요.\n\n`;
    
    // 3. 핵심 포인트 (호기심 자극, 일부만 공개)
    const pointPrefixes = ['첫째,', '둘째,', '셋째,', '그리고,'];
    
    keyPoints.forEach((point, index) => {
      const prefix = index < pointPrefixes.length ? pointPrefixes[index] : '또한,';
      
      // 마지막 포인트는 클리프행어처럼 일부러 미완성으로 남김
      if (index === keyPoints.length - 1 && point.length > 30) {
        const words = point.split(' ');
        const partialPoint = words.slice(0, Math.floor(words.length * 0.7)).join(' ') + '...';
        shortsScript += `${prefix} ${partialPoint}\n\n`;
      } else {
        shortsScript += `${prefix} ${completeEndingSentence(point)}\n\n`;
      }
    });
    
    // 4. 강력한 유입 유도 (CTA)
    const cta = generateCTA(topic);
    shortsScript += cta;
    
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
      <h3 className="text-lg font-medium mb-3">쇼츠/릴스용 TTS 스크립트 (유입 최적화)</h3>
      
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
          
          <div className="mt-4 text-sm text-gray-600">
            <p className="font-medium">💡 TIP: 효과적인 쇼츠 스크립트 특징</p>
            <ul className="list-disc pl-5 mt-1">
              <li>호기심을 자극하는 질문으로 시작</li>
              <li>일부 정보만 공개하여 더 알고 싶게 함</li>
              <li>마지막은 항상 프로필/블로그 방문 유도</li>
              <li>핵심 정보만 담아 15-30초 내외로 제작</li>
            </ul>
          </div>
        </>
      )}
    </div>
  );
};

export default ShortsScriptGenerator;
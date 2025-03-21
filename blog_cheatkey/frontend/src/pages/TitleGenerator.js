// src/pages/TitleGenerator.js
import React, { useState, useEffect } from 'react';
import { titleService } from '../api/titleService';
import { keywordService } from '../api/keywordService';
import { contentService } from '../api/contentService';

const TitleGenerator = () => {
  const [keywords, setKeywords] = useState([]);
  const [selectedKeyword, setSelectedKeyword] = useState('');
  const [titleCount, setTitleCount] = useState(5);
  const [titles, setTitles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [savedTitles, setSavedTitles] = useState([]);
  const [success, setSuccess] = useState(null);
  const [generationStatus, setGenerationStatus] = useState(null);
  const [statusCheckInterval, setStatusCheckInterval] = useState(null);
  const [selectedContentId, setSelectedContentId] = useState(null);

  // 키워드 목록 로드
  useEffect(() => {
    const fetchKeywords = async () => {
      try {
        const response = await keywordService.getKeywords();
        console.log('API 응답 (키워드):', response.data);
        
        // 응답이 배열인지 확인하고 처리
        if (Array.isArray(response.data)) {
          setKeywords(response.data);
        } else if (response.data && response.data.results && Array.isArray(response.data.results)) {
          // Django REST Framework의 페이지네이션 응답인 경우
          setKeywords(response.data.results);
        } else {
          // 기타 경우, 빈 배열로 설정
          console.error('예상치 못한 API 응답 형식 (키워드):', response.data);
          setKeywords([]);
        }
      } catch (err) {
        setError('키워드를 불러오는 중 오류가 발생했습니다.');
        console.error('API 오류 (키워드):', err);
      }
    };

    const fetchSavedTitles = async () => {
      try {
        const response = await titleService.getTitles();
        console.log('API 응답 (저장된 제목):', response.data);
        
        if (Array.isArray(response.data)) {
          setSavedTitles(response.data);
        } else if (response.data && response.data.results && Array.isArray(response.data.results)) {
          setSavedTitles(response.data.results);
        } else {
          console.error('예상치 못한 API 응답 형식 (저장된 제목):', response.data);
          setSavedTitles([]);
        }
      } catch (err) {
        console.error('저장된 제목을 불러오는 중 오류 발생:', err);
        setSavedTitles([]);
      }
    };

    fetchKeywords();
    fetchSavedTitles();
    
    // 컴포넌트 언마운트 시 인터벌 정리
    return () => {
      if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
      }
    };
  }, []);

  // 상태 폴링 함수
  const startStatusPolling = (contentId) => {
    // 이전 인터벌 정리
    if (statusCheckInterval) {
      clearInterval(statusCheckInterval);
    }
    
    // 상태 폴링 시작
    const intervalId = setInterval(async () => {
      try {
        const response = await titleService.getStatus(contentId);
        console.log('제목 생성 상태:', response.data);
        
        if (response.data.status === 'completed') {
          // 생성 완료
          setTitles(response.data.data);
          setGenerationStatus('completed');
          setLoading(false);
          setSuccess('제목이 성공적으로 생성되었습니다.');
          
          // 인터벌 정리
          clearInterval(intervalId);
          setStatusCheckInterval(null);
        }
      } catch (err) {
        console.error('상태 확인 오류:', err);
        // 오류가 있어도 폴링은 계속
      }
    }, 5000); // 5초마다 확인
    
    setStatusCheckInterval(intervalId);
  };

  // 제목 생성
  const handleGenerateTitles = async () => {
    if (!selectedKeyword) {
      setError('키워드를 선택해주세요.');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);
    setGenerationStatus('preparing');

    try {
      // 1. 키워드 ID로 콘텐츠 목록 조회
      const contentResponse = await contentService.getContentsByKeyword(selectedKeyword);
      let contentData = [];
      
      // 응답 형식에 따라 데이터 추출
      if (Array.isArray(contentResponse.data)) {
        contentData = contentResponse.data;
      } else if (contentResponse.data && contentResponse.data.results) {
        contentData = contentResponse.data.results;
      }
      
      // 콘텐츠가 없으면 에러 표시
      if (!contentData || contentData.length === 0) {
        setError('선택한 키워드의 콘텐츠가 없습니다. 먼저 콘텐츠 관리 페이지에서 콘텐츠를 생성해주세요.');
        setLoading(false);
        return;
      }
      
      // 가장 최신 콘텐츠 ID 추출 (정렬 기준은 생성일 내림차순)
      const contentId = contentData[0].id;
      setSelectedContentId(contentId);
      setGenerationStatus('generating');
      
      // 2. 콘텐츠 ID로 제목 생성 API 호출
      const response = await titleService.generateTitles({
        content_id: contentId
      });
      
      // 응답 처리
      console.log('제목 생성 응답:', response.data);
      
      if (response.data.status === 'processing') {
        // 백그라운드 처리 중인 경우 상태 폴링 시작
        setGenerationStatus('processing');
        startStatusPolling(contentId);
      } else if (response.data && response.data.data) {
        // 바로 결과가 온 경우
        setTitles(response.data.data);
        setGenerationStatus('completed');
        setLoading(false);
        setSuccess('제목이 성공적으로 생성되었습니다.');
      } else {
        // 기타 응답 형식
        console.error('예상치 못한 API 응답 형식 (생성된 제목):', response.data);
        setTitles([]);
        setLoading(false);
        setError('제목 생성 응답이 올바른 형식이 아닙니다.');
      }
    } catch (err) {
      console.error('제목 생성 실패:', err);
      
      if (err.message && err.message.includes('timeout')) {
        // 타임아웃 오류
        setError('서버 응답 시간이 너무 깁니다. 제목은 백그라운드에서 계속 생성되고 있으니 잠시 후 다시 시도해주세요.');
        
        // 선택된 콘텐츠 ID가 있다면 폴링 시작
        if (selectedContentId) {
          setGenerationStatus('processing');
          startStatusPolling(selectedContentId);
        }
      } else if (err.response && err.response.data && err.response.data.error) {
        setError(err.response.data.error);
      } else {
        setError('제목 생성 중 오류가 발생했습니다.');
      }
      
      setLoading(false);
    }
  };

  // 제목 체크 상태
  const checkTitleStatus = async () => {
    if (!selectedContentId) {
      setError('먼저 제목 생성을 시작해주세요.');
      return;
    }
    
    try {
      setLoading(true);
      const response = await titleService.getStatus(selectedContentId);
      
      if (response.data.status === 'completed') {
        setTitles(response.data.data);
        setGenerationStatus('completed');
        setSuccess('제목이 성공적으로 생성되었습니다.');
      } else {
        setGenerationStatus(response.data.status);
        setSuccess(response.data.message);
      }
    } catch (err) {
      setError('제목 상태 확인 중 오류가 발생했습니다.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // 제목 저장
  const handleSaveTitle = async (title) => {
    if (!selectedKeyword) {
      setError('키워드를 선택해주세요.');
      return;
    }

    try {
      // 키워드 ID로 콘텐츠 조회
      const contentResponse = await contentService.getContentsByKeyword(selectedKeyword);
      let contentData = [];
      
      if (Array.isArray(contentResponse.data)) {
        contentData = contentResponse.data;
      } else if (contentResponse.data && contentResponse.data.results) {
        contentData = contentResponse.data.results;
      }
      
      if (!contentData || contentData.length === 0) {
        setError('선택한 키워드의 콘텐츠가 없습니다.');
        return;
      }
      
      // 가장 최신 콘텐츠의 ID 사용
      const contentId = contentData[0].id;
      
      // 제목 저장 API 호출
      const response = await titleService.saveTitle({
        content_id: contentId,
        title: title
      });
      
      if (response.data) {
        setSavedTitles([...savedTitles, response.data]);
        setError(null);
        setSuccess('제목이 성공적으로 저장되었습니다.');
        
        // 성공 메시지 3초 후 자동 제거
        setTimeout(() => {
          setSuccess(null);
        }, 3000);
      }
    } catch (err) {
      console.error('제목 저장 실패:', err);
      setError('제목 저장 중 오류가 발생했습니다.');
    }
  };

  // 상태 표시 컴포넌트
  const StatusIndicator = () => {
    if (!generationStatus || generationStatus === 'completed') return null;
    
    let message = '';
    let color = 'yellow';
    
    switch (generationStatus) {
      case 'preparing':
        message = '콘텐츠 정보를 조회 중입니다...';
        break;
      case 'generating':
        message = '제목을 생성하는 중입니다...';
        break;
      case 'processing':
        message = '제목이 백그라운드에서 생성 중입니다. 잠시 후 자동으로 표시됩니다...';
        color = 'blue';
        break;
      case 'pending':
        message = '제목이 아직 생성되지 않았습니다.';
        break;
      default:
        message = '처리 중입니다...';
    }
    
    return (
      <div className={`bg-${color}-100 border-l-4 border-${color}-500 text-${color}-700 p-4 mb-4`}>
        <div className="flex items-center">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500 mr-2"></div>
          <p>{message}</p>
        </div>
      </div>
    );
  };

  // 제목 목록 표시 함수
  const renderTitleLists = () => {
    if (!titles || Object.keys(titles).length === 0) return null;
    
    return (
      <div className="space-y-6">
        {Object.entries(titles).map(([type, typeItems]) => (
          <div key={type} className="bg-white rounded-lg shadow p-4">
            <h3 className="text-lg font-medium mb-2">
              {(() => {
                switch (type) {
                  case 'general': return '일반 상식 반박형';
                  case 'approval': return '인정욕구 자극형';
                  case 'secret': return '숨겨진 비밀형';
                  case 'trend': return '트렌드 제시형';
                  case 'failure': return '실패담 공유형';
                  case 'comparison': return '비교형';
                  case 'warning': return '경고형';
                  case 'blame': return '남탓 공감형';
                  case 'beginner': return '초보자 가이드형';
                  case 'benefit': return '효과 제시형';
                  default: return type;
                }
              })()}
            </h3>
            <ul className="space-y-2">
              {typeItems.map((item, index) => (
                <li key={index} className="flex justify-between items-center border-b pb-2">
                  <span>{item.suggestion || item.title}</span>
                  <button 
                    onClick={() => handleSaveTitle(item.suggestion || item.title)}
                    className="text-sm bg-green-500 hover:bg-green-600 text-white px-2 py-1 rounded"
                  >
                    저장
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    );
  };

  // 저장된 제목 렌더링
  const renderSavedTitles = () => {
    if (!savedTitles.length) return null;
    
    return (
      <div className="bg-white rounded-lg shadow p-4 mt-8">
        <h2 className="text-lg font-semibold mb-2">저장된 제목</h2>
        <ul className="space-y-2">
          {savedTitles.map(item => (
            <li key={item.id} className="flex justify-between items-center border-b pb-2">
              <div>
                <span>{item.suggestion || item.title}</span>
                {item.content_detail?.keyword_detail && (
                  <span className="ml-2 text-sm text-gray-500">
                    ({item.content_detail.keyword_detail.keyword})
                  </span>
                )}
              </div>
              {item.created_at && (
                <span className="text-sm text-gray-500">
                  {new Date(item.created_at).toLocaleDateString()}
                </span>
              )}
            </li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">제목 생성기</h1>
      
      {error && (
        <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4">
          {error}
        </div>
      )}
      
      {success && (
        <div className="bg-green-100 border-l-4 border-green-500 text-green-700 p-4 mb-4">
          {success}
        </div>
      )}
      
      <StatusIndicator />
      
      <div className="bg-white rounded-lg shadow p-4 mb-8">
        <h2 className="text-lg font-semibold mb-2">블로그 제목 생성</h2>
        
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            키워드 선택
          </label>
          <select 
            className="w-full border rounded p-2"
            value={selectedKeyword}
            onChange={(e) => setSelectedKeyword(e.target.value)}
            disabled={loading}
          >
            <option value="">키워드 선택</option>
            {Array.isArray(keywords) && keywords.map(keyword => (
              <option key={keyword.id} value={keyword.id}>
                {keyword.keyword}
              </option>
            ))}
          </select>
          
          {keywords.length === 0 && (
            <div className="text-red-500 mt-1 p-2 bg-red-50 rounded">
              <p>분석된 키워드가 없습니다. 키워드 관리에서 키워드를 추가하고 분석해주세요.</p>
              <p className="text-sm mt-1">키워드가 이미 분석되었다면 '새로고침' 버튼을 눌러보세요.</p>
            </div>
          )}
        </div>
        
        <div className="flex flex-wrap gap-2 mt-4">
          <button 
            onClick={handleGenerateTitles}
            disabled={loading || !selectedKeyword}
            className={`${
              loading || !selectedKeyword
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-blue-500 hover:bg-blue-600'
            } text-white px-4 py-2 rounded`}
          >
            {loading ? '생성 중...' : '제목 생성하기'}
          </button>
          
          {generationStatus === 'processing' && (
            <button 
              onClick={checkTitleStatus}
              className="bg-yellow-500 hover:bg-yellow-600 text-white px-4 py-2 rounded"
            >
              제목 생성 상태 확인
            </button>
          )}
          
          <button 
            onClick={() => window.location.reload()}
            className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded"
          >
            새로고침
          </button>
        </div>
      </div>
      
      {/* 생성된 제목 목록 */}
      {renderTitleLists()}
      
      {/* 저장된 제목 목록 */}
      {renderSavedTitles()}
    </div>
  );
};

export default TitleGenerator;
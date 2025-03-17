import React, { useState, useEffect, useCallback } from 'react';
import { contentService } from '../api/contentService';
import { keywordService } from '../api/keywordService';
import { useNavigate } from 'react-router-dom';
import BusinessInfoSelector from './BusinessInfoSelector'; // 새로 만든 컴포넌트 import

function ContentManagement() {
  const [contents, setContents] = useState([]);
  const [keywords, setKeywords] = useState([]);
  const [selectedKeyword, setSelectedKeyword] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [businessName, setBusinessName] = useState('');
  const [expertise, setExpertise] = useState('');
  const [customMorphemes, setCustomMorphemes] = useState('');
  const [generatingContent, setGeneratingContent] = useState(false);
  const [networkStatus, setNetworkStatus] = useState(navigator.onLine);
  const [retryCount, setRetryCount] = useState(0);
  const navigate = useNavigate();

  // 네트워크 상태 모니터링
  useEffect(() => {
    const handleOnline = () => {
      setNetworkStatus(true);
      console.log('네트워크 연결됨, 데이터 다시 로드');
      if (retryCount > 0) {
        loadData();
        setRetryCount(0);
      }
    };
    
    const handleOffline = () => {
      setNetworkStatus(false);
      console.log('네트워크 연결 끊김');
      setError('네트워크 연결이 끊겼습니다. 인터넷 연결을 확인해주세요.');
    };
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [retryCount]);

  // 재시도 로직이 포함된 loadData 함수
  const loadData = useCallback(async () => {
    const MAX_RETRIES = 3;
    let currentRetry = 0;
    
    const attemptLoad = async () => {
      try {
        console.log('데이터 로드 시작');
        setRefreshing(true);
        
        // 키워드 로드
        const keywordResponse = await keywordService.getKeywords();
        console.log('키워드 응답:', keywordResponse);
        
        // 응답 데이터 처리 개선
        let keywordData = [];
        if (Array.isArray(keywordResponse.data)) {
          keywordData = keywordResponse.data;
        } else if (keywordResponse.data.results && Array.isArray(keywordResponse.data.results)) {
          keywordData = keywordResponse.data.results;
        } else {
          console.error('예상치 못한 키워드 응답 형식:', keywordResponse.data);
        }
        
        // 분석된 키워드만 필터링
        const analyzedKeywords = keywordData.filter(k => k.main_intent);
        console.log('분석된 키워드 수:', analyzedKeywords.length);
        console.log('분석된 키워드:', analyzedKeywords);
        setKeywords(analyzedKeywords);
        
        // 콘텐츠 로드
        const contentResponse = await contentService.getContents();
        console.log('콘텐츠 응답:', contentResponse);
        
        let contentData = [];
        if (Array.isArray(contentResponse.data)) {
          contentData = contentResponse.data;
        } else if (contentResponse.data.results && Array.isArray(contentResponse.data.results)) {
          contentData = contentResponse.data.results;
        } else {
          console.error('예상치 못한 콘텐츠 응답 형식:', contentResponse.data);
        }
        
        setContents(contentData);
        setError(null); // 성공 시 에러 상태 초기화
        
      } catch (err) {
        console.error('데이터 로드 실패:', err);
        if (err.response) {
          console.error('오류 응답 데이터:', err.response.data);
          console.error('오류 응답 상태:', err.response.status);
        }
        
        // 재시도 로직
        currentRetry++;
        if (currentRetry < MAX_RETRIES) {
          console.log(`재시도 중... (${currentRetry}/${MAX_RETRIES})`);
          setError(`데이터를 불러오는 중 오류가 발생했습니다. 재시도 중... (${currentRetry}/${MAX_RETRIES})`);
          
          // 지수 백오프: 점점 더 길게 기다림
          const retryDelay = 1000 * Math.pow(2, currentRetry - 1);
          await new Promise(r => setTimeout(r, retryDelay));
          
          return attemptLoad(); // 재귀적으로 다시 시도
        } else {
          setError('데이터를 불러오는 중 오류가 발생했습니다. 새로고침을 시도해보세요.');
          setRetryCount(prev => prev + 1);
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    };
    
    await attemptLoad();
  }, []);

  // 초기 로드
  useEffect(() => {
    loadData();
  }, [loadData]);

  function handleKeywordChange(e) {
    setSelectedKeyword(e.target.value);
  }

  // 콘텐츠 생성 함수 - 재시도 로직 추가
  const handleContentGeneration = async () => {
    if (!selectedKeyword) return;
    
    // 필수 필드 검증
    if (!businessName.trim() || !expertise.trim()) {
      setError('업체명과 전문성/경력은 필수 입력 사항입니다.');
      return;
    }
    
    const MAX_RETRIES = 2;
    let currentRetry = 0;
    
    const attemptContentGeneration = async () => {
      try {
        // 로딩 상태 설정
        setLoading(true);
        setGeneratingContent(true);
        setError(null);
        
        // 형태소 처리: 공백으로 구분된 형태소들을 배열로 변환
        const morphemesArray = customMorphemes.trim() 
          ? customMorphemes.split(/\s+/).filter(m => m.trim() !== '') 
          : [];
        
        // 백엔드가 예상하는 정확한 데이터 형식으로 요청
        const requestData = {
          keyword_id: selectedKeyword,
          // 필요한 추가 필드
          target_audience: {},
          business_info: {
            name: businessName,
            expertise: expertise
          },
          custom_morphemes: morphemesArray
        };
        
        console.log('콘텐츠 생성 요청 데이터:', requestData);
        
        const response = await contentService.createContent(requestData);
        console.log('콘텐츠 생성 응답:', response.data);
        
        // 콘텐츠 생성 요청 후 상태 확인 함수
        let retryDelay = 2000; // 초기 2초
        const maxDelay = 10000; // 최대 10초
        let statusCheckRetries = 0;
        const MAX_STATUS_CHECK_RETRIES = 30; // 최대 30번 시도 (약 5분)
        
        const checkContentStatus = async () => {
          try {
            if (statusCheckRetries >= MAX_STATUS_CHECK_RETRIES) {
              setError('콘텐츠 생성 시간이 너무 오래 걸립니다. 나중에 다시 시도해주세요.');
              setGeneratingContent(false);
              setLoading(false);
              return;
            }
            
            statusCheckRetries++;
            
            // 키워드 ID로 연결된 콘텐츠 상태 확인
            const statusResponse = await contentService.getContentStatusByKeyword(selectedKeyword);
            console.log('콘텐츠 상태 확인:', statusResponse.data);
            
            if (statusResponse.data.is_completed) {
              // 콘텐츠 생성이 완료되면 전체 콘텐츠 목록 새로고침
              try {
                const refreshedContents = await contentService.getContents();
                
                let contentData = [];
                if (Array.isArray(refreshedContents.data)) {
                  contentData = refreshedContents.data;
                } else if (refreshedContents.data.results && Array.isArray(refreshedContents.data.results)) {
                  contentData = refreshedContents.data.results;
                }
                
                setContents(contentData);
                
                // 로컬 스토리지에 캐싱
                localStorage.setItem('cachedContentData', JSON.stringify(contentData));
                
              } catch (err) {
                console.error('콘텐츠 목록 새로고침 실패:', err);
                // 에러가 발생해도 진행은 계속
              }
              
              setGeneratingContent(false);
              setLoading(false);
              
              // 입력 필드 초기화
              setSelectedKeyword('');
              setBusinessName('');
              setExpertise('');
              setCustomMorphemes('');
              
              // 성공 메시지
              setError(null);
              
              return;
            } else if (statusResponse.data.has_error) {
              // 오류 발생
              setError('콘텐츠 생성 중 오류가 발생했습니다.');
              setGeneratingContent(false);
              setLoading(false);
              return;
            }
            
            // 아직 생성 중이면 점점 더 긴 간격으로 다시 확인
            retryDelay = Math.min(retryDelay * 1.5, maxDelay);
            setTimeout(checkContentStatus, retryDelay);
          } catch (err) {
            console.error('콘텐츠 상태 확인 실패:', err);
            
            // 네트워크 오류인 경우 재시도
            setTimeout(checkContentStatus, retryDelay);
          }
        };
        
        // 콘텐츠 상태 확인 시작
        setTimeout(checkContentStatus, retryDelay);
        
      } catch (err) {
        console.error('콘텐츠 생성 실패:', err);
        
        // 상세 오류 정보 로깅
        if (err.response) {
          console.error('오류 상태:', err.response.status);
          console.error('오류 데이터:', err.response.data);
          
          // 서버에서 전달한 오류 메시지 사용
          const errorMessage = err.response.data?.error || '콘텐츠 생성 중 오류가 발생했습니다.';
          setError(errorMessage);
        } else {
          setError('콘텐츠 생성 중 오류가 발생했습니다.');
        }
        
        // 네트워크 오류인 경우 재시도
        if (!err.response && currentRetry < MAX_RETRIES) {
          currentRetry++;
          console.log(`콘텐츠 생성 재시도 중... (${currentRetry}/${MAX_RETRIES})`);
          setError(`콘텐츠 생성 중 오류가 발생했습니다. 재시도 중... (${currentRetry}/${MAX_RETRIES})`);
          
          // 지수 백오프: 점점 더 길게 기다림
          const retryDelay = 2000 * Math.pow(2, currentRetry - 1);
          setTimeout(() => attemptContentGeneration(), retryDelay);
          return;
        }
        
        setGeneratingContent(false);
        setLoading(false);
      }
    };
    
    attemptContentGeneration();
  };

  // 로컬 스토리지에서 콘텐츠 데이터 캐싱 복원
  useEffect(() => {
    try {
      const cachedData = localStorage.getItem('cachedContentData');
      if (cachedData && !contents.length) {
        const parsedData = JSON.parse(cachedData);
        setContents(parsedData);
        console.log('캐시된 콘텐츠 데이터를 로드했습니다.');
      }
    } catch (err) {
      console.error('캐시된 데이터 복원 실패:', err);
    }
  }, [contents.length]);

  // 로딩 상태 표시
  if (loading && !refreshing && !generatingContent) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-2"></div>
          <p>로딩 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">콘텐츠 관리</h1>
        <div className="flex items-center space-x-2">
          {!networkStatus && (
            <div className="bg-red-100 text-red-700 px-3 py-1 rounded-md text-sm">
              오프라인 모드
            </div>
          )}
          <button 
            onClick={loadData}
            disabled={refreshing || !networkStatus}
            className={`px-4 py-2 rounded text-white ${
              refreshing || !networkStatus ? 'bg-gray-400' : 'bg-blue-500 hover:bg-blue-600'
            }`}
          >
            {refreshing ? '새로고침 중...' : '데이터 새로고침'}
          </button>
        </div>
      </div>
      
      {error && (
        <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4 flex justify-between items-center">
          <div>{error}</div>
          {error.includes('데이터를 불러오는 중') && (
            <button 
              onClick={loadData}
              className="bg-red-500 text-white px-3 py-1 rounded hover:bg-red-600 text-sm"
            >
              다시 시도
            </button>
          )}
        </div>
      )}
      
      <div className="bg-white rounded-lg shadow p-4 mb-8">
        <h2 className="text-lg font-semibold mb-2">새 콘텐츠 생성</h2>
        
        <div className="mb-4">
          <label className="block text-gray-700 mb-2">키워드 선택</label>
          <select 
            className="w-full border rounded p-2"
            value={selectedKeyword}
            onChange={handleKeywordChange}
            disabled={generatingContent || !networkStatus}
          >
            <option value="">키워드 선택</option>
            {keywords.map((keyword) => (
              <option key={keyword.id} value={keyword.id}>
                {keyword.keyword}
              </option>
            ))}
          </select>
          
          {keywords.length === 0 && (
            <div className="text-red-500 mt-1 p-2 bg-red-50 rounded">
              <p>분석된 키워드가 없습니다. 키워드 관리에서 키워드를 추가하고 분석해주세요.</p>
              <p className="text-sm mt-1">키워드가 이미 분석되었다면 '데이터 새로고침' 버튼을 눌러보세요.</p>
            </div>
          )}
        </div>
        
        {/* 업체 정보 선택/입력 컴포넌트 */}
        <BusinessInfoSelector
          businessName={businessName}
          setBusinessName={setBusinessName}
          expertise={expertise}
          setExpertise={setExpertise}
          disabled={generatingContent || !networkStatus}
        />
        
        {/* 형태소 입력 필드 (선택) */}
        <div className="mb-4 mt-4">
          <label className="block text-gray-700 mb-2">
            추가 형태소 (선택사항)
          </label>
          <input
            type="text"
            className="w-full border rounded p-2"
            placeholder="추가하고 싶은 형태소를 띄어쓰기로 구분하여 입력하세요 (예: 자동차 수리 점검)"
            value={customMorphemes}
            onChange={(e) => setCustomMorphemes(e.target.value)}
            disabled={generatingContent || !networkStatus}
          />
          <p className="text-sm text-gray-500 mt-1">
            콘텐츠에 추가로 포함시키고 싶은 핵심 단어나 형태소를 입력하세요.
          </p>
        </div>

        {selectedKeyword && (
          <button 
            onClick={handleContentGeneration}
            disabled={loading || generatingContent || !businessName.trim() || !expertise.trim() || !networkStatus}
            className={`text-white px-4 py-2 rounded w-full mt-4 ${
              loading || generatingContent || !businessName.trim() || !expertise.trim() || !networkStatus
                ? 'bg-gray-400 cursor-not-allowed' 
                : 'bg-green-500 hover:bg-green-600'
            }`}
          >
            {generatingContent ? '콘텐츠 생성 중...' : '콘텐츠 생성 시작'}
          </button>
        )}
        
        {generatingContent && (
          <div className="mt-4 bg-yellow-50 p-3 rounded border border-yellow-200">
            <div className="flex items-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-yellow-500 mr-2"></div>
              <div>
                <p className="text-yellow-700">
                  콘텐츠를 생성하고 있습니다. 이 작업은 1-2분 정도 소요될 수 있습니다.
                </p>
                <p className="text-sm text-yellow-600">
                  생성 중에는 페이지를 벗어나지 마세요. 완료되면 자동으로 목록이 새로고침됩니다.
                </p>
                <p className="text-sm text-yellow-600 mt-1">
                  만약 오류가 발생하면 자동으로 재시도합니다.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* 콘텐츠 목록 섹션 */}
      <div className="mt-8">
        <h2 className="text-xl font-semibold mb-4">콘텐츠 목록</h2>
        
        {contents.length === 0 ? (
          <div className="bg-gray-50 p-4 rounded text-center">
            생성된 콘텐츠가 없습니다.
          </div>
        ) : (
          <div className="space-y-4">
            {contents.map((content) => (
              <div key={content.id} className="bg-white p-4 rounded-lg shadow">
                <h3 className="font-semibold text-lg">{content.title}</h3>
                <p className="text-gray-600 mb-2">키워드: {content.keyword?.keyword || '정보 없음'}</p>
                <p className="text-gray-600 mb-2">생성일: {new Date(content.created_at).toLocaleDateString()}</p>
                <div className="flex gap-2 mt-2">
                  <button
                    className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                    onClick={() => navigate(`/content/${content.id}`)}
                  >
                    상세보기
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      
      <div className="bg-gray-50 p-4 rounded-lg mt-4">
        <p><strong>로드된 키워드 수:</strong> {keywords.length}</p>
        <p><strong>로드된 콘텐츠 수:</strong> {contents.length}</p>
        <p><strong>네트워크 상태:</strong> {networkStatus ? '온라인' : '오프라인'}</p>
      </div>
    </div>
  );
}

export default ContentManagement;
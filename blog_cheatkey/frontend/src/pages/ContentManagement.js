// src/pages/ContentManagement.js
import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { contentService } from '../api/contentService';
import { keywordService } from '../api/keywordService';
import { researchService } from '../api/researchService';
import { useNavigate } from 'react-router-dom';
import BusinessInfoSelector from './BusinessInfoSelector';

function ContentManagement() {
  const navigate = useNavigate();
  
  // 상태 관리
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
  const [statusCheckInterval, setStatusCheckInterval] = useState(null);
  const [collectingResearch, setCollectingResearch] = useState(false);
  const [researchCollected, setResearchCollected] = useState(false);
  const [researchStats, setResearchStats] = useState(null);
  const [processingStep, setProcessingStep] = useState('');
  // 진행 상태 추적을 위한 상태 추가
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationStatus, setGenerationStatus] = useState(null);
  const [generationMessage, setGenerationMessage] = useState('');
  const [hasNavigated, setHasNavigated] = useState(false);

  
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

  // 페이지 로드시 대기 시간 설정
  useEffect(() => {
    // 0.5초 대기 후 로딩 완료 처리
    const timer = setTimeout(() => {
      setLoading(false);
    }, 500);
    
    return () => clearTimeout(timer);
  }, []);

  // 콘텐츠 생성 완료 처리 함수
  const handleContentCompletion = (statusData, interval) => {
    // 페이지 이동 플래그 설정
    setHasNavigated(true);
    
    // 로그와 상태 갱신
    console.log('콘텐츠 생성 100% 완료 - 폴링 중지');
    clearInterval(interval);
    setStatusCheckInterval(null);
    setGeneratingContent(false);
    
    // 콘텐츠 ID 가져오기
    const contentId = statusData.content_id || 
                    statusData.id || 
                    (statusData.result && statusData.result.id) || 
                    (statusData.data && statusData.data.content_id);
    
    // 사용자에게 완료 메시지 표시
    setGenerationMessage('콘텐츠 생성이 완료되었습니다. 잠시 후 자동으로 이동합니다...');
    
    if (contentId) {
      console.log('콘텐츠 ID 감지:', contentId, '- 페이지 이동 필요');
      
      // 상태에 contentId 저장
      setGenerationStatus(prev => ({
        ...prev,
        content_id: contentId
      }));
      
      // 네트워크 오류 방지를 위해 직접 이동 사용 - broken pipe 해결
      // 로딩바가 100% 되었음을 보여주기 위해 2초 대기
      setTimeout(() => {
        console.log('새창으로 페이지 이동 실행');
        window.location.href = `/content/${contentId}`;
      }, 2000);
    }
  };

  function handleKeywordChange(e) {
    setSelectedKeyword(e.target.value);
    // 키워드가 변경되면 연구 자료 수집 상태 초기화
    setResearchCollected(false);
    setResearchStats(null);
  }

  // 연구 자료 수집 함수
  const collectResearchData = async () => {
    if (!selectedKeyword) {
      setError('키워드를 선택해주세요.');
      return false;
    }
    
    // 필수 필드 검증
    if (!businessName.trim() || !expertise.trim()) {
      setError('업체명과 전문성/경력은 필수 입력 사항입니다.');
      return false;
    }
    
    try {
      setCollectingResearch(true);
      setProcessingStep('research');
      setError(null);
      
      // 연구 자료 수집 API 호출
      const response = await researchService.collectResearch(selectedKeyword);
      
      if (response.data) {
        console.log('연구 자료 수집 응답:', response.data);
        
        // 연구 자료 수집 상태 확인 (폴링 방식)
        let isCompleted = false;
        let attempts = 0;
        const MAX_ATTEMPTS = 30; // 최대 30번 확인 (약 60초)
        
        while (!isCompleted && attempts < MAX_ATTEMPTS) {
          attempts++;
          
          // 2초 지연
          await new Promise(resolve => setTimeout(resolve, 2000));
          
          try {
            // 연구 자료 수집 상태 확인
            const statusResponse = await researchService.checkResearchStatus(selectedKeyword);
            console.log('연구 자료 수집 상태:', statusResponse.data);
            
            if (statusResponse.data.status === 'completed') {
              isCompleted = true;
              
              // 수집 결과 통계 설정
              setResearchStats({
                newsCount: statusResponse.data.data?.news_count || 0,
                academicCount: statusResponse.data.data?.academic_count || 0,
                generalCount: statusResponse.data.data?.general_count || 0,
                statisticsCount: statusResponse.data.data?.statistics_count || 0
              });
              
              setResearchCollected(true);
              break;
            } else if (statusResponse.data.status === 'failed') {
              throw new Error(statusResponse.data.error || '연구 자료 수집 실패');
            }
          } catch (statusError) {
            console.error('상태 확인 중 오류:', statusError);
            // 오류가 발생해도 계속 시도
          }
        }
        
        // 시간 초과 또는 완료
        if (!isCompleted) {
          if (attempts >= MAX_ATTEMPTS) {
            setError('연구 자료 수집 시간이 초과되었습니다. 다시 시도해주세요.');
            setResearchCollected(false);
            setCollectingResearch(false);
            return false;
          }
        }
        
        setCollectingResearch(false);
        return true;
      } else {
        throw new Error('응답 데이터가 없습니다');
      }
      
    } catch (err) {
      console.error('연구 자료 수집 실패:', err);
      setError('연구 자료 수집 중 오류가 발생했습니다: ' + (err.message || '알 수 없는 오류'));
      setCollectingResearch(false);
      return false;
    }
  };

  // 콘텐츠 생성 전 소제목 확인 기능 추가
  const confirmSubtopics = async () => {
    if (!selectedKeyword) {
      setError('키워드를 선택해주세요.');
      return false;
    }
    
    try {
      // 선택된 키워드의 소제목 정보 가져오기
      const keywordDetail = await keywordService.getKeyword(selectedKeyword);
      const subtopics = keywordDetail.data.subtopics || [];
      
      // 소제목이 없는 경우
      if (subtopics.length === 0) {
        const confirm = window.confirm('이 키워드에는 소제목이 없습니다. 계속 진행하시겠습니까?');
        return confirm;
      }
      
      // 소제목 목록 표시 및 확인
      const subtopicsList = subtopics.map((st, idx) => `${idx+1}. ${st.title || st}`).join('\n');
      const confirmMsg = `다음 소제목을 기준으로 콘텐츠를 생성합니다:\n\n${subtopicsList}\n\n계속 진행하시겠습니까?`;
      
      return window.confirm(confirmMsg);
    } catch (err) {
      console.error('소제목 확인 중 오류:', err);
      return false;
    }
  };

  // 콘텐츠 생성 함수 - 새로운 백그라운드 처리 방식으로 수정
  const handleContentGeneration = async () => {
    // 소제목 확인 요청
    const confirmed = await confirmSubtopics();
    if (!confirmed) return;

    if (!selectedKeyword) {
      setError('키워드를 선택해주세요.');
      return;
    }
    
    // 필수 필드 검증
    if (!businessName.trim() || !expertise.trim()) {
      setError('업체명과 전문성/경력은 필수 입력 사항입니다.');
      return;
    }
    
    // 연구 자료 수집 단계
    if (!researchCollected) {
      const researchSuccess = await collectResearchData();
      if (!researchSuccess) {
        return;  // 연구 자료 수집 실패 시 중단
      }
    }
    
    try {
      // 로딩 상태 설정
      setLoading(true);
      setGeneratingContent(true);
      setProcessingStep('content');
      setError(null);
      setGenerationProgress(0);
      setGenerationMessage('콘텐츠 생성 준비 중...');
      
      // 형태소 처리
      const morphemesArray = customMorphemes.trim() 
        ? customMorphemes.split(/\s+/).filter(m => m.trim() !== '') 
        : [];
      
      // 백엔드가 예상하는 정확한 데이터 형식으로 요청
      const requestData = {
        keyword_id: selectedKeyword,
        business_info: {
          name: businessName,
          expertise: expertise
        },
        custom_morphemes: morphemesArray
      };
      
      console.log('콘텐츠 생성 요청 데이터:', requestData);
      
      // 백그라운드에서 콘텐츠 생성 시작
      const response = await contentService.createContent(requestData);
      console.log('콘텐츠 생성 응답:', response.data);
      
      // 상태 ID 가져오기 - 다양한 형태의 응답 처리
      // ID를 추출하는데 문자열 값이 아닌 숫자만 사용
      let statusId = null;
      
      // 가능한 ID 필드들
      const possibleIdFields = [
        response.data.status_id,
        response.data.id,
        response.data.content_id,
        response.data.process_id,
        response.data.result?.id,
        response.data.data?.id
      ];
      
      // 첫 번째 유효한 숫자 ID 사용
      for (const field of possibleIdFields) {
        if (field !== undefined && field !== null && !isNaN(Number(field))) {
          statusId = field;
          break;
        }
      }
      
      // 유효한 ID가 없으면 최종적으로 키워드 ID 사용 (숫자만 사용)
      if (statusId === null) {
        // 키워드 ID가 유효한 숫자인지 확인
        if (!isNaN(Number(selectedKeyword))) {
          statusId = selectedKeyword;
          console.log('응답에서 ID를 찾을 수 없어 키워드 ID 사용:', statusId);
        } else {
          // 유효한 ID가 없으면 오류 처리
          throw new Error('유효한 상태 ID를 찾을 수 없습니다');
        }
      }
      
      console.log('추출된 상태 ID:', statusId);
      
      if (statusId) {
        // 상태 폴링 시작
        startStatusPolling(statusId);
      } else {
        throw new Error('상태 ID를 찾을 수 없습니다');
      }
      
    } catch (err) {
      console.error('콘텐츠 생성 실패:', err);
      setError('콘텐츠 생성 중 오류가 발생했습니다: ' + (err.message || '알 수 없는 오류'));
      setGeneratingContent(false);
      setLoading(false);
    }
  };
  
  // 오류 발생 횟수 추적을 위한 상태
  const [errorCount, setErrorCount] = useState(0);

  // 상태 폴링 함수 - 상태 ID를 받아 상태를 확인하고 페이지 이동 처리
  const startStatusPolling = (statusId) => {
    console.log('상태 폴링 시작. 상태 ID:', statusId);
    
    // 기존 인터벌이 있으면 제거
    if (statusCheckInterval) {
      clearInterval(statusCheckInterval);
      setStatusCheckInterval(null);
    }
    
    // 오류 카운트 초기화
    setErrorCount(0);
    
    // 상태 확인을 위한 새 인터벌 생성
    const newInterval = setInterval(async () => {
      // 인터벌 변수 상태에 저장
      setStatusCheckInterval(newInterval);
      
      try {
        // 현재 이미 다른 페이지로 이동 중인지 확인
        if (hasNavigated) {
          console.log('이미 이동 중이므로 폴링 중지');
          clearInterval(newInterval);
          setStatusCheckInterval(null);
          return;
        }
        
        // 상태 정보 요청
        const statusResponse = await contentService.getContentGenerationStatus(statusId);
        const statusData = statusResponse.data;
        
        // 로그 추가
        console.log('상태 업데이트:', statusData);
        
        // 상태 업데이트
        setGenerationStatus(statusData);
        
        // 진행률 업데이트
        const progress = statusData.progress || 0;
        setGenerationProgress(progress);
        
        // 메시지 업데이트
        try {
          if (statusData.message) {
            setGenerationMessage(statusData.message);
          }
        } catch (err) {
          console.error('메시지 업데이트 오류:', err);
        }
        
        // 콘텐츠 ID 추출
        const contentId = statusData.content_id || statusResponse.data.content_id;
        
        // 상태에 따른 처리
        if (statusData.status === 'completed') {
          // 완료 상태지만 진행률이 100%가 아니면 100%로 설정
          if (progress < 100) {
            console.log('완료 상태지만 진행률이 100%가 아님:', progress, '100%로 설정');
            setGenerationProgress(100);
            // 1초 대기 후 페이지 이동 처리
            setTimeout(() => {
              handleContentCompletion(statusData, newInterval);
            }, 1000);
            return;
          }
          
          // 상태가 completed이고 진행률이 이미 100%인 경우 바로 처리
          const contentResult = handleContentCompletion(statusData, newInterval);
        } 
        // 100%이지만 'completed'가 아닌 경우 대비
        else if (progress === 100 && statusData.status !== 'completed') {
          console.log('100% 진행률이지만 완료 상태가 아님 - 기다리는 중');          
          setGenerationMessage('콘텐츠 완성중... 잠시만 기다려주세요.');  
        }
        // 진행률이 높지만 100%가 아닌 경우
        else if (progress >= 95 && progress < 100) {
          console.log('진행률이 거의 끝나가는 중:', progress, '%');
          setGenerationMessage(`콘텐츠 생성 거의 완료: ${progress}%. 잠시만 기다려주세요...`);
        }
        // 오류 상태 처리
        else if (statusData.status === 'error' || statusResponse.data.status === 'failed' || statusResponse.data.error) {
          // 실패한 경우 인터벌 정리 및 에러 표시
          console.log('오류 상태 감지:', statusData.status, statusResponse.data.status);
          clearInterval(newInterval);
          setStatusCheckInterval(null);
          setGeneratingContent(false);
          setError(`콘텐츠 생성 실패: ${statusData.message || statusResponse.data.error || '알 수 없는 오류'}`);
        }
        // processing 상태는 계속 진행

      } catch (error) {
        // 오류 상세 정보 로깅
        console.error('상태 확인 중 오류 발생:', error);
        if (error.response) {
          // 서버 응답 오류
          console.error('서버 응답 오류:', error.response.status, error.response.data);
        } else if (error.request) {
          // 요청은 보냈지만 응답이 없음 (CORS 문제 등)
          console.error('서버 응답 없음:', error.request);
        } else {
          // 그 외 오류
          console.error('오류 메시지:', error.message);
        }
        
        // 사용자에게 메시지 표시
        setGenerationMessage('상태 확인 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
        
        // 오류 횟수 증가 (상태 변수 사용)
        const newErrorCount = errorCount + 1;
        setErrorCount(newErrorCount);
        console.log(`오류 발생 횟수: ${newErrorCount}/5`);
        
        // 여러 번의 오류가 연속되면 폴링 중지
        if (newErrorCount >= 5) {
          console.log('오류가 여러 번 발생하여 폴링을 중지합니다.');
          clearInterval(newInterval);
          setStatusCheckInterval(null);
          setGeneratingContent(false);
          setError('콘텐츠 생성 중 연속 오류 발생 - 페이지를 새로고침해주세요.');
        }
      }
    }, 2000); // 2초마다 상태 확인
    
    // 새 인터벌 저장
    setStatusCheckInterval(newInterval);
  };
  
  // 컴포넌트 언마운트 시 인터벌 정리
  useEffect(() => {
    return () => {
      if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
      }
    };
  }, [statusCheckInterval]);

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
  if (loading && !refreshing && !generatingContent && !collectingResearch) {
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
            disabled={generatingContent || collectingResearch || !networkStatus}
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
          disabled={generatingContent || collectingResearch || !networkStatus}
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
            disabled={generatingContent || collectingResearch || !networkStatus}
          />
          <p className="text-sm text-gray-500 mt-1">
            콘텐츠에 추가로 포함시키고 싶은 핵심 단어나 형태소를 입력하세요.
          </p>
        </div>

        {selectedKeyword && (
          <button 
            onClick={handleContentGeneration}
            disabled={loading || generatingContent || collectingResearch || !businessName.trim() || !expertise.trim() || !networkStatus}
            className={`text-white px-4 py-2 rounded w-full mt-4 ${
              loading || generatingContent || collectingResearch || !businessName.trim() || !expertise.trim() || !networkStatus
                ? 'bg-gray-400 cursor-not-allowed' 
                : researchCollected 
                  ? 'bg-green-500 hover:bg-green-600'
                  : 'bg-blue-500 hover:bg-blue-600'
            }`}
          >
            {generatingContent || collectingResearch 
              ? processingStep === 'research' 
                ? '연구 자료 수집 중...' 
                : '콘텐츠 생성 중...'
              : researchCollected
                ? '콘텐츠 생성 시작'
                : '자료 수집 후 콘텐츠 생성하기'
            }
          </button>
        )}
        
        {/* 연구 자료 수집 결과 표시 */}
        {researchCollected && researchStats && (
          <div className="mt-4 bg-green-50 p-3 rounded border border-green-200">
            <p className="text-green-700 font-medium">연구 자료 수집 완료</p>
            <div className="grid grid-cols-2 gap-2 mt-2">
              <div className="bg-white p-2 rounded border border-green-100">
                <p className="text-sm text-gray-600">뉴스 자료</p>
                <p className="font-bold text-green-600">{researchStats.newsCount} 개</p>
              </div>
              <div className="bg-white p-2 rounded border border-green-100">
                <p className="text-sm text-gray-600">학술 자료</p>
                <p className="font-bold text-green-600">{researchStats.academicCount} 개</p>
              </div>
              <div className="bg-white p-2 rounded border border-green-100">
                <p className="text-sm text-gray-600">일반 자료</p>
                <p className="font-bold text-green-600">{researchStats.generalCount} 개</p>
              </div>
              <div className="bg-white p-2 rounded border border-green-100">
                <p className="text-sm text-gray-600">통계 데이터</p>
                <p className="font-bold text-green-600">{researchStats.statisticsCount} 개</p>
              </div>
            </div>
          </div>
        )}
        
        {(generatingContent || collectingResearch) && (
          <div className="mt-4 bg-yellow-50 p-3 rounded border border-yellow-200">
            <div className="flex items-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-yellow-500 mr-2"></div>
              <div className="w-full">
                {processingStep === 'research' ? (
                  <div>
                    <p className="text-yellow-700">연구 자료를 수집하고 있습니다. 이 작업은 30초 정도 소요될 수 있습니다.</p>
                    <p className="text-sm text-yellow-600">수집된 자료는 콘텐츠 생성에 활용됩니다.</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-yellow-700">
                      {generationStatus === 'completed' ? generationMessage : `콘텐츠를 생성하고 있습니다: ${generationMessage}`}
                    </p>
                    <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2 mb-2">
                      <div 
                        className="bg-blue-600 h-2.5 rounded-full transition-all duration-300" 
                        style={{ width: `${generationProgress}%` }}
                      ></div>
                    </div>
                    <div className="flex justify-between text-xs text-gray-500 mb-2">
                      <span>진행률: {generationProgress}%</span>
                      <span>{generationStatus === 'completed' ? '완료됨' : '진행 중...'}</span>
                    </div>
                    <p className="text-sm text-yellow-600">
                      {generationStatus === 'completed' && generationStatus.content_id ? (
                        <button
                          onClick={() => navigate(`/content/${generationStatus.content_id}`)}
                          className="mt-2 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 font-bold"
                        >
                          콘텐츠 보기
                        </button>
                      ) : (
                        '생성 중에는 페이지를 벗어나지 마세요. 완료되면 콘텐츠 보기 버튼이 나타납니다.'
                      )}
                    </p>
                  </div>
                )}
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
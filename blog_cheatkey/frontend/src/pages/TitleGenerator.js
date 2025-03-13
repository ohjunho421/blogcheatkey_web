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
  }, []);

  // 제목 생성
  const handleGenerateTitles = async () => {
    if (!selectedKeyword) {
      setError('키워드를 선택해주세요.');
      return;
    }

    setLoading(true);
    setError(null);

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
      
      // 2. 콘텐츠 ID로 제목 생성 API 호출
      const response = await titleService.generateTitles({
        content_id: contentId,
        count: titleCount
      });
      
      // 응답 처리
      console.log('제목 생성 응답:', response.data);
      
      if (response.data && response.data.data) {
        // 응답 구조가 { message: string, data: { [type]: [] } } 형태인 경우
        // 모든 유형의 제목을 하나의 배열로 합치기
        const allTitles = [];
        for (const type in response.data.data) {
          if (Array.isArray(response.data.data[type])) {
            response.data.data[type].forEach(title => {
              allTitles.push(title.suggestion || title.title);
            });
          }
        }
        setTitles(allTitles);
      } else if (response.data && response.data.titles && Array.isArray(response.data.titles)) {
        // 응답 구조가 { titles: [] } 형태인 경우
        setTitles(response.data.titles);
      } else {
        console.error('예상치 못한 API 응답 형식 (생성된 제목):', response.data);
        setTitles([]);
      }
    } catch (err) {
      console.error('제목 생성 실패:', err);
      if (err.response && err.response.data && err.response.data.error) {
        setError(err.response.data.error);
      } else {
        setError('제목 생성 중 오류가 발생했습니다.');
      }
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
      }
    } catch (err) {
      console.error('제목 저장 실패:', err);
      setError('제목 저장 중 오류가 발생했습니다.');
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">제목 생성기</h1>
      
      {error && <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4">{error}</div>}
      
      <div className="bg-white rounded-lg shadow p-4 mb-8">
        <h2 className="text-lg font-semibold mb-2">블로그 제목 생성</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              키워드 선택
            </label>
            <select 
              className="w-full border rounded p-2"
              value={selectedKeyword}
              onChange={(e) => setSelectedKeyword(e.target.value)}
            >
              <option value="">키워드 선택</option>
              {Array.isArray(keywords) && keywords.map(keyword => (
                <option key={keyword.id} value={keyword.id}>
                  {keyword.keyword}
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              생성할 제목 수
            </label>
            <input 
              type="number" 
              min="1" 
              max="10"
              value={titleCount}
              onChange={(e) => setTitleCount(Math.min(10, Math.max(1, parseInt(e.target.value) || 1)))}
              className="w-full border rounded p-2"
            />
          </div>
        </div>
        
        <button 
          onClick={handleGenerateTitles}
          disabled={loading}
          className="w-full bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded"
        >
          {loading ? '생성 중...' : '제목 생성하기'}
        </button>
      </div>
      
      {Array.isArray(titles) && titles.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4 mb-8">
          <h2 className="text-lg font-semibold mb-2">생성된 제목</h2>
          <ul className="space-y-2">
            {titles.map((title, index) => (
              <li key={index} className="flex justify-between items-center border-b pb-2">
                <span>{title}</span>
                <button 
                  onClick={() => handleSaveTitle(title)}
                  className="text-sm bg-green-500 hover:bg-green-600 text-white px-2 py-1 rounded"
                >
                  저장
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {Array.isArray(savedTitles) && savedTitles.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-2">저장된 제목</h2>
          <ul className="space-y-2">
            {savedTitles.map(item => (
              <li key={item.id} className="flex justify-between items-center border-b pb-2">
                <div>
                  <span>{item.title}</span>
                  {item.keyword && (
                    <span className="ml-2 text-sm text-gray-500">
                      ({item.keyword.keyword})
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
      )}
    </div>
  );
};

export default TitleGenerator;
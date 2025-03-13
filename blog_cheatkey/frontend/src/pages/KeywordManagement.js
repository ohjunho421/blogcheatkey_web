// src/pages/KeywordManagement.js
import React, { useState, useEffect } from 'react';
import { keywordService } from '../api/keywordService';

const KeywordManagement = () => {
  const [keywords, setKeywords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newKeyword, setNewKeyword] = useState('');
  const [analyzing, setAnalyzing] = useState(false);

  // 키워드 목록 로드
  useEffect(() => {
    fetchKeywords();
  }, []);
  
  const fetchKeywords = async () => {
    console.log('키워드 가져오기 시작');
    console.log('로컬 스토리지 토큰:', localStorage.getItem('token'));
    try {
      const response = await keywordService.getKeywords();
      console.log('API 응답:', response);
      
      // 응답이 배열인지 확인하고 처리
      if (Array.isArray(response.data)) {
        setKeywords(response.data);
      } else if (response.data.results && Array.isArray(response.data.results)) {
        // Django REST Framework의 페이지네이션 응답인 경우
        setKeywords(response.data.results);
      } else {
        // 기타 경우, 빈 배열로 설정
        console.error('예상치 못한 API 응답 형식:', response.data);
        setKeywords([]);
      }
      setLoading(false);
    } catch (err) {
      console.error('키워드 가져오기 실패:', err);
      // 오류 응답 상세 정보 확인
      if (err.response) {
        console.error('오류 응답 데이터:', err.response.data);
        console.error('오류 응답 상태:', err.response.status);
        console.error('오류 응답 헤더:', err.response.headers);
      }
      setError('키워드를 불러오는 중 오류가 발생했습니다.');
      setLoading(false);
    }
  };

  // 새 키워드 추가
  const handleAddKeyword = async (e) => {
    e.preventDefault();
    if (!newKeyword.trim()) return;

    try {
      const response = await keywordService.createKeyword({ keyword: newKeyword });
      setKeywords([...keywords, response.data]);
      setNewKeyword('');
    } catch (err) {
      setError('키워드 추가 중 오류가 발생했습니다.');
      console.error(err);
    }
  };

  // 키워드 삭제 함수
  const handleDeleteKeyword = async (id) => {
    if (window.confirm('정말로 이 키워드를 삭제하시겠습니까?')) {
      try {
        await keywordService.deleteKeyword(id);
        // 삭제 후 키워드 목록에서 해당 항목 제거
        setKeywords(keywords.filter(keyword => keyword.id !== id));
      } catch (err) {
        setError('키워드 삭제 중 오류가 발생했습니다.');
        console.error(err);
      }
    }
  };

  // 키워드 분석
  const analyzeKeyword = async (id) => {
    setAnalyzing(true);
    setError(null); // 기존 오류 메시지 초기화
    
    try {
      const response = await keywordService.analyzeKeyword(id);
      console.log('키워드 분석 응답:', response.data);
      
      // 분석 데이터 확인
      if (!response.data || Object.keys(response.data).length === 0) {
        throw new Error('분석 데이터가 비어있습니다');
      }
      
      // 서버에 분석 결과 저장 (PUT 요청)
      const updateResponse = await keywordService.updateKeyword(id, {
        ...response.data,
        analysis_complete: true // 분석 완료 플래그 추가
      });
      
      console.log('키워드 업데이트 응답:', updateResponse.data);
      
      // 상태 업데이트 전에 확인
      console.log('업데이트할 키워드 ID:', id);
      
      // 로컬 상태 업데이트
      setKeywords(prevKeywords => 
        prevKeywords.map(keyword => 
          keyword.id === id ? { ...keyword, ...response.data, analysis_complete: true } : keyword
        )
      );
      
      // 성공 알림 (선택적)
      // alert('키워드 분석이 완료되었습니다');
      
    } catch (err) {
      console.error('키워드 분석 오류:', err);
      setError('키워드 분석 중 오류가 발생했습니다.');
      
      // 3초 후 오류 메시지 자동 제거 (선택적)
      setTimeout(() => {
        setError(null);
      }, 3000);
      
    } finally {
      setAnalyzing(false);
    }
  };

  // 소제목 추천
  const suggestSubtopics = async (id) => {
    try {
      const response = await keywordService.suggestSubtopics(id);
      console.log('소제목 응답:', response.data);
      
      // 소제목 추천 결과로 키워드 업데이트
      const updatedKeywords = keywords.map(keyword => 
        keyword.id === id ? { ...keyword, subtopics: response.data } : keyword
      );
      
      setKeywords(updatedKeywords);
    } catch (err) {
      setError('소제목 추천 중 오류가 발생했습니다.');
      console.error(err);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">키워드 관리</h1>
      
      {error && <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4">{error}</div>}
      
      <div className="bg-white rounded-lg shadow p-4 mb-8">
        <h2 className="text-lg font-semibold mb-2">새 키워드 추가</h2>
        <form onSubmit={handleAddKeyword} className="flex gap-2">
          <input
            type="text"
            value={newKeyword}
            onChange={(e) => setNewKeyword(e.target.value)}
            placeholder="키워드 입력..."
            className="flex-1 border rounded p-2"
          />
          <button 
            type="submit"
            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded"
          >
            추가
          </button>
        </form>
      </div>
      
      <h2 className="text-xl font-semibold mb-4">키워드 목록</h2>
      
      {loading ? (
        <div className="text-center py-4">로딩 중...</div>
      ) : keywords.length === 0 ? (
        <div className="text-center py-4 bg-gray-50 rounded">
          등록된 키워드가 없습니다.
        </div>
      ) : (
        <div className="space-y-4">
          {keywords.map(keyword => (
            <div key={keyword.id} className="border rounded-lg bg-white p-4">
              <h3 className="text-lg font-semibold mb-2">{keyword.keyword}</h3>
              
              {keyword.main_intent && (
                <div className="mb-4">
                  <p className="font-medium">주요 검색 의도:</p>
                  <p className="text-gray-700">{keyword.main_intent}</p>
                </div>
              )}
              
              {keyword.subtopics && keyword.subtopics.length > 0 && (
                <div className="mb-4">
                  <p className="font-medium">추천 소제목:</p>
                  <ul className="list-disc pl-5">
                    {keyword.subtopics.map((subtopic, index) => (
                      <li key={index} className="text-gray-700">
                        {typeof subtopic === 'string' 
                          ? subtopic 
                          : (subtopic.title || `소제목 ${index + 1}`)}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              <div className="flex gap-2 mt-4">
                {!keyword.main_intent && (
                  <button 
                    onClick={() => analyzeKeyword(keyword.id)}
                    disabled={analyzing}
                    className="bg-purple-500 hover:bg-purple-600 text-white px-3 py-1 rounded text-sm"
                  >
                    {analyzing ? '분석 중...' : '키워드 분석'}
                  </button>
                )}
                
                {keyword.main_intent && !keyword.subtopics && (
                  <button 
                    onClick={() => suggestSubtopics(keyword.id)}
                    className="bg-green-500 hover:bg-green-600 text-white px-3 py-1 rounded text-sm"
                  >
                    소제목 추천
                  </button>
                )}
                
                <button 
                  onClick={() => handleDeleteKeyword(keyword.id)}
                  className="bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded text-sm"
                >
                  삭제
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default KeywordManagement;
// src/pages/KeywordManagement.js
import React, { useState, useEffect } from 'react';
import { keywordService } from '../api/keywordService';

const KeywordManagement = () => {
  const [keywords, setKeywords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [newKeyword, setNewKeyword] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [editingSubtopic, setEditingSubtopic] = useState({ keywordId: null, index: null, value: '' });
  
  //키워드 타겟 정보 편집 상태
  //const [editingTargetInfo, setEditingTargetInfo] = useState({ keywordId: null, field: null });
  //const [editValue, setEditValue] = useState('');
  //const [editingPainPoints, setEditingPainPoints] = useState([]);
  //const [editingInfoNeeded, setEditingInfoNeeded] = useState([]);
  //const [updateMessage, setUpdateMessage] = useState('');

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

  // 새 키워드 추가 - 맨 위에 추가되도록 수정
  const handleAddKeyword = async (e) => {
    e.preventDefault();
    if (!newKeyword.trim()) return;

    try {
      const response = await keywordService.addKeyword({ keyword: newKeyword });
      // 새 키워드를 배열의 맨 앞에 추가 (변경된 부분)
      setKeywords([response.data, ...keywords]);
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

  // 키워드 분석 - 자동 새로고침 기능 추가
  const analyzeKeyword = async (id) => {
    setAnalyzing(true);
    setError(null); // 기존 오류 메시지 초기화
    
    try {
      // 분석 요청 전송
      const response = await keywordService.analyzeKeyword(id);
      console.log('키워드 분석 요청 성공:', response.data);
      
      // 분석 상태 확인 함수
      const checkAnalysisStatus = async () => {
        try {
          // 키워드 상세 정보 가져오기
          const keywordDetail = await keywordService.getKeyword(id);
          console.log('키워드 상태 확인:', keywordDetail.data);
          
          // 분석 결과가 있는지 확인
          if (keywordDetail.data.main_intent) {
            // 분석이 완료된 경우 키워드 목록 새로고침
            const updatedKeywords = await keywordService.getKeywords();
            if (Array.isArray(updatedKeywords.data)) {
              setKeywords(updatedKeywords.data);
            } else if (updatedKeywords.data.results && Array.isArray(updatedKeywords.data.results)) {
              setKeywords(updatedKeywords.data.results);
            }
            
            setAnalyzing(false);
            // 분석 완료 메시지 설정 (3초 후 자동 사라짐)
            setError(null);
            return;
          }
          
          // 아직 분석 중인 경우 2초 후 다시 확인
          setTimeout(checkAnalysisStatus, 2000);
        } catch (err) {
          console.error('키워드 상태 확인 오류:', err);
          setError('키워드 상태 확인 중 오류가 발생했습니다.');
          setAnalyzing(false);
        }
      };
      
      // 분석 상태 확인 시작
      setTimeout(checkAnalysisStatus, 2000);
      
    } catch (err) {
      console.error('키워드 분석 오류:', err);
      setError('키워드 분석 중 오류가 발생했습니다.');
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

  // 소제목 편집 시작
  const handleEditSubtopic = (keywordId, index, value) => {
    setEditingSubtopic({ keywordId, index, value });
  };

  // 소제목 편집 취소
  const handleCancelEdit = () => {
    setEditingSubtopic({ keywordId: null, index: null, value: '' });
  };

  // 소제목 편집 저장
  const handleSaveSubtopic = async (keywordId) => {
    try {
      // 편집할 키워드 찾기
      const keyword = keywords.find(k => k.id === keywordId);
      if (!keyword || !keyword.subtopics) return;
      
      // 소제목 목록 복사 및 변경
      const updatedSubtopics = [...keyword.subtopics];
      updatedSubtopics[editingSubtopic.index] = editingSubtopic.value;
      
      console.log('저장 중인 소제목:', updatedSubtopics); // 소제목 데이터 로깅
      
      // 일반 updateKeyword 대신 updateSubtopics 호출
      const response = await keywordService.updateSubtopics(keywordId, updatedSubtopics);
      
      console.log('API 응답:', response.data); // 응답 로깅
      
      // 로컬 상태 업데이트
      const updatedKeywords = keywords.map(k => {
        if (k.id === keywordId) {
          return { ...k, subtopics: updatedSubtopics };
        }
        return k;
      });
      
      setKeywords(updatedKeywords);
      setEditingSubtopic({ keywordId: null, index: null, value: '' });
      
      // 성공 메시지 추가
      setSuccess('소제목이 성공적으로 저장되었습니다. 이 소제목으로 콘텐츠가 생성됩니다.');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      console.error('소제목 업데이트 오류:', err);
      if (err.response) {
        console.error('오류 응답:', err.response.data);
      }
      setError('소제목 업데이트 중 오류가 발생했습니다.');
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">키워드 관리</h1>
      
      {error && <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4">{error}</div>}
      
      {/* 성공 메시지 추가 */}
      {success && <div className="bg-green-100 border-l-4 border-green-500 text-green-700 p-4 mb-4">{success}</div>}

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
                      <li key={index} className="text-gray-700 mt-2">
                        {editingSubtopic.keywordId === keyword.id && editingSubtopic.index === index ? (
                          <div className="flex items-center gap-2">
                            <input
                              type="text"
                              value={editingSubtopic.value}
                              onChange={(e) => setEditingSubtopic({...editingSubtopic, value: e.target.value})}
                              className="border rounded p-1 w-full"
                            />
                            <button 
                              onClick={() => handleSaveSubtopic(keyword.id)}
                              className="bg-green-500 text-white px-2 py-1 rounded text-xs"
                            >
                              저장
                            </button>
                            <button 
                              onClick={handleCancelEdit}
                              className="bg-gray-500 text-white px-2 py-1 rounded text-xs"
                            >
                              취소
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center justify-between">
                            <span>
                              {typeof subtopic === 'string' 
                                ? subtopic 
                                : (subtopic.title || `소제목 ${index + 1}`)}
                            </span>
                            <button 
                              onClick={() => handleEditSubtopic(
                                keyword.id, 
                                index, 
                                typeof subtopic === 'string' ? subtopic : (subtopic.title || `소제목 ${index + 1}`)
                              )}
                              className="bg-blue-500 text-white px-2 py-1 rounded text-xs ml-2"
                            >
                              수정
                            </button>
                          </div>
                        )}
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
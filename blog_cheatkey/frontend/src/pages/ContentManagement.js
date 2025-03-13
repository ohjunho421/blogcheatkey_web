import React, { useState, useEffect } from 'react';
import { contentService } from '../api/contentService';
import { keywordService } from '../api/keywordService';
import { useNavigate } from 'react-router-dom';

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
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
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
      setError('데이터를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  function handleKeywordChange(e) {
    setSelectedKeyword(e.target.value);
  }

  // 콘텐츠 생성 함수 추가
  const handleContentGeneration = async () => {
    if (!selectedKeyword) return;
    
    // 필수 필드 검증
    if (!businessName.trim() || !expertise.trim()) {
      setError('업체명과 전문성/경력은 필수 입력 사항입니다.');
      return;
    }
    
    try {
      // 로딩 상태 설정
      setLoading(true);
      
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
      
      // 응답 구조에 맞게 데이터 처리
      if (response.data && response.data.data) {
        // 응답 구조가 { message: string, data: BlogContent } 형태인 경우
        setContents([...contents, response.data.data]);
        alert(response.data.message || '콘텐츠가 성공적으로 생성되었습니다.');
      } else {
        // 응답 구조가 직접 콘텐츠 객체인 경우
        setContents([...contents, response.data]);
        alert('콘텐츠가 성공적으로 생성되었습니다.');
      }
      
      // 입력 필드 초기화
      setSelectedKeyword('');
      setBusinessName('');
      setExpertise('');
      setCustomMorphemes('');
      
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
    } finally {
      setLoading(false);
    }
  };

  if (loading && !refreshing) {
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
        <button 
          onClick={loadData}
          disabled={refreshing}
          className={`px-4 py-2 rounded text-white ${refreshing ? 'bg-gray-400' : 'bg-blue-500 hover:bg-blue-600'}`}
        >
          {refreshing ? '새로고침 중...' : '데이터 새로고침'}
        </button>
      </div>
      
      {error && (
        <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4">
          {error}
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
        
        {/* 업체명 입력 필드 (필수) */}
        <div className="mb-4">
          <label className="block text-gray-700 mb-2">
            업체명 <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            className="w-full border rounded p-2"
            placeholder="업체명 또는 서비스명을 입력하세요"
            value={businessName}
            onChange={(e) => setBusinessName(e.target.value)}
            required
          />
        </div>

        {/* 전문성/경력 입력 필드 (필수) */}
        <div className="mb-4">
          <label className="block text-gray-700 mb-2">
            전문성/경력 <span className="text-red-500">*</span>
          </label>
          <textarea
            className="w-full border rounded p-2"
            placeholder="관련 분야의 전문성이나 경력을 입력하세요"
            value={expertise}
            onChange={(e) => setExpertise(e.target.value)}
            rows={3}
            required
          />
        </div>
        
        {/* 형태소 입력 필드 (선택) */}
        <div className="mb-4">
          <label className="block text-gray-700 mb-2">
            추가 형태소 (선택사항)
          </label>
          <input
            type="text"
            className="w-full border rounded p-2"
            placeholder="추가하고 싶은 형태소를 띄어쓰기로 구분하여 입력하세요 (예: 자동차 수리 점검)"
            value={customMorphemes}
            onChange={(e) => setCustomMorphemes(e.target.value)}
          />
          <p className="text-sm text-gray-500 mt-1">
            콘텐츠에 추가로 포함시키고 싶은 핵심 단어나 형태소를 입력하세요.
          </p>
        </div>

        {selectedKeyword && (
          <button 
            onClick={handleContentGeneration}
            disabled={loading || !businessName.trim() || !expertise.trim()}
            className={`text-white px-4 py-2 rounded w-full ${
              loading || !businessName.trim() || !expertise.trim() 
                ? 'bg-gray-400 cursor-not-allowed' 
                : 'bg-green-500 hover:bg-green-600'
            }`}
          >
            {loading ? '콘텐츠 생성 중...' : '콘텐츠 생성 시작'}
          </button>
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
      
      <div className="bg-gray-50 p-4 rounded-lg">
        <p><strong>로드된 키워드 수:</strong> {keywords.length}</p>
        <p><strong>로드된 콘텐츠 수:</strong> {contents.length}</p>
      </div>
    </div>
  );
}

export default ContentManagement;
// src/components/ImageGeneratorWrapper.js
import React, { useState, useEffect, useCallback } from 'react';
import { imageGeneratorService } from '../api/imageGeneratorService';

// 디바운스 함수 정의
const debounce = (func, wait) => {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
};

const ImageGeneratorWrapper = ({ contentId, content }) => {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [subtopics, setSubtopics] = useState([]);
  const [selectedSubtopic, setSelectedSubtopic] = useState(0);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [generationType, setGenerationType] = useState('all');
  const [isFirstLoad, setIsFirstLoad] = useState(true);
  const [timeoutMessage, setTimeoutMessage] = useState(null);
  const [imageLoadStatus, setImageLoadStatus] = useState({});

  // 콘텐츠에서 소제목 추출
  useEffect(() => {
    if (content) {
      const subtopicPattern = /###\s+(.*?)\n/g;
      const matches = [...content.matchAll(subtopicPattern)];
      const extractedSubtopics = matches.map(match => match[1].trim());
      setSubtopics(extractedSubtopics);
    }
  }, [content]);

  // 생성된 이미지 목록 조회 - 메모이제이션
  const loadGeneratedImages = useCallback(async () => {
    // 이미 로딩 중이면 실행하지 않음
    if (loading) return;
    
    try {
      setLoading(true);
      const response = await imageGeneratorService.getGeneratedImages(contentId);
      
      if (response && response.data) {
        // 응답이 배열인지 확인
        const imageData = Array.isArray(response.data) ? response.data : [];
        // 중복 제거 (image 또는 url 기준)
        const uniqueImageData = imageData.filter((item, index, self) => 
          self.findIndex(t => (t.image === item.image) || (t.url === item.url)) === index
        );
        console.log('로드된 이미지 데이터:', uniqueImageData);
        setImages(uniqueImageData);
      } else {
        setImages([]);
      }
    } catch (error) {
      console.error('이미지 로드 실패:', error);
      setError('이미지를 불러오는 중 오류가 발생했습니다: ' + (error.message || '알 수 없는 오류'));
      setImages([]);
    } finally {
      setLoading(false);
      setIsFirstLoad(false);
    }
  }, [contentId, loading]);

  // 디바운스된 이미지 로드 함수
  const debouncedLoadImages = useCallback(
    debounce(() => {
      loadGeneratedImages();
    }, 500),
    [loadGeneratedImages]
  );

  // 초기 이미지 로드
  useEffect(() => {
    if (contentId && isFirstLoad) {
      loadGeneratedImages();
    }
  }, [contentId, loadGeneratedImages, isFirstLoad]);

  // 모든 소제목에 대한 이미지 생성
  const handleGenerateAllImages = async () => {
    if (loading) return;
    
    setLoading(true);
    setError(null);
    setSuccess(null);
    setTimeoutMessage(null);
    setGenerationType('all');

    // 타임아웃 알림 설정 (60초 후)
    const timeoutAlert = setTimeout(() => {
      setTimeoutMessage('이미지 생성이 오래 걸리고 있습니다. 계속 기다려주세요...');
    }, 60000);

    try {
      const response = await imageGeneratorService.generateImagesForContent(contentId);
      
      clearTimeout(timeoutAlert);
      console.log('이미지 생성 응답:', response.data);
      
      if (response && response.data) {
        await loadGeneratedImages();
        setSuccess('모든 소제목에 대한 이미지가 성공적으로 생성되었습니다.');
      } else {
        setError('이미지 생성 결과가 올바른 형식이 아닙니다.');
      }
    } catch (error) {
      clearTimeout(timeoutAlert);
      if (error.message && error.message.includes('timeout')) {
        setError('이미지 생성 시간이 초과되었습니다. 서버에서는 계속 처리 중일 수 있으니 잠시 후 "이미지 새로고침" 버튼을 눌러보세요.');
      } else {
        setError('이미지 생성 중 오류가 발생했습니다: ' + (error.message || '알 수 없는 오류'));
      }
      console.error('이미지 생성 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  // 특정 소제목에 대한 이미지 생성
  const handleGenerateSingleImage = async () => {
    if (loading) return;
    
    setLoading(true);
    setError(null);
    setSuccess(null);
    setTimeoutMessage(null);
    setGenerationType('single');

    // 타임아웃 알림 설정 (60초 후)
    const timeoutAlert = setTimeout(() => {
      setTimeoutMessage('이미지 생성이 오래 걸리고 있습니다. 계속 기다려주세요...');
    }, 60000);

    try {
      const response = await imageGeneratorService.generateImagesForContent(contentId, selectedSubtopic);
      
      clearTimeout(timeoutAlert);
      console.log('단일 이미지 생성 응답:', response.data);
      
      if (response && response.data) {
        await loadGeneratedImages();
        setSuccess('선택한 소제목에 대한 이미지가 성공적으로 생성되었습니다.');
      }
    } catch (error) {
      clearTimeout(timeoutAlert);
      if (error.message && error.message.includes('timeout')) {
        setError('이미지 생성 시간이 초과되었습니다. 서버에서는 계속 처리 중일 수 있으니 잠시 후 "이미지 새로고침" 버튼을 눌러보세요.');
      } else {
        setError('이미지 생성 중 오류가 발생했습니다: ' + (error.message || '알 수 없는 오류'));
      }
      console.error('이미지 생성 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  // 인포그래픽 생성
  const handleGenerateInfographic = async () => {
    if (loading) return;
    
    setLoading(true);
    setError(null);
    setSuccess(null);
    setTimeoutMessage(null);
    setGenerationType('infographic');

    // 타임아웃 알림 설정 (60초 후)
    const timeoutAlert = setTimeout(() => {
      setTimeoutMessage('인포그래픽 생성이 오래 걸리고 있습니다. 계속 기다려주세요...');
    }, 60000);

    try {
      const response = await imageGeneratorService.generateInfographic(contentId, selectedSubtopic);
      
      clearTimeout(timeoutAlert);
      console.log('인포그래픽 생성 응답:', response.data);
      
      if (response && response.data) {
        await loadGeneratedImages(); // 전체 이미지 목록 새로고침
        setSuccess('인포그래픽이 성공적으로 생성되었습니다.');
      }
    } catch (error) {
      clearTimeout(timeoutAlert);
      if (error.message && error.message.includes('timeout')) {
        setError('인포그래픽 생성 시간이 초과되었습니다. 서버에서는 계속 처리 중일 수 있으니 잠시 후 "이미지 새로고침" 버튼을 눌러보세요.');
      } else {
        setError('인포그래픽 생성 중 오류가 발생했습니다: ' + (error.message || '알 수 없는 오류'));
      }
      console.error('인포그래픽 생성 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  // 테스트 목적으로 이미지 데이터 확인
  const checkImageData = () => {
    console.log('현재 이미지 데이터:', images);
    if (Array.isArray(images) && images.length > 0) {
      setSuccess(`현재 ${images.length}개의 이미지가 있습니다. 콘솔에서 데이터를 확인하세요.`);
    } else {
      setError('이미지 데이터가 없거나 배열이 아닙니다.');
    }
  };

  // 이미지 로드 성공 핸들러
  const handleImageLoad = (imageId) => {
    setImageLoadStatus(prev => ({
      ...prev,
      [imageId]: 'loaded'
    }));
    console.log(`이미지 로드 성공: ${imageId}`);
  };

  // 이미지 다운로드 함수
  const handleDownloadImage = (imageUrl, fileName) => {
    // URL이 상대 경로인 경우 절대 경로로 변환
    const fullUrl = imageUrl.startsWith('/') 
      ? `${window.location.origin}${imageUrl}` 
      : imageUrl;
    
    // fetch를 사용하여 이미지를 가져온 후 blob으로 다운로드
    fetch(fullUrl)
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP 오류: ${response.status}`);
        }
        return response.blob();
      })
      .then(blob => {
        const blobUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = fileName || '이미지.png';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(blobUrl); // 메모리 누수 방지
      })
      .catch(err => {
        console.error('이미지 다운로드 실패:', err);
        alert('이미지 다운로드에 실패했습니다. 다시 시도해 주세요.');
      });
  };

  return (
    <div className="bg-white rounded-lg shadow p-6 mt-6">
      <h3 className="text-lg font-medium mb-3">이미지 생성</h3>
      
      {/* 소제목 선택 */}
      {subtopics.length > 0 && (
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            소제목 선택
          </label>
          <select
            value={selectedSubtopic}
            onChange={(e) => setSelectedSubtopic(parseInt(e.target.value))}
            className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
            disabled={loading}
          >
            {subtopics.map((subtopic, index) => (
              <option key={index} value={index}>
                {subtopic}
              </option>
            ))}
          </select>
        </div>
      )}
      
      {/* 버튼 그룹 */}
      <div className="flex flex-wrap gap-3 mb-4">
        <button
          onClick={handleGenerateAllImages}
          disabled={loading}
          className={`px-4 py-2 rounded ${
            loading && generationType === 'all'
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-500 hover:bg-blue-600 text-white'
          }`}
        >
          {loading && generationType === 'all' ? (
            <span className="flex items-center">
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              처리 중...
            </span>
          ) : (
            '모든 소제목 이미지 생성'
          )}
        </button>
        
        <button
          onClick={handleGenerateSingleImage}
          disabled={loading || subtopics.length === 0}
          className={`px-4 py-2 rounded ${
            loading && generationType === 'single'
              ? 'bg-gray-400 cursor-not-allowed'
              : subtopics.length === 0
                ? 'bg-gray-300 cursor-not-allowed'
                : 'bg-green-500 hover:bg-green-600 text-white'
          }`}
        >
          {loading && generationType === 'single' ? (
            <span className="flex items-center">
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              처리 중...
            </span>
          ) : (
            '선택한 소제목 이미지 생성'
          )}
        </button>
        
        <button
          onClick={handleGenerateInfographic}
          disabled={loading || subtopics.length === 0}
          className={`px-4 py-2 rounded ${
            loading && generationType === 'infographic'
              ? 'bg-gray-400 cursor-not-allowed'
              : subtopics.length === 0
                ? 'bg-gray-300 cursor-not-allowed'
                : 'bg-purple-500 hover:bg-purple-600 text-white'
          }`}
        >
          {loading && generationType === 'infographic' ? (
            <span className="flex items-center">
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              처리 중...
            </span>
          ) : (
            '인포그래픽 생성'
          )}
        </button>
        
        <button
          onClick={checkImageData}
          className="px-4 py-2 rounded bg-gray-500 hover:bg-gray-600 text-white"
        >
          이미지 데이터 확인
        </button>
        
        <button
          onClick={debouncedLoadImages}
          disabled={loading}
          className={`px-4 py-2 rounded ${
            loading ? 'bg-gray-400 cursor-not-allowed' : 'bg-yellow-500 hover:bg-yellow-600 text-white'
          }`}
        >
          이미지 새로고침
        </button>
      </div>
      
      {/* 알림 메시지 */}
      {error && (
        <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4">
          {error}
        </div>
      )}
      
      {timeoutMessage && (
        <div className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 mb-4">
          {timeoutMessage}
          <div className="mt-2">
            <span className="inline-block bg-yellow-500 text-white text-xs px-2 py-1 rounded animate-pulse">
              이미지 생성에는 1-3분이 소요될 수 있습니다
            </span>
          </div>
        </div>
      )}
      
      {success && (
        <div className="bg-green-100 border-l-4 border-green-500 text-green-700 p-4 mb-4">
          {success}
          {Array.isArray(images) && images.length > 0 && (
            <p className="mt-2">이미지 {images.length}개가 있습니다. 아래에서 확인하세요.</p>
          )}
        </div>
      )}
      
      {/* 로딩 인디케이터 */}
      {loading && (
        <div className="flex justify-center my-4">
          <div className="animate-pulse flex space-x-4">
            <div className="flex-1 space-y-4 py-1">
              <div className="h-4 bg-gray-200 rounded w-3/4"></div>
              <div className="space-y-2">
                <div className="h-4 bg-gray-200 rounded"></div>
                <div className="h-4 bg-gray-200 rounded w-5/6"></div>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* 생성된 이미지 미리보기 */}
      {Array.isArray(images) && images.length > 0 ? (
        <div className="mt-6">
          <h4 className="text-md font-medium mb-3">생성된 이미지 ({images.length}개)</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {images.map((image, index) => (
              <div key={`${image.id || index}-${image.image || image.url}`} className="border rounded-lg overflow-hidden">
                {/* 이미지에 onError 핸들러 수정 및 onLoad 핸들러 추가 */}
                <img 
                  src={image.url || image.image} 
                  alt={image.alt_text || image.subtopic || '생성된 이미지'}
                  className="w-full h-auto object-cover"
                  loading="lazy"
                  onLoad={() => handleImageLoad(image.id)}
                  onError={(e) => {
                    // 이미 대체 이미지로 변경된 경우 더 이상 시도하지 않음
                    if (e.target.src.includes('data:image')) return;
                    
                    console.error('이미지 로드 오류:', image.url || image.image);
                    // 외부 서비스 대신 데이터 URI 사용
                    e.target.src = 'data:image/svg+xml;charset=UTF-8,%3Csvg%20width%3D%22400%22%20height%3D%22300%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Crect%20width%3D%22400%22%20height%3D%22300%22%20fill%3D%22%23eee%22%2F%3E%3Ctext%20x%3D%22200%22%20y%3D%22150%22%20font-family%3D%22Arial%22%20font-size%3D%2216%22%20text-anchor%3D%22middle%22%20alignment-baseline%3D%22middle%22%20fill%3D%22%23999%22%3E%EC%9D%B4%EB%AF%B8%EC%A7%80%20%EB%A1%9C%EB%93%9C%20%EC%8B%A4%ED%8C%A8%3C%2Ftext%3E%3C%2Fsvg%3E';
                    // 이미지 스타일 추가
                    e.target.style.backgroundColor = '#f0f0f0';
                    e.target.style.border = '1px solid #ddd';
                    
                    // 이미지 로드 상태 업데이트
                    setImageLoadStatus(prev => ({
                      ...prev,
                      [image.id]: 'error'
                    }));
                  }}
                />
                <div className="p-3 bg-gray-50">
                  <div className="flex justify-between items-center">
                    <p className="font-medium text-sm">{image.subtopic || '소제목 정보 없음'}</p>
                    <button
                      onClick={() => handleDownloadImage(image.url || image.image, `${image.subtopic || '이미지'}.png`)}
                      className="text-xs bg-blue-500 hover:bg-blue-600 text-white py-1 px-2 rounded"
                    >
                      다운로드
                    </button>
                  </div>
                  
                  {image.image && (
                    <p className="text-xs text-gray-500 mt-1 truncate">이미지 경로: {image.image}</p>
                  )}
                  
                  {image.is_infographic && (
                    <span className="inline-block bg-purple-100 text-purple-800 text-xs px-2 py-1 rounded mt-1">
                      인포그래픽
                    </span>
                  )}
                  
                  {/* 이미지 로드 상태 표시 */}
                  {imageLoadStatus[image.id] === 'error' && (
                    <p className="text-xs text-red-500 mt-1">이미지 로드 실패</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : !loading && (
        <div className="text-center py-10 text-gray-500">
          <p>생성된 이미지가 없습니다. 위 버튼을 눌러 이미지를 생성해보세요.</p>
          <p className="text-xs mt-2">이미지 생성에는 시간이 다소 소요될 수 있습니다.</p>
        </div>
      )}
    </div>
  );
};

export default ImageGeneratorWrapper;
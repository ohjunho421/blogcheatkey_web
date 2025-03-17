import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { contentService } from '../api/contentService';
import EnhancedCopyButton from '../components/EnhancedCopyButton';
import ShortsScriptGenerator from '../components/ShortsScriptGenerator';
import MobileOptimizedContent from '../components/MobileOptimizedContent';
import ImageGeneratorWrapper from '../components/ImageGeneratorWrapper';

function ContentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [content, setContent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('content'); // 'content', 'images', 'mobile', 'shorts'

  useEffect(() => {
    async function loadContent() {
      if (!id) {
        setError('콘텐츠 ID가 없습니다.');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const response = await contentService.getContent(id);
        if (response && response.data) {
          setContent(response.data);
        } else {
          setError('콘텐츠 데이터를 불러오지 못했습니다.');
        }
      } catch (err) {
        console.error('콘텐츠 로드 실패:', err);
        setError('콘텐츠를 불러오는 중 오류가 발생했습니다.');
      } finally {
        setLoading(false);
      }
    }

    loadContent();
  }, [id]);

  // 콘텐츠에서 참고자료 섹션을 찾아 링크를 활성화하는 함수
  const processContentWithActiveReferences = (htmlContent) => {
    if (!htmlContent) return '';

    // 참고자료 섹션을 찾기 위한 정규식
    const referenceRegex = /(## 참고자료[\s\S]*)/;
    const match = htmlContent.match(referenceRegex);
    
    if (!match) return htmlContent; // 참고자료 섹션이 없으면 원본 반환
    
    const beforeReferences = htmlContent.substring(0, match.index);
    let referencesSection = match[0];
    
    // 마크다운 링크 형식([텍스트](URL))을 HTML 링크로 변환
    referencesSection = referencesSection.replace(
      /\[(.*?)\]\((https?:\/\/[^\s)]+)\)/g, 
      '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline">$1</a>'
    );
    
    return beforeReferences + referencesSection;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-2"></div>
          <p>콘텐츠를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error || !content) {
    return (
      <div className="p-6">
        <div className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 mb-4">
          {error || '콘텐츠를 찾을 수 없습니다.'}
        </div>
        <button
          onClick={() => navigate('/contents')}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          목록으로 돌아가기
        </button>
      </div>
    );
  }

  // 링크 활성화된 콘텐츠 가져오기
  const processedContent = processContentWithActiveReferences(content.content?.replace(/\n/g, '<br>') || '');

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">{content.title}</h1>
        <button
          onClick={() => navigate('/contents')}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          목록으로 돌아가기
        </button>
      </div>
  
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="mb-4">
          <span className="inline-block bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm mr-2">
            키워드: {content.keyword?.keyword || '정보 없음'}
          </span>
          <span className="inline-block bg-gray-100 text-gray-800 px-2 py-1 rounded text-sm">
            작성일: {new Date(content.created_at).toLocaleDateString()}
          </span>
        </div>
        
        {/* 탭 네비게이션 */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-6">
            <button
              onClick={() => setActiveTab('content')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'content'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              콘텐츠
            </button>
            <button
              onClick={() => setActiveTab('mobile')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'mobile'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              모바일 최적화
            </button>
            <button
              onClick={() => setActiveTab('images')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'images'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              이미지 생성
            </button>
            <button
              onClick={() => setActiveTab('shorts')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'shorts'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              쇼츠 스크립트
            </button>
          </nav>
        </div>
        
        {/* 탭 콘텐츠 */}
        <div className="tab-content">
          {/* 콘텐츠 탭 */}
          {activeTab === 'content' && (
            <div className="prose max-w-none">
              <div dangerouslySetInnerHTML={{ __html: processedContent }} />
              
              {/* 복사 버튼 */}
              <div className="mt-6">
                <h3 className="text-lg font-medium mb-3">텍스트 복사</h3>
                <EnhancedCopyButton originalText={content.content || ''} />
              </div>
            </div>
          )}
          
          {/* 모바일 최적화 탭 */}
          {activeTab === 'mobile' && (
            <MobileOptimizedContent 
              content={content.content?.replace(/\n/g, '<br>') || ''}
            />
          )}
          
          {/* 이미지 생성 탭 */}
          {activeTab === 'images' && (
            <ImageGeneratorWrapper 
              contentId={id} 
              content={content.content || ''} 
            />
          )}
          
          {/* 쇼츠 스크립트 탭 */}
          {activeTab === 'shorts' && (
            <ShortsScriptGenerator content={content.content || ''} />
          )}
        </div>
      </div>
    </div>
  );
}

export default ContentDetail;
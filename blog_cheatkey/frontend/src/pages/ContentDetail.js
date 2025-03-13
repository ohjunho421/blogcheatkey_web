// src/pages/ContentDetail.js
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { contentService } from '../api/contentService';

function ContentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [content, setContent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadContent() {
      try {
        setLoading(true);
        const response = await contentService.getContent(id);
        setContent(response.data);
      } catch (err) {
        console.error('콘텐츠 로드 실패:', err);
        setError('콘텐츠를 불러오는 중 오류가 발생했습니다.');
      } finally {
        setLoading(false);
      }
    }

    loadContent();
  }, [id]);

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

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4">
          {error}
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

  if (!content) {
    return (
      <div className="p-6">
        <div className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 mb-4">
          콘텐츠를 찾을 수 없습니다.
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

        <div className="prose max-w-none">
          <div dangerouslySetInnerHTML={{ __html: content.content.replace(/\n/g, '<br>') }} />
        </div>
      </div>
    </div>
  );
}

export default ContentDetail;
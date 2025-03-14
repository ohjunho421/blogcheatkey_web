// src/api/imageGeneratorService.js
import axios from 'axios';

// 백엔드 API 기본 URL 설정 (환경 변수 또는 설정에 따라 조정)
const API_BASE_URL = process.env.REACT_APP_API_URL || '';  // 빈 문자열로 설정하면 상대 경로로 요청됨
const API_URL = `${API_BASE_URL}/api`;

// 인증 토큰 가져오기
const getAuthToken = () => {
  return localStorage.getItem('authToken');
};

// axios 인스턴스 생성
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  }
});

// 요청 인터셉터 설정
apiClient.interceptors.request.use(
  (config) => {
    const token = getAuthToken();
    if (token) {
      config.headers['Authorization'] = `Token ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export const imageGeneratorService = {
  /**
   * 블로그 콘텐츠의 각 소제목별 이미지 생성 요청
   * 
   * @param {number} contentId - 블로그 콘텐츠 ID
   * @returns {Promise} - 응답 객체
   */
  generateImagesForContent: async (contentId) => {
    try {
      // 경로 수정 - 백엔드 API 경로에 맞게 조정
      const response = await apiClient.post(`/images/generate/${contentId}/`);
      return response;
    } catch (error) {
      console.error('이미지 생성 요청 실패:', error);
      console.error('오류 응답 데이터:', error.response?.data);
      throw error;
    }
  },

  /**
   * 특정 소제목에 대한 인포그래픽 생성 요청
   * 
   * @param {number} contentId - 블로그 콘텐츠 ID
   * @param {number} subtopicIndex - 소제목 인덱스 (0부터 시작)
   * @returns {Promise} - 응답 객체
   */
  generateInfographic: async (contentId, subtopicIndex = 0) => {
    try {
      // 경로 수정 - 백엔드 API 경로에 맞게 조정
      const response = await apiClient.post(`/images/infographic/${contentId}/`, {
        subtopic_index: subtopicIndex
      });
      return response;
    } catch (error) {
      console.error('인포그래픽 생성 요청 실패:', error);
      console.error('오류 응답 데이터:', error.response?.data);
      throw error;
    }
  },

  /**
   * 생성된 이미지 목록 조회
   * 
   * @param {number} contentId - 블로그 콘텐츠 ID
   * @returns {Promise} - 응답 객체
   */
  getGeneratedImages: async (contentId) => {
    try {
      // 경로 수정 - 백엔드 API 경로에 맞게 조정
      const response = await apiClient.get(`/images/content/${contentId}/`);
      return response;
    } catch (error) {
      console.error('이미지 목록 조회 실패:', error);
      console.error('오류 응답 데이터:', error.response?.data);
      throw error;
    }
  },
  
  /**
   * API 연결 테스트 (디버깅용)
   */
  testConnection: async () => {
    try {
      // 간단한 GET 요청으로 API 연결 테스트
      const response = await apiClient.get(`/auth/user/`);
      console.log('API 연결 테스트 성공:', response.data);
      return response;
    } catch (error) {
      console.error('API 연결 테스트 실패:', error);
      console.error('오류 응답 데이터:', error.response?.data);
      throw error;
    }
  }
};

export default imageGeneratorService;
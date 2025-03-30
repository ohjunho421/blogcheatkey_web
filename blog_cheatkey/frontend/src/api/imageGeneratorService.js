// src/api/imageGeneratorService.js
import client from './client';

/**
 * 이미지 생성 및 관리를 위한 서비스
 */
export const imageGeneratorService = {
  /**
   * 블로그 콘텐츠의 각 소제목별 이미지 생성 요청
   * 
   * @param {number} contentId - 블로그 콘텐츠 ID
   * @param {number} subtopicIndex - 선택적 소제목 인덱스 (지정 시 해당 소제목만 생성)
   * @returns {Promise} - 응답 객체
   */
  generateImagesForContent: async (contentId, subtopicIndex) => {
    try {
      let url = `/images/generate/${contentId}/`;
      let params = {};
      
      // 특정 소제목 인덱스가 제공된 경우 쿼리 파라미터 추가
      if (subtopicIndex !== undefined) {
        params.subtopic_index = subtopicIndex;
      }
      
      const response = await client.get(url, { params });
      return response;
    } catch (error) {
      // 오류 처리는 인터셉터에서 기록하므로 여기서는 다시 던지기만 함
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
      const response = await client.post(`/images/infographic/${contentId}/`, {
        subtopic_index: subtopicIndex
      });
      return response;
    } catch (error) {
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
      const response = await client.get(`/images/content/${contentId}/`);
      return response;
    } catch (error) {
      throw error;
    }
  },
  
  /**
   * 이미지 삭제
   * 
   * @param {number} imageId - 삭제할 이미지 ID
   * @returns {Promise} - 응답 객체
   */
  deleteImage: async (imageId) => {
    try {
      const response = await client.delete(`/images/${imageId}/`);
      return response;
    } catch (error) {
      throw error;
    }
  },
  
  /**
   * 특정 이미지 상세 정보 조회
   * 
   * @param {number} imageId - 이미지 ID
   * @returns {Promise} - 응답 객체
   */
  getImageDetails: async (imageId) => {
    try {
      const response = await client.get(`/images/${imageId}/`);
      return response;
    } catch (error) {
      throw error;
    }
  }
};

export default imageGeneratorService;
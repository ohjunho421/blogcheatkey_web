// src/api/contentService.js
import client from './client';

export const contentService = {
  getContents: () => client.get('/content/'),
  getContent: (id) => client.get(`/content/${id}/`),
  getContentsByKeyword: (keywordId) => client.get(`/content/?keyword=${keywordId}`),
  createContent: (data) => client.post('/content/generate/', data),
  updateContent: (id, data) => client.put(`/content/${id}/`, data),
  deleteContent: (id) => client.delete(`/content/${id}/`)
};
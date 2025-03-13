// src/api/keywordService.js
import client from './client';


export const keywordService = {
  getKeywords: () => client.get('/key-word/keywords/'),
  getKeyword: (id) => client.get(`/key-word/keywords/${id}/`),
  createKeyword: (data) => client.post('/key-word/keywords/', data),
  updateKeyword: (id, data) => client.put(`/key-word/keywords/${id}/`, data),
  deleteKeyword: (id) => client.delete(`/key-word/keywords/${id}/`),
  analyzeKeyword: (id) => client.post(`/key-word/keywords/${id}/analyze/`),
  suggestSubtopics: (id) => client.post(`/key-word/keywords/${id}/suggest-subtopics/`)
};
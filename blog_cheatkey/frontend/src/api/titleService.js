// src/api/titleService.js
import client from './client';

export const titleService = {
  generateTitles: (data) => client.post('/title/generate/', data),
  getTitles: () => client.get('/title/'),
  getTitle: (id) => client.get(`/title/${id}/`),
  saveTitle: (data) => client.post(`/title/${data.id}/select/`),
  summarize: (data) => client.post('/title/summarize/', data)
};
// src/utils/auth.js
export const getAuthToken = () => {
    return localStorage.getItem('authToken'); // 또는 sessionStorage에서 가져올 수 있음
  };
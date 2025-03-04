// src/App.js
import React from 'react';
import { AuthProvider } from './context/AuthContext';
import AppRouter from './routes';
import './index.css';

function App() {
  return (
    <AuthProvider>
      <AppRouter />
    </AuthProvider>
  );
}

export default App;
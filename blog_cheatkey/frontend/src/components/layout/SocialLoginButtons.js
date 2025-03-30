// src/components/layout/SocialLoginButton.js
import React from 'react';
import { useAuth } from '../../context/AuthContext';

const SocialLoginButton = () => {
  const { socialLogin } = useAuth();

  return (
    <div className="grid grid-cols-2 gap-3">
      <button
        onClick={() => socialLogin('google')}
        type="button"
        className="py-2 px-4 flex justify-center items-center bg-red-600 hover:bg-red-700 text-white w-full rounded-md transition ease-in duration-200"
      >
        Google
      </button>
      
      <button
        onClick={() => socialLogin('facebook')}
        type="button"
        className="py-2 px-4 flex justify-center items-center bg-blue-600 hover:bg-blue-700 text-white w-full rounded-md transition ease-in duration-200"
      >
        Facebook
      </button>
      
      <button
        onClick={() => socialLogin('kakao')}
        type="button"
        className="py-2 px-4 flex justify-center items-center bg-yellow-400 hover:bg-yellow-500 text-black w-full rounded-md transition ease-in duration-200"
      >
        Kakao
      </button>
      
      <button
        onClick={() => socialLogin('naver')}
        type="button"
        className="py-2 px-4 flex justify-center items-center bg-green-600 hover:bg-green-700 text-white w-full rounded-md transition ease-in duration-200"
      >
        Naver
      </button>
    </div>
  );
};

export default SocialLoginButton;
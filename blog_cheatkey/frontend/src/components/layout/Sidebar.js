// src/components/layout/Sidebar.js
import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const Sidebar = () => {
  const location = useLocation();
  
  const isActive = (path) => {
    return location.pathname === path;
  };
  
  const menuItems = [
    { path: '/', name: '대시보드', },
    { path: '/keywords', name: '키워드 관리' },
    { path: '/contents', name: '콘텐츠 관리' },
    { path: '/titles', name: '제목 생성기' },
  ];

  return (
    <aside className="w-64 bg-white shadow-md min-h-screen">
      <div className="p-4">
        <ul className="space-y-2">
          {menuItems.map((item) => (
            <li key={item.path}>
              <Link
                to={item.path}
                className={`block p-2 rounded ${
                  isActive(item.path)
                    ? 'bg-blue-500 text-white'
                    : 'hover:bg-gray-100'
                }`}
              >
                {item.name}
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
};

export default Sidebar;
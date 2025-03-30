// src/components/layout/Sidebar.js
import React from 'react';
import { NavLink } from 'react-router-dom';

const Sidebar = () => {
  const menuItems = [
    { path: '/', name: '메인으로' },
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
              <NavLink
                to={item.path}
                className={({ isActive }) => 
                  `block p-2 rounded ${
                    isActive
                      ? 'bg-blue-500 text-white'
                      : 'hover:bg-gray-100'
                  }`
                }
              >
                {item.name}
              </NavLink>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
};

export default Sidebar;
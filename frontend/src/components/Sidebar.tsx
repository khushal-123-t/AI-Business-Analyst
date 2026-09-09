import React, { useEffect, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, Bot, Database, FileSpreadsheet, 
  Users, Activity, User, LogOut, TrendingUp 
} from 'lucide-react';
import { api } from '../services/api';

export default function Sidebar() {
  const navigate = useNavigate();
  const [userName, setUserName] = useState(() => localStorage.getItem('userName') || 'User');
  const [role, setRole] = useState(() => localStorage.getItem('role') || 'CLIENT');

  useEffect(() => {
    // Listen for custom event when profile name changes
    const handleNameChange = () => {
      setUserName(localStorage.getItem('userName') || 'User');
    };
    window.addEventListener('userNameChanged', handleNameChange);
    return () => window.removeEventListener('userNameChanged', handleNameChange);
  }, []);

  const handleLogout = () => {
    api.logout();
    navigate('/login');
  };

  // Define Navigation Items based on Role
  const adminMenu = [
    { to: '/admin/dashboard', label: 'Platform Dashboard', icon: LayoutDashboard },
    { to: '/admin/clients', label: 'Client Management', icon: Users },
    { to: '/admin/analytics', label: 'Platform Analytics', icon: Activity }
  ];

  const clientMenu = [
    { to: '/client/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/client/data', label: 'My Data', icon: Database },
    { to: '/client/analytics', label: 'Analytics', icon: Activity },
    { to: '/client/insights', label: 'AI Insights', icon: Bot },
    { to: '/client/reports', label: 'Saved Reports', icon: FileSpreadsheet },
    { to: '/client/profile', label: 'My Profile', icon: User }
  ];

  const menuItems = role === 'ADMIN' ? adminMenu : clientMenu;

  return (
    <aside className="w-64 border-r border-slate-800 bg-[#0d121f] flex flex-col h-screen sticky top-0 shrink-0 z-40">
      {/* Brand logo header */}
      <div className="p-6 border-b border-slate-800 flex items-center gap-3">
        <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
          <TrendingUp className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="font-bold text-sm text-slate-100 tracking-wide uppercase">InsightGen</h1>
          <span className="text-[10px] text-slate-400 font-medium">
            {role === 'ADMIN' ? 'Control Console' : 'Enterprise Analytics'}
          </span>
        </div>
      </div>

      {/* Nav Menu Links */}
      <nav className="flex-1 px-4 py-6 space-y-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `w-full flex items-center gap-3 px-4 py-3 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all ${
                  isActive
                    ? 'bg-gradient-to-r from-indigo-600/90 to-violet-600/90 text-white shadow-md shadow-indigo-600/10 font-bold'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/40'
                }`
              }
            >
              <Icon className="h-4.5 w-4.5 shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Profile Footer Panel */}
      <div className="p-4 border-t border-slate-800 bg-[#090d16] flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-xs text-indigo-400 uppercase">
              {userName.slice(0, 2)}
            </div>
            <div>
              <p className="text-xs font-bold text-slate-350 truncate max-w-[120px]">{userName}</p>
              <p className="text-[9px] text-indigo-400 font-bold uppercase tracking-wider">{role}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="p-1.5 text-slate-450 hover:text-rose-450 hover:bg-rose-500/10 rounded transition cursor-pointer"
            title="Log Out"
          >
            <LogOut className="h-4.5 w-4.5" />
          </button>
        </div>
      </div>
    </aside>
  );
}

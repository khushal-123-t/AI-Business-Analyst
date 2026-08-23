import React from 'react';
import { LayoutDashboard, Bot, Database, History, TrendingUp } from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export default function Sidebar({ activeTab, setActiveTab }: SidebarProps) {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'analyst', label: 'AI Business Analyst', icon: Bot },
    { id: 'explorer', label: 'Data Explorer', icon: Database },
    { id: 'history', label: 'Query History', icon: History },
  ];

  return (
    <aside className="w-64 border-r border-slate-800 bg-[#0d121f] flex flex-col h-screen sticky top-0">
      {/* Brand logo header */}
      <div className="p-6 border-b border-slate-800 flex items-center gap-3">
        <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
          <TrendingUp className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="font-bold text-sm text-slate-100 tracking-wide uppercase">InsightGen</h1>
          <span className="text-[10px] text-slate-400 font-medium">Enterprise Analytics</span>
        </div>
      </div>

      {/* Nav Menu */}
      <nav className="flex-1 px-4 py-6 space-y-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-gradient-to-r from-indigo-600/90 to-violet-600/90 text-white shadow-md shadow-indigo-600/10'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/40'
              }`}
            >
              <Icon className={`h-5 w-5 ${isActive ? 'text-white' : 'text-slate-400 group-hover:text-slate-100'}`} />
              {item.label}
            </button>
          );
        })}
      </nav>

      {/* Footer footer */}
      <div className="p-4 border-t border-slate-800 bg-[#090d16]">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-xs text-indigo-400 uppercase">
            AD
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-300">Admin User</p>
            <p className="text-[10px] text-slate-500">Sales Department</p>
          </div>
        </div>
      </div>
    </aside>
  );
}

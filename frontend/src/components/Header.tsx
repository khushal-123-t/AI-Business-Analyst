import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Database, ShieldCheck, RefreshCw } from 'lucide-react';
import { api } from '../services/api';

export default function Header() {
  const [dbConnected, setDbConnected] = useState<boolean>(true);
  const [checking, setChecking] = useState<boolean>(false);
  
  const location = useLocation();

  const getTitle = () => {
    const path = location.pathname;
    if (path.startsWith('/admin/dashboard')) {
      return 'Platform Control Panel';
    } else if (path.startsWith('/admin/clients')) {
      return 'Client Management Hub';
    } else if (path.startsWith('/admin/analytics')) {
      return 'Platform Resource Usage';
    } else if (path.startsWith('/client/dashboard')) {
      return 'Corporate Dashboard';
    } else if (path.startsWith('/client/data')) {
      return 'Relational Datasets Workspace';
    } else if (path.startsWith('/client/analytics')) {
      return 'Executive Business Analytics';
    } else if (path.startsWith('/client/insights')) {
      return 'AI Business Analyst Assistant';
    } else if (path.startsWith('/client/reports')) {
      return 'Saved Business Reports';
    } else if (path.startsWith('/client/profile')) {
      return 'Account Configuration';
    }
    return 'InsightGen Intelligence';
  };

  const checkHealth = async () => {
    setChecking(true);
    try {
      await api.getHealth();
      setDbConnected(true);
    } catch {
      setDbConnected(false);
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    checkHealth();
    // Poll health every 30 seconds
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-20 border-b border-slate-800 bg-[#0d121f]/80 backdrop-blur-md px-8 flex items-center justify-between sticky top-0 z-40 shrink-0">
      <div>
        <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider">{getTitle()}</h2>
        <p className="text-[10px] text-slate-450 font-semibold tracking-wide">Real-time business insights from SQLite warehouse</p>
      </div>

      <div className="flex items-center gap-4">
        {/* Database Connection Status Badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/60 border border-slate-805 text-slate-400">
          <Database className={`h-3.5 w-3.5 ${dbConnected ? 'text-emerald-450' : 'text-rose-450'}`} />
          <span className="text-[10px] font-bold uppercase tracking-wider">business.db</span>
          <div className="relative flex h-1.5 w-1.5">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${dbConnected ? 'bg-emerald-450' : 'bg-rose-450'}`}></span>
            <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${dbConnected ? 'bg-emerald-450' : 'bg-rose-450'}`}></span>
          </div>
        </div>

        {/* Read-Only Safety Badge */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
          <ShieldCheck className="h-3.5 w-3.5" />
          <span className="text-[9px] font-bold uppercase tracking-wider">Read-Only SQL Sandbox</span>
        </div>

        {/* Refresh button */}
        <button
          onClick={checkHealth}
          disabled={checking}
          className="p-2 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800 transition"
          title="Refresh database connection status"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${checking ? 'animate-spin' : ''}`} />
        </button>
      </div>
    </header>
  );
}

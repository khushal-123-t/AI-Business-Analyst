import React, { useEffect, useState } from 'react';
import { Database, ShieldCheck, RefreshCw } from 'lucide-react';
import { api } from '../services/api';

interface HeaderProps {
  activeTab: string;
}

export default function Header({ activeTab }: HeaderProps) {
  const [dbConnected, setDbConnected] = useState<boolean>(true);
  const [checking, setChecking] = useState<boolean>(false);

  const getTitle = () => {
    switch (activeTab) {
      case 'dashboard':
        return 'Executive Sales Dashboard';
      case 'analyst':
        return 'AI Analytics Assistant';
      case 'explorer':
        return 'Database Schema Explorer';
      case 'history':
        return 'Analytical Query Logs';
      default:
        return 'Business intelligence';
    }
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
    <header className="h-20 border-b border-slate-800 bg-[#0d121f]/80 backdrop-blur-md px-8 flex items-center justify-between sticky top-0 z-40">
      <div>
        <h2 className="text-xl font-bold text-slate-100 tracking-tight">{getTitle()}</h2>
        <p className="text-xs text-slate-400 font-medium">Real-time business insights from SQLite warehouse</p>
      </div>

      <div className="flex items-center gap-4">
        {/* Database Connection Badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/60 border border-slate-700/60">
          <Database className={`h-4 w-4 ${dbConnected ? 'text-emerald-400' : 'text-rose-400'}`} />
          <span className="text-xs font-semibold text-slate-300">business.db</span>
          <div className="relative flex h-2 w-2">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${dbConnected ? 'bg-emerald-400' : 'bg-rose-400'}`}></span>
            <span className={`relative inline-flex rounded-full h-2 w-2 ${dbConnected ? 'bg-emerald-400' : 'bg-rose-400'}`}></span>
          </div>
        </div>

        {/* Read-Only Safety Badge */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
          <ShieldCheck className="h-4 w-4" />
          <span className="text-xs font-medium uppercase tracking-wider text-[10px]">Read-Only Mode</span>
        </div>

        {/* Refresh connection status */}
        <button
          onClick={checkHealth}
          disabled={checking}
          className="p-2 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800 transition"
          title="Refresh connection status"
        >
          <RefreshCw className={`h-4 w-4 ${checking ? 'animate-spin' : ''}`} />
        </button>
      </div>
    </header>
  );
}

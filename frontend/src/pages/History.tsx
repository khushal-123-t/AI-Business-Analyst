import React, { useEffect, useState } from 'react';
import { History, Play, Code, Clock, BarChart2, Loader2, AlertCircle, Trash2 } from 'lucide-react';
import { api } from '../services/api';
import type { HistoryItem } from '../types';

interface HistoryProps {
  onSelectQuestion: (question: string) => void;
}

export default function HistoryPage({ onSelectQuestion }: HistoryProps) {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getHistory();
      setHistory(res);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch query logs.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center h-full min-h-[500px]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
          <p className="text-sm text-slate-400 font-semibold">Loading analytical history logs...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 max-w-xl mx-auto my-12 glass-panel rounded-xl border border-rose-500/10 text-center space-y-4">
        <AlertCircle className="h-10 w-10 text-rose-400 mx-auto" />
        <h3 className="font-bold text-slate-100">History Load Error</h3>
        <p className="text-sm text-slate-400 leading-relaxed">{error}</p>
        <button
          onClick={fetchHistory}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold border border-slate-700 transition"
        >
          Retry Load
        </button>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8 overflow-y-auto h-[calc(100vh-80px)] bg-[#0b0f19]">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center gap-2 pb-4 border-b border-slate-800">
          <History className="h-5 w-5 text-indigo-400" />
          <h3 className="text-sm font-bold text-slate-200 tracking-wide uppercase">Analytical Query Logs</h3>
        </div>

        {history.length === 0 ? (
          <div className="glass-panel p-12 rounded-xl text-center border border-slate-800 text-slate-500 space-y-3">
            <Clock className="h-8 w-8 text-slate-600 mx-auto" />
            <p className="text-sm font-semibold">No questions queried yet.</p>
            <p className="text-xs text-slate-600 max-w-xs mx-auto">
              Ask your first query in the AI Business Analyst page to see logs recorded here.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {history.map((item) => (
              <div
                key={item.id}
                className="glass-panel p-6 rounded-xl border border-slate-800/80 hover:border-slate-800 transition flex flex-col md:flex-row md:items-center justify-between gap-6"
              >
                <div className="space-y-3 flex-1 min-w-0">
                  {/* Metadata labels row */}
                  <div className="flex flex-wrap items-center gap-3 text-[10px] text-slate-500 font-semibold uppercase">
                    <span className="flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5" />
                      {item.timestamp}
                    </span>
                    <div className="h-1.5 w-1.5 rounded-full bg-slate-800" />
                    <span className="flex items-center gap-1.5 text-indigo-400">
                      <BarChart2 className="h-3.5 w-3.5" />
                      Visual: {item.chart_type}
                    </span>
                  </div>

                  {/* The User Question */}
                  <h4 className="text-sm font-bold text-slate-200 truncate">{item.question}</h4>

                  {/* SQL Preview code pane */}
                  <div className="p-3 bg-[#080c14] border border-slate-800/60 rounded-lg max-h-24 overflow-y-auto">
                    <pre className="text-[10px] text-indigo-300/80 font-mono leading-relaxed truncate">
                      <code>{item.sql}</code>
                    </pre>
                  </div>
                </div>

                {/* Re-run action buttons */}
                <div className="shrink-0 flex items-center">
                  <button
                    onClick={() => onSelectQuestion(item.question)}
                    className="flex items-center justify-center gap-2 py-2.5 px-4 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-lg text-xs font-bold transition shadow-lg shadow-indigo-600/10"
                  >
                    <Play className="h-3.5 w-3.5" />
                    <span>Run Query Again</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

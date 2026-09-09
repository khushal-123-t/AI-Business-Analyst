import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { AdminDashboardResponse } from '../types';
import { BarChart3, Database, FileSpreadsheet, Activity, Loader2, ShieldAlert } from 'lucide-react';
import ChartsWrapper from '../components/charts/ChartsWrapper';

export default function AdminUsage() {
  const [data, setData] = useState<AdminDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUsage = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getAdminDashboard();
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load usage statistics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsage();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-80px)]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
          <p className="text-sm text-slate-400 font-semibold">Compiling platform analytics...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 max-w-xl mx-auto my-12 glass-panel rounded-xl border border-rose-500/10 text-center space-y-4">
        <ShieldAlert className="h-10 w-10 text-rose-400 mx-auto" />
        <h3 className="font-bold text-slate-100">Analytics Error</h3>
        <p className="text-sm text-slate-400">{error}</p>
        <button
          onClick={fetchUsage}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold border border-slate-700 transition"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  const { client_usage, client_growth } = data;

  return (
    <div className="p-8 space-y-8 overflow-y-auto h-[calc(100vh-80px)]">
      {/* Header Panel */}
      <div>
        <h2 className="text-xl font-bold text-slate-100 tracking-tight">Platform Usage Analytics</h2>
        <p className="text-xs text-slate-400">Monitor tenant growth curves, dataset allocations, query calls, and reports storage</p>
      </div>

      {/* Usage Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Growth Curve */}
        <div className="glass-panel p-6 rounded-xl border border-slate-800/80 space-y-4">
          <div>
            <h3 className="text-sm font-bold text-slate-200 tracking-wide uppercase">Subscriber Acquisition Growth</h3>
            <span className="text-[10px] text-slate-500 font-medium">Growth in number of clients over time</span>
          </div>
          <ChartsWrapper
            chartType="bar"
            xAxis="date"
            yAxis="clients"
            data={client_growth}
            height={260}
          />
        </div>

        {/* Dataset Distribution bar */}
        <div className="glass-panel p-6 rounded-xl border border-slate-800/80 space-y-4">
          <div>
            <h3 className="text-sm font-bold text-slate-200 tracking-wide uppercase">Dataset Allocation</h3>
            <span className="text-[10px] text-slate-500 font-medium">Datasets uploaded by client company</span>
          </div>
          <ChartsWrapper
            chartType="bar"
            xAxis="company"
            yAxis="datasets"
            data={client_usage}
            height={260}
          />
        </div>
      </div>

      {/* Resource Allocation Matrix */}
      <div className="glass-panel p-6 rounded-xl border border-slate-800 space-y-4">
        <div>
          <h3 className="text-sm font-bold text-slate-200 tracking-wide uppercase">Resource Consumption Matrix</h3>
          <span className="text-[10px] text-slate-500 font-medium">Breakdown of storage allocations and LLM api query requests</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 text-[10px] font-bold tracking-wider uppercase">
                <th className="pb-3 pl-4">Company</th>
                <th className="pb-3 text-center">Datasets Uploaded</th>
                <th className="pb-3 text-center">AI Analyst Queries</th>
                <th className="pb-3 text-center">Reports Generated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40 text-xs font-semibold text-slate-300">
              {client_usage.map((usage, idx) => (
                <tr key={idx} className="hover:bg-slate-800/10">
                  <td className="py-4 pl-4 font-bold text-slate-200">{usage.company}</td>
                  <td className="py-4 text-center">
                    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-indigo-500/5 text-indigo-400 border border-indigo-500/10">
                      <Database className="h-3.5 w-3.5" />
                      {usage.datasets}
                    </div>
                  </td>
                  <td className="py-4 text-center">
                    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-500/5 text-emerald-400 border border-emerald-500/10">
                      <Activity className="h-3.5 w-3.5" />
                      {usage.queries}
                    </div>
                  </td>
                  <td className="py-4 text-center">
                    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-sky-500/5 text-sky-400 border border-sky-500/10">
                      <FileSpreadsheet className="h-3.5 w-3.5" />
                      {usage.reports}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

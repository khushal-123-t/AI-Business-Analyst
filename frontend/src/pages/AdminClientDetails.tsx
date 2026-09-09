import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { Client, Dataset, Report } from '../types';
import { 
  ArrowLeft, Users, Database, FileSpreadsheet, Activity, 
  Calendar, ShieldAlert, Loader2, BarChart3
} from 'lucide-react';
import KPICard from '../components/KPICard';

export default function AdminClientDetails() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [client, setClient] = useState<Client | null>(null);
  const [stats, setStats] = useState<any>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDetails = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.getClientDetails(parseInt(id));
      setClient(res.client);
      setStats(res.stats);
      setDatasets(res.datasets);
      setReports(res.reports);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch client details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-80px)]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
          <p className="text-sm text-slate-400 font-semibold">Loading tenant statistics...</p>
        </div>
      </div>
    );
  }

  if (error || !client) {
    return (
      <div className="p-8 max-w-xl mx-auto my-12 glass-panel rounded-xl border border-rose-500/10 text-center space-y-4">
        <ShieldAlert className="h-10 w-10 text-rose-400 mx-auto" />
        <h3 className="font-bold text-slate-100">Error Loading Client</h3>
        <p className="text-sm text-slate-400">{error || 'Client profile not found.'}</p>
        <button
          onClick={() => navigate('/admin/clients')}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold border border-slate-700 transition"
        >
          Back to Clients
        </button>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8 overflow-y-auto h-[calc(100vh-80px)]">
      {/* Header Panel */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/admin/clients')}
          className="p-2 border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded-lg transition"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-slate-100 tracking-tight">{client.company_name}</h2>
            <span className="px-2.5 py-0.5 rounded-full border bg-slate-800/80 border-slate-700 text-[10px] uppercase font-bold text-indigo-400">
              {client.plan} Plan
            </span>
          </div>
          <p className="text-xs text-slate-400">Tenant usage statistics and resource breakdown</p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard
          title="Datasets Uploaded"
          value={stats.datasets_uploaded.toString()}
          icon={Database}
          description="Resource files"
          color="indigo"
        />
        <KPICard
          title="Analyses Executed"
          value={stats.analyses_performed.toString()}
          icon={Activity}
          description="AI analyst triggers"
          color="emerald"
        />
        <KPICard
          title="Reports Saved"
          value={stats.reports_generated.toString()}
          icon={FileSpreadsheet}
          description="Tenant saved documents"
          color="sky"
        />
        <KPICard
          title="Total Rows Processed"
          value={stats.total_rows.toLocaleString()}
          icon={BarChart3}
          description="Data entries storage size"
          color="amber"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Profile Card */}
        <div className="glass-panel p-6 rounded-xl border border-slate-800 space-y-5">
          <div className="border-b border-slate-800/60 pb-3">
            <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Tenant Credentials</h3>
          </div>
          <div className="space-y-4 text-xs font-semibold">
            <div className="flex justify-between">
              <span className="text-slate-500">Contact Person</span>
              <span className="text-slate-300">{client.contact_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Email Address</span>
              <span className="text-slate-300">{client.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Phone Number</span>
              <span className="text-slate-300">{client.phone || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Industry Sector</span>
              <span className="text-slate-300">{client.industry || '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Account Status</span>
              <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold border ${
                client.status === 'ACTIVE'
                  ? 'bg-emerald-500/10 border-emerald-500/25 text-emerald-400'
                  : 'bg-rose-500/10 border-rose-500/25 text-rose-400'
              }`}>
                {client.status}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Created Date</span>
              <span className="text-slate-300">{new Date(client.created_at).toLocaleDateString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Last Active Session</span>
              <span className="text-slate-400">{stats.last_activity}</span>
            </div>
          </div>
        </div>

        {/* Datasets List */}
        <div className="glass-panel p-6 rounded-xl border border-slate-800 lg:col-span-2 space-y-4">
          <div className="border-b border-slate-800/60 pb-3">
            <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Uploaded Datasets</h3>
          </div>
          <div className="overflow-y-auto max-h-[250px] pr-1">
            {datasets.length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-12">No datasets uploaded by this tenant</p>
            ) : (
              <table className="w-full text-left">
                <thead>
                  <tr className="text-[10px] text-slate-500 uppercase tracking-wider font-bold border-b border-slate-800/80 pb-2">
                    <th className="pb-2">Dataset Name</th>
                    <th className="pb-2 text-center">Rows</th>
                    <th className="pb-2 text-center">Cols</th>
                    <th className="pb-2">Uploaded</th>
                  </tr>
                </thead>
                <tbody className="text-xs font-semibold text-slate-300 divide-y divide-slate-800/40">
                  {datasets.map((ds) => (
                    <tr key={ds.id} className="hover:bg-slate-800/10">
                      <td className="py-3 font-bold text-slate-200">{ds.name}</td>
                      <td className="py-3 text-center text-slate-400">{ds.row_count}</td>
                      <td className="py-3 text-center text-slate-400">{ds.col_count}</td>
                      <td className="py-3 text-slate-500">{new Date(ds.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {/* Reports List */}
      <div className="glass-panel p-6 rounded-xl border border-slate-800 space-y-4">
        <div className="border-b border-slate-800/60 pb-3">
          <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Saved Client Reports</h3>
        </div>
        <div>
          {reports.length === 0 ? (
            <p className="text-xs text-slate-500 text-center py-12">No reports saved by this tenant</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="text-[10px] text-slate-500 uppercase tracking-wider font-bold border-b border-slate-800 pb-2">
                    <th className="pb-2 pl-4">Report Name</th>
                    <th className="pb-2">Type</th>
                    <th className="pb-2">Status</th>
                    <th className="pb-2">Created Date</th>
                  </tr>
                </thead>
                <tbody className="text-xs font-semibold text-slate-300 divide-y divide-slate-800/40">
                  {reports.map((rep) => (
                    <tr key={rep.id} className="hover:bg-slate-800/10">
                      <td className="py-3 pl-4 font-bold text-slate-200">{rep.name}</td>
                      <td className="py-3 text-slate-400">{rep.report_type}</td>
                      <td className="py-3">
                        <span className="px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/25 text-[10px] uppercase font-bold text-emerald-400">
                          {rep.status}
                        </span>
                      </td>
                      <td className="py-3 text-slate-500">{new Date(rep.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

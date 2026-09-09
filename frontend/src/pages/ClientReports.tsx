import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { Report } from '../types';
import { 
  FileSpreadsheet, Eye, Download, Trash2, Calendar, 
  X, Loader2, FileText, ShieldAlert
} from 'lucide-react';

export default function ClientReports() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // View Report Modal
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);

  const fetchReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getClientReports();
      setReports(res);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch reports.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleDeleteReport = async (id: number) => {
    if (!confirm('Are you sure you want to delete this saved report?')) {
      return;
    }
    try {
      await api.deleteReport(id);
      fetchReports();
    } catch (err: any) {
      alert(`Error deleting report: ${err.message}`);
    }
  };

  const handleDownloadReport = (rep: Report) => {
    if (!rep.content) return;
    
    // Create markdown download file
    const blob = new Blob([rep.content], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    // Safe filename conversion
    const safeName = rep.name.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    link.setAttribute('download', `${safeName}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Convert markdown-like content to simple HTML paragraphs
  const renderContent = (content: string) => {
    return content.split('\n').map((line, idx) => {
      if (line.startsWith('### ')) {
        return <h4 key={idx} className="text-xs font-bold text-indigo-400 uppercase tracking-wider mt-4 mb-2">{line.replace('### ', '')}</h4>;
      }
      if (line.startsWith('- ')) {
        return <li key={idx} className="ml-4 list-disc text-xs text-slate-350 font-medium leading-relaxed mb-1">{line.replace('- ', '')}</li>;
      }
      if (line.trim() === '') {
        return null;
      }
      return <p key={idx} className="text-xs text-slate-300 leading-relaxed font-semibold mb-2">{line}</p>;
    });
  };

  return (
    <div className="p-8 space-y-8 overflow-y-auto h-[calc(100vh-80px)]">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-100 tracking-tight">Saved Reports</h2>
        <p className="text-xs text-slate-400 font-medium">Access saved AI analyst insights, business impacts, and visual snapshots</p>
      </div>

      {/* Reports Table */}
      <div className="glass-panel rounded-xl border border-slate-800 overflow-hidden">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
            <p className="text-xs text-slate-400 font-semibold">Retrieving documents archive...</p>
          </div>
        ) : reports.length === 0 ? (
          <div className="text-center py-20 space-y-3 max-w-sm mx-auto">
            <FileSpreadsheet className="h-10 w-10 text-slate-700 mx-auto" />
            <div className="space-y-1">
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">No Saved Reports</h3>
              <p className="text-xs text-slate-500 leading-normal">
                No reports saved yet. Ask questions in the 'AI Insights' chat assistant and save analysis outputs.
              </p>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/20 text-slate-400 text-[10px] font-bold tracking-wider uppercase">
                  <th className="py-3.5 pl-5">Report Name</th>
                  <th className="py-3.5">Report Type</th>
                  <th className="py-3.5">Status</th>
                  <th className="py-3.5">Created Date</th>
                  <th className="py-3.5 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40 text-xs font-semibold text-slate-300">
                {reports.map((rep) => (
                  <tr key={rep.id} className="hover:bg-slate-800/10 transition">
                    <td className="py-4 pl-5 font-bold text-slate-200 flex items-center gap-2">
                      <FileText className="h-4 w-4 text-indigo-400 shrink-0" />
                      {rep.name}
                    </td>
                    <td className="py-4 text-slate-400">{rep.report_type}</td>
                    <td className="py-4">
                      <span className="px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/25 text-[10px] font-bold text-emerald-400">
                        {rep.status}
                      </span>
                    </td>
                    <td className="py-4 text-slate-500">
                      {new Date(rep.created_at).toLocaleString()}
                    </td>
                    <td className="py-4 text-center">
                      <div className="flex justify-center items-center gap-2">
                        <button
                          onClick={() => setSelectedReport(rep)}
                          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition"
                          title="View Report"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDownloadReport(rep)}
                          className="p-1.5 text-slate-400 hover:text-indigo-400 hover:bg-indigo-500/10 rounded transition"
                          title="Download Markdown Report"
                        >
                          <Download className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteReport(rep.id)}
                          className="p-1.5 text-slate-500 hover:text-rose-450 hover:bg-rose-500/10 rounded transition"
                          title="Delete Report"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* View Report Overlay Modal */}
      {selectedReport && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-2xl glass-panel border border-slate-800 rounded-2xl overflow-hidden shadow-2xl relative flex flex-col max-h-[85vh]">
            {/* Modal Header */}
            <div className="p-6 border-b border-slate-800 shrink-0 flex justify-between items-start pr-12">
              <div>
                <h3 className="text-sm font-bold text-slate-100 tracking-tight">{selectedReport.name}</h3>
                <span className="text-[10px] text-slate-500 font-semibold uppercase flex items-center gap-1.5 mt-1">
                  <Calendar className="h-3 w-3" />
                  Saved on {new Date(selectedReport.created_at).toLocaleString()}
                </span>
              </div>
              <button
                onClick={() => setSelectedReport(null)}
                className="absolute top-6 right-6 p-1.5 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-850 transition"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Scrollable Content Pane */}
            <div className="p-6 overflow-y-auto space-y-4 flex-1 scrollbar-thin">
              {selectedReport.content ? (
                <div className="bg-slate-900/20 p-5 rounded-xl border border-slate-800/80">
                  {renderContent(selectedReport.content)}
                </div>
              ) : (
                <p className="text-xs text-slate-500 text-center py-10">No report content logged.</p>
              )}
            </div>

            {/* Footer Actions */}
            <div className="p-4 border-t border-slate-800 bg-[#090d16] shrink-0 flex justify-end gap-3">
              <button
                onClick={() => handleDownloadReport(selectedReport)}
                className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-lg text-xs font-semibold shadow-lg flex items-center gap-1.5 transition cursor-pointer"
              >
                <Download className="h-3.5 w-3.5" />
                Download Markdown (.md)
              </button>
              <button
                onClick={() => setSelectedReport(null)}
                className="px-4 py-2 border border-slate-800 hover:bg-slate-800 text-slate-350 rounded-lg text-xs font-semibold transition cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

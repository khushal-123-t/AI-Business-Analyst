import React, { useEffect, useState, useRef } from 'react';
import { api } from '../services/api';
import type { Dataset, LibraryDataset } from '../types';
import { 
  Database, Upload, Trash2, Calendar, FileSpreadsheet,
  AlertTriangle, Loader2, CheckCircle2, ShieldCheck, X,
  FolderDown, Sparkles, Layers, FileText, Check, RefreshCw
} from 'lucide-react';

export default function ClientData() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Upload & Library Modal States
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'upload' | 'library'>('upload');
  
  // Local File Upload States
  const [datasetName, setDatasetName] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [uploadStage, setUploadStage] = useState<'idle' | 'uploading' | 'processing' | 'importing' | 'detecting' | 'ready'>('idle');
  const [uploadPercent, setUploadPercent] = useState<number>(0);
  const [uploadLoaded, setUploadLoaded] = useState<number>(0);
  const [uploadTotal, setUploadTotal] = useState<number>(0);

  // File Input Ref for native file picker dialog and reset
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Library States
  const [libraryDatasets, setLibraryDatasets] = useState<LibraryDataset[]>([]);
  const [libraryLoading, setLibraryLoading] = useState(false);
  const [importingLibId, setImportingLibId] = useState<string | null>(null);
  const [librarySuccess, setLibrarySuccess] = useState<string | null>(null);

  const fetchDatasets = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getClientDatasets();
      setDatasets(res);
      
      // Auto-set first active dataset if none exists in localStorage
      const activeId = localStorage.getItem('activeDatasetId');
      if (!activeId && res.length > 0) {
        const firstActive = res.find((d) => d.status === 'ACTIVE');
        if (firstActive) {
          localStorage.setItem('activeDatasetId', firstActive.id.toString());
          localStorage.setItem('activeDatasetName', firstActive.name);
          window.dispatchEvent(new Event('activeDatasetChanged'));
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch datasets.');
    } finally {
      setLoading(false);
    }
  };

  const fetchLibraryCatalog = async () => {
    setLibraryLoading(true);
    try {
      const res = await api.getLibraryDatasets();
      setLibraryDatasets(res);
    } catch {
      // Fallback local library datasets in case backend endpoint is refreshing
      setLibraryDatasets([
        {
          id: 'retail_sales',
          name: 'Global Retail Sales Warehouse',
          description: '5,000 retail transactions across Electronics, Fashion, Furniture, and Grocery with revenues, profit margins, discounts, and regional data.',
          category: 'Retail & E-Commerce',
          rows: 5000,
          columns: 12,
          filename: 'sales_data.csv'
        },
        {
          id: 'saas_subscriptions',
          name: 'SaaS Subscriptions & ARR Analytics',
          description: '1,200 subscription records tracking Starter, Pro, and Enterprise accounts with MRR, churn status, customer LTV, and support metrics.',
          category: 'SaaS & Subscriptions',
          rows: 1200,
          columns: 10,
          filename: 'saas_mrr_data.csv'
        },
        {
          id: 'marketing_campaigns',
          name: 'Digital Marketing & ROI Performance',
          description: '850 ad campaigns across Search, Social, and Email with impressions, click-through rates, conversions, ad spend, and net ROI.',
          category: 'Marketing & Ads',
          rows: 850,
          columns: 10,
          filename: 'marketing_roi_data.csv'
        }
      ]);
    } finally {
      setLibraryLoading(false);
    }
  };

  useEffect(() => {
    fetchDatasets();
    fetchLibraryCatalog();
  }, []);

  const openUploadModal = () => {
    setActiveTab('upload');
    setDatasetName('');
    setSelectedFile(null);
    setUploadError(null);
    setUploadSuccess(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    setShowUploadModal(true);
  };

  const validateAndSetFile = (file: File) => {
    const validExtensions = /\.(csv|xlsx|xls|tsv|txt|json)$/i;
    if (!validExtensions.test(file.name)) {
      setUploadError('Unsupported file type. Please select a .csv, .xlsx, .xls, .json, .tsv, or .txt file.');
      setSelectedFile(null);
      return false;
    }
    
    // Check for empty file
    if (file.size === 0) {
      setUploadError('The selected file is empty (0 bytes). Please select a file with valid data.');
      setSelectedFile(null);
      return false;
    }

    // Check file size (25MB limit)
    if (file.size > 25 * 1024 * 1024) {
      setUploadError('File exceeds the 25MB size limit.');
      setSelectedFile(null);
      return false;
    }

    setSelectedFile(file);
    setUploadError(null);
    if (!datasetName.trim()) {
      // Auto-fill dataset name with clean file name
      const cleanName = file.name.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ');
      setDatasetName(cleanName.charAt(0).toUpperCase() + cleanName.slice(1));
    }
    return true;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
    // Clear input value so that selecting the same file again triggers onChange
    if (e.target) {
      e.target.value = '';
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!datasetName.trim() || !selectedFile) {
      setUploadError('Please specify a dataset name and select a data file.');
      return;
    }

    setUploadLoading(true);
    setUploadError(null);
    setUploadSuccess(false);
    setUploadStage('uploading');
    setUploadPercent(0);
    setUploadLoaded(0);
    setUploadTotal(selectedFile.size);

    try {
      const newDs = await api.uploadDataset(
        datasetName.trim(), 
        selectedFile,
        (percent, loaded, total) => {
          setUploadPercent(percent);
          setUploadLoaded(loaded);
          setUploadTotal(total);
          if (percent >= 100) {
            setUploadStage('processing');
            setTimeout(() => setUploadStage((prev) => prev === 'processing' ? 'importing' : prev), 300);
            setTimeout(() => setUploadStage((prev) => prev === 'importing' ? 'detecting' : prev), 800);
          }
        }
      );
      setUploadStage('ready');
      setUploadSuccess(true);
      
      // Auto set as active dataset
      localStorage.setItem('activeDatasetId', newDs.id.toString());
      localStorage.setItem('activeDatasetName', newDs.name);
      window.dispatchEvent(new Event('activeDatasetChanged'));
      window.dispatchEvent(new Event('datasetsUpdated'));

      // Immediately refresh dataset list from backend
      await fetchDatasets();

      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }

      setTimeout(() => {
        setShowUploadModal(false);
        setDatasetName('');
        setSelectedFile(null);
        setUploadSuccess(false);
        setUploadStage('idle');
      }, 700);
    } catch (err: any) {
      setUploadError(err.message || 'Upload failed. Please verify format.');
      setUploadStage('idle');
    } finally {
      setUploadLoading(false);
    }
  };

  const handleImportLibraryDataset = async (lib: LibraryDataset) => {
    setImportingLibId(lib.id);
    setUploadError(null);
    try {
      const newDs = await api.importLibraryDataset(lib.id, lib.name);
      setLibrarySuccess(lib.id);
      
      localStorage.setItem('activeDatasetId', newDs.id.toString());
      localStorage.setItem('activeDatasetName', newDs.name);
      window.dispatchEvent(new Event('activeDatasetChanged'));
      window.dispatchEvent(new Event('datasetsUpdated'));

      await fetchDatasets();

      setTimeout(() => {
        setShowUploadModal(false);
        setLibrarySuccess(null);
        setImportingLibId(null);
      }, 350);
    } catch (err: any) {
      setUploadError(err.message || `Failed to import dataset: ${lib.name}`);
      setImportingLibId(null);
    }
  };

  const handleDeleteDataset = async (id: number) => {
    if (!confirm('Are you sure you want to delete this dataset? This will drop the SQL table and clear linked reports.')) {
      return;
    }

    try {
      await api.deleteDataset(id);
      
      const activeId = localStorage.getItem('activeDatasetId');
      if (activeId === id.toString()) {
        localStorage.removeItem('activeDatasetId');
        localStorage.removeItem('activeDatasetName');
        window.dispatchEvent(new Event('activeDatasetChanged'));
      }
      window.dispatchEvent(new Event('datasetsUpdated'));
      fetchDatasets();
    } catch (err: any) {
      alert(`Error deleting dataset: ${err.message}`);
    }
  };

  const selectActiveDataset = (ds: Dataset) => {
    localStorage.setItem('activeDatasetId', ds.id.toString());
    localStorage.setItem('activeDatasetName', ds.name);
    window.dispatchEvent(new Event('activeDatasetChanged'));
    fetchDatasets();
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileExtension = (filename: string) => {
    const ext = filename.split('.').pop();
    return ext ? ext.toUpperCase() : 'FILE';
  };

  const currentActiveId = localStorage.getItem('activeDatasetId');

  return (
    <div className="p-8 space-y-8 overflow-y-auto h-[calc(100vh-80px)]">
      {/* Header Panel */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 tracking-tight">Dataset Explorer</h2>
          <p className="text-xs text-slate-400 font-medium">Select files from your Downloads or computer (.csv, .xlsx, .xls, .json, .tsv, .txt) or load verified library datasets</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setActiveTab('library');
              setUploadError(null);
              setUploadSuccess(false);
              setShowUploadModal(true);
            }}
            className="px-4 py-2.5 bg-slate-800 hover:bg-slate-750 text-slate-200 border border-slate-700/80 rounded-xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer active:scale-98 transition shadow-sm"
          >
            <FolderDown className="h-4 w-4 text-indigo-400" />
            Browse Library
          </button>
          <button
            onClick={openUploadModal}
            className="px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/10 flex items-center gap-1.5 cursor-pointer active:scale-98 transition"
          >
            <Upload className="h-4 w-4" />
            Add New Data
          </button>
        </div>
      </div>

      {/* Dataset Inventory Controls & Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Available Datasets</h3>
            <span className="text-[10px] px-2 py-0.5 bg-slate-800 text-slate-400 rounded-full font-bold">
              {datasets.length} {datasets.length === 1 ? 'dataset' : 'datasets'}
            </span>
          </div>
          <button
            onClick={() => fetchDatasets()}
            disabled={loading}
            className="px-3 py-1.5 bg-slate-800/90 hover:bg-slate-800 text-slate-300 border border-slate-700/70 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer disabled:opacity-50"
            title="Refresh dataset list from database"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
            Refresh
          </button>
        </div>

        <div className="glass-panel rounded-xl border border-slate-800 overflow-hidden">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
              <p className="text-xs text-slate-400 font-semibold">Updating file directories...</p>
            </div>
          ) : datasets.length === 0 ? (
            <div className="text-center py-16 space-y-6 max-w-md mx-auto px-4">
              <div className="h-16 w-16 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center mx-auto text-indigo-400">
                <Database className="h-8 w-8" />
              </div>
              <div className="space-y-1.5">
                <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">No Active Datasets Found</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Select and upload your business data files (.csv, .xlsx, .xls, .json, .tsv, .txt) from your Downloads or import one of our pre-built library datasets.
                </p>
              </div>
              <div className="flex justify-center gap-3 pt-2">
                <button
                  onClick={() => {
                    setActiveTab('library');
                    setShowUploadModal(true);
                  }}
                  className="px-4 py-2 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded-xl text-xs font-semibold flex items-center gap-2 transition cursor-pointer"
                >
                  <FolderDown className="h-4 w-4" />
                  Load Sample from Library
                </button>
                <button
                  onClick={openUploadModal}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center gap-2 transition shadow-lg shadow-indigo-600/15 cursor-pointer"
                >
                  <Upload className="h-4 w-4" />
                  Add New Data
                </button>
              </div>
            </div>
          ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/20 text-slate-400 text-[10px] font-bold tracking-wider uppercase">
                  <th className="py-3.5 pl-5">Status</th>
                  <th className="py-3.5">Dataset Name</th>
                  <th className="py-3.5">Source File</th>
                  <th className="py-3.5 text-center">Row Count</th>
                  <th className="py-3.5 text-center">Col Count</th>
                  <th className="py-3.5">Upload Date</th>
                  <th className="py-3.5 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40 text-xs font-semibold text-slate-300">
                {datasets.map((ds) => {
                  const isActive = currentActiveId === ds.id.toString();
                  const fileExt = getFileExtension(ds.filename);
                  return (
                    <tr 
                      key={ds.id} 
                      className={`hover:bg-slate-800/15 transition cursor-pointer ${isActive ? 'bg-indigo-600/5' : ''}`}
                      onClick={() => selectActiveDataset(ds)}
                    >
                      <td className="py-4 pl-5">
                        {isActive ? (
                          <span className="inline-flex items-center gap-1 text-[10px] uppercase font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/25 px-2 py-0.5 rounded">
                            <ShieldCheck className="h-3 w-3" />
                            Active
                          </span>
                        ) : (
                          <span className="text-[10px] uppercase font-bold text-slate-500 border border-slate-800 px-2 py-0.5 rounded hover:border-slate-700">
                            Switch
                          </span>
                        )}
                      </td>
                      <td className="py-4 font-bold text-slate-200">{ds.name}</td>
                      <td className="py-4 text-slate-400">
                        <div className="flex items-center gap-2">
                          <span className="px-1.5 py-0.5 text-[9px] font-mono font-bold bg-slate-800 text-indigo-400 rounded border border-slate-700/60 shrink-0">
                            {fileExt}
                          </span>
                          <span className="truncate max-w-[180px] text-slate-300">{ds.filename}</span>
                        </div>
                      </td>
                      <td className="py-4 text-center text-slate-300">{ds.row_count.toLocaleString()}</td>
                      <td className="py-4 text-center text-slate-400">{ds.col_count}</td>
                      <td className="py-4 text-slate-500">
                        {new Date(ds.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-4 text-center" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => handleDeleteDataset(ds.id)}
                          className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded transition cursor-pointer"
                          title="Delete Dataset"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
      </div>

      {/* Upload / Library Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-2xl glass-panel border border-slate-800 rounded-2xl overflow-hidden shadow-2xl relative flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="p-6 border-b border-slate-800 flex justify-between items-center bg-[#0e1322]">
              <div>
                <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                  Add Dataset to Workspace
                </h3>
                <p className="text-[11px] text-slate-400">
                  Import data from your Downloads folder or pick a verified library dataset
                </p>
              </div>
              <button
                onClick={() => setShowUploadModal(false)}
                className="p-1.5 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800/80 transition cursor-pointer"
                disabled={uploadLoading || !!importingLibId}
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Modal Tabs */}
            <div className="flex border-b border-slate-800 bg-[#090d16] px-6">
              <button
                onClick={() => {
                  setActiveTab('upload');
                  setUploadError(null);
                }}
                className={`py-3 px-4 text-xs font-semibold border-b-2 flex items-center gap-2 transition cursor-pointer ${
                  activeTab === 'upload'
                    ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Upload className="h-3.5 w-3.5" />
                Upload from Computer (Downloads / Library)
              </button>
              <button
                onClick={() => {
                  setActiveTab('library');
                  setUploadError(null);
                }}
                className={`py-3 px-4 text-xs font-semibold border-b-2 flex items-center gap-2 transition cursor-pointer ${
                  activeTab === 'library'
                    ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <FolderDown className="h-3.5 w-3.5" />
                Sample Datasets Library
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-4">
              {uploadError && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-xl font-medium flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                  <span>{uploadError}</span>
                </div>
              )}

              {/* TAB 1: LOCAL UPLOAD */}
              {activeTab === 'upload' && (
                <form onSubmit={handleUploadSubmit} className="space-y-4">
                  {uploadSuccess && (
                    <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs rounded-xl font-medium flex items-start gap-2">
                      <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
                      <span>New data uploaded successfully. Switching workspace...</span>
                    </div>
                  )}

                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-slate-400 uppercase">Dataset Name *</label>
                    <input
                      type="text"
                      required
                      value={datasetName}
                      onChange={(e) => setDatasetName(e.target.value)}
                      placeholder="e.g. Q3 Sales & Revenue Report"
                      className="w-full px-3.5 py-2.5 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                      disabled={uploadLoading || uploadSuccess}
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-slate-400 uppercase">
                      Select Data File (.csv, .xlsx, .xls, .json, .tsv, .txt) *
                    </label>
                    
                    <div
                      onDragOver={handleDragOver}
                      onDragLeave={handleDragLeave}
                      onDrop={handleDrop}
                      className={`relative border-2 border-dashed rounded-xl p-6 text-center transition flex flex-col items-center justify-center gap-2.5 ${
                        isDragging 
                          ? 'border-indigo-500 bg-indigo-600/10' 
                          : 'border-slate-800 hover:border-indigo-500/40 bg-[#090e17]/50'
                      }`}
                    >
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept=".csv,.xlsx,.xls,.tsv,.txt,.json,text/csv,text/plain,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/tab-separated-values,application/csv,text/x-csv,application/json"
                        onChange={handleFileChange}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                        disabled={uploadLoading || uploadSuccess}
                      />
                      
                      <div className={`h-11 w-11 rounded-full flex items-center justify-center transition ${
                        selectedFile ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-slate-800 text-slate-400'
                      }`}>
                        {selectedFile ? <FileSpreadsheet className="h-5 w-5" /> : <Upload className="h-5 w-5" />}
                      </div>

                      {selectedFile ? (
                        <div className="space-y-1 relative z-20">
                          <p className="text-xs font-bold text-slate-100 flex items-center justify-center gap-1.5">
                            <span className="px-1.5 py-0.5 text-[9px] font-mono bg-indigo-500/20 text-indigo-300 rounded border border-indigo-500/30">
                              {getFileExtension(selectedFile.name)}
                            </span>
                            {selectedFile.name}
                          </p>
                          <p className="text-[10px] text-slate-400">
                            Size: {formatFileSize(selectedFile.size)} • Click or drop another file to replace
                          </p>
                        </div>
                      ) : (
                        <div className="space-y-2 relative z-20">
                          <p className="text-xs font-bold text-slate-200">
                            Drop your file here, or click to open file picker
                          </p>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              fileInputRef.current?.click();
                            }}
                            className="px-3.5 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 transition cursor-pointer"
                          >
                            <FolderDown className="h-3.5 w-3.5" />
                            Choose File from Downloads / Computer
                          </button>
                          <p className="text-[10px] text-slate-500">
                            Supports CSV, Excel (.xlsx, .xls), JSON, TSV, and TXT files up to 25MB
                          </p>
                        </div>
                      )}
                    </div>
                  </div>

                  {uploadLoading && (
                    <div className="p-4 bg-[#0d1220]/90 border border-indigo-500/25 rounded-xl space-y-2.5">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-slate-200 flex items-center gap-2">
                          <Loader2 className="h-3.5 w-3.5 text-indigo-400 animate-spin" />
                          {uploadStage === 'uploading' && `Uploading... ${uploadPercent}%`}
                          {uploadStage === 'processing' && 'Processing dataset...'}
                          {uploadStage === 'importing' && 'Importing data to database...'}
                          {uploadStage === 'detecting' && 'Detecting schema...'}
                          {uploadStage === 'ready' && 'Ready ✓'}
                        </span>
                        <span className="text-[11px] font-mono text-slate-400">
                          {uploadStage === 'uploading' 
                            ? `${formatFileSize(uploadLoaded)} / ${formatFileSize(uploadTotal)}`
                            : 'Optimized bulk insertion'}
                        </span>
                      </div>

                      {/* Real Progress Bar */}
                      <div className="w-full bg-slate-800/80 rounded-full h-2 overflow-hidden">
                        <div 
                          className="bg-gradient-to-r from-indigo-500 to-violet-500 h-2 rounded-full transition-all duration-200"
                          style={{ 
                            width: uploadStage === 'uploading' 
                              ? `${Math.max(5, uploadPercent)}%` 
                              : '100%' 
                          }}
                        />
                      </div>

                      {/* Stage steps indicator */}
                      <div className="grid grid-cols-4 gap-1 text-[10px] pt-1">
                        <div className={`flex items-center gap-1 ${uploadStage === 'uploading' ? 'text-indigo-400 font-bold' : 'text-emerald-400'}`}>
                          <CheckCircle2 className="h-3 w-3" />
                          <span>Uploading</span>
                        </div>
                        <div className={`flex items-center gap-1 ${uploadStage === 'uploading' ? 'text-slate-500' : uploadStage === 'processing' ? 'text-indigo-400 font-bold' : 'text-emerald-400'}`}>
                          {uploadStage === 'uploading' ? <div className="h-2 w-2 rounded-full bg-slate-700" /> : <CheckCircle2 className="h-3 w-3" />}
                          <span>Processing</span>
                        </div>
                        <div className={`flex items-center gap-1 ${['uploading', 'processing'].includes(uploadStage) ? 'text-slate-500' : uploadStage === 'importing' ? 'text-indigo-400 font-bold' : 'text-emerald-400'}`}>
                          {['uploading', 'processing'].includes(uploadStage) ? <div className="h-2 w-2 rounded-full bg-slate-700" /> : <CheckCircle2 className="h-3 w-3" />}
                          <span>Importing</span>
                        </div>
                        <div className={`flex items-center gap-1 ${uploadStage === 'ready' ? 'text-emerald-400' : uploadStage === 'detecting' ? 'text-indigo-400 font-bold' : 'text-slate-500'}`}>
                          {uploadStage === 'ready' ? <CheckCircle2 className="h-3 w-3" /> : <div className="h-2 w-2 rounded-full bg-slate-700" />}
                          <span>Schema</span>
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="pt-4 flex justify-end gap-3 border-t border-slate-800/80">
                    <button
                      type="button"
                      onClick={() => setShowUploadModal(false)}
                      className="px-4 py-2 border border-slate-800 hover:bg-slate-800 text-slate-300 rounded-xl text-xs font-semibold transition cursor-pointer"
                      disabled={uploadLoading || uploadSuccess}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={uploadLoading || uploadSuccess || !selectedFile}
                      className="px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/10 cursor-pointer disabled:opacity-50 flex items-center gap-2"
                    >
                      {uploadLoading ? (
                        <>
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          {uploadStage === 'uploading' ? `Uploading (${uploadPercent}%)` : 'Importing Dataset...'}
                        </>
                      ) : (
                        <>
                          <Upload className="h-3.5 w-3.5" />
                          Upload & Build Table
                        </>
                      )}
                    </button>
                  </div>
                </form>
              )}

              {/* TAB 2: LIBRARY DATASETS */}
              {activeTab === 'library' && (
                <div className="space-y-4">
                  {libraryLoading ? (
                    <div className="flex flex-col items-center justify-center py-12 gap-3">
                      <Loader2 className="h-6 w-6 text-indigo-500 animate-spin" />
                      <p className="text-xs text-slate-400">Loading library datasets...</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 gap-3">
                      {libraryDatasets.map((lib) => {
                        const isImporting = importingLibId === lib.id;
                        const isSuccess = librarySuccess === lib.id;
                        return (
                          <div
                            key={lib.id}
                            className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-indigo-500/30 transition flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
                          >
                            <div className="space-y-1.5 flex-1">
                              <div className="flex items-center gap-2">
                                <h4 className="text-xs font-bold text-slate-100">{lib.name}</h4>
                                <span className="px-2 py-0.5 text-[9px] font-semibold bg-indigo-500/10 text-indigo-400 rounded-full border border-indigo-500/20">
                                  {lib.category}
                                </span>
                              </div>
                              <p className="text-[11px] text-slate-400 leading-relaxed">
                                {lib.description}
                              </p>
                              <div className="flex items-center gap-3 text-[10px] text-slate-500 font-mono">
                                <span>{lib.rows.toLocaleString()} rows</span>
                                <span>•</span>
                                <span>{lib.columns} columns</span>
                                <span>•</span>
                                <span>{lib.filename}</span>
                              </div>
                            </div>

                            <button
                              onClick={() => handleImportLibraryDataset(lib)}
                              disabled={isImporting || isSuccess || !!importingLibId}
                              className={`px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 shrink-0 transition cursor-pointer disabled:opacity-50 ${
                                isSuccess
                                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                  : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/10'
                              }`}
                            >
                              {isImporting ? (
                                <>
                                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                  Importing...
                                </>
                              ) : isSuccess ? (
                                <>
                                  <Check className="h-3.5 w-3.5" />
                                  Imported!
                                </>
                              ) : (
                                <>
                                  <Sparkles className="h-3.5 w-3.5" />
                                  Import Dataset
                                </>
                              )}
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

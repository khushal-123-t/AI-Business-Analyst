import React, { useEffect, useState } from 'react';
import { Database, Table, HelpCircle, Columns, Loader2, AlertCircle } from 'lucide-react';
import { api } from '../services/api';
import type { SchemaResponse, TableInfo } from '../types';
import DataTable from '../components/DataTable';

export default function DataExplorer() {
  const [schema, setSchema] = useState<SchemaResponse | null>(null);
  const [selectedTable, setSelectedTable] = useState<TableInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSchema = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getSchema();
      setSchema(res);
      if (res.tables && res.tables.length > 0) {
        setSelectedTable(res.tables[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to inspect database schema.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchema();
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center h-full min-h-[500px]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
          <p className="text-sm text-slate-400 font-semibold">Inspecting database metadata...</p>
        </div>
      </div>
    );
  }

  if (error || !schema) {
    return (
      <div className="p-8 max-w-xl mx-auto my-12 glass-panel rounded-xl border border-rose-500/10 text-center space-y-4">
        <AlertCircle className="h-10 w-10 text-rose-400 mx-auto" />
        <h3 className="font-bold text-slate-100">Schema Inspection Error</h3>
        <p className="text-sm text-slate-400 leading-relaxed">{error}</p>
        <button
          onClick={fetchSchema}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold border border-slate-700 transition"
        >
          Retry Inspection
        </button>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8 overflow-y-auto h-[calc(100vh-80px)] bg-[#0b0f19]">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Tables list panel (Left 1/4) */}
        <div className="glass-panel p-6 rounded-xl border border-slate-800/80 flex flex-col space-y-6 h-fit">
          <div className="flex items-center gap-2 pb-4 border-b border-slate-800">
            <Database className="h-5 w-5 text-indigo-400" />
            <h3 className="text-sm font-bold text-slate-200 tracking-wide uppercase">Warehouse Tables</h3>
          </div>

          <div className="space-y-2">
            {schema.tables.map((table) => {
              const isSelected = selectedTable?.name === table.name;
              return (
                <button
                  key={table.name}
                  onClick={() => setSelectedTable(table)}
                  className={`w-full flex items-center justify-between p-3.5 rounded-lg text-xs font-semibold border transition ${
                    isSelected
                      ? 'bg-indigo-600/15 border-indigo-500/30 text-indigo-300'
                      : 'bg-transparent border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/30'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Table className="h-4 w-4 shrink-0" />
                    <span>{table.name}</span>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 bg-slate-800 rounded-full text-slate-400">
                    {table.row_count.toLocaleString()} rows
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Selected table structure metadata panel (Right 3/4) */}
        {selectedTable && (
          <div className="lg:col-span-3 space-y-8">
            {/* Table schema structure description grid */}
            <div className="glass-panel p-6 rounded-xl border border-slate-800/80">
              <div className="flex items-center gap-2 pb-4 border-b border-slate-800 mb-6">
                <Columns className="h-5 w-5 text-indigo-400" />
                <h3 className="text-sm font-bold text-slate-200 tracking-wide uppercase">
                  Column Metadata: <span className="text-indigo-400">{selectedTable.name}</span>
                </h3>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {selectedTable.columns.map((col) => (
                  <div
                    key={col.name}
                    className="p-3 bg-slate-900/40 rounded-lg border border-slate-800/80 hover:border-slate-800 transition flex flex-col space-y-1"
                  >
                    <span className="text-xs font-bold text-slate-300 truncate">{col.name}</span>
                    <span className="text-[10px] font-mono text-slate-500 uppercase">{col.type}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Selected table data preview grid */}
            <div>
              <DataTable
                columns={selectedTable.columns.map((c) => c.name)}
                rows={selectedTable.preview}
                title={`Data Preview: ${selectedTable.name} (showing first 10 rows)`}
                pageSize={10}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

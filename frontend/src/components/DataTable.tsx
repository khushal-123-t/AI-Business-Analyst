import React, { useState } from 'react';
import { Search, ChevronLeft, ChevronRight, FileSpreadsheet } from 'lucide-react';

interface DataTableProps {
  columns: string[];
  rows: Record<string, any>[];
  title?: string;
  pageSize?: number;
}

export default function DataTable({ columns, rows, title = 'Query Results', pageSize = 10 }: DataTableProps) {
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);

  if (!rows || rows.length === 0) {
    return (
      <div className="border border-slate-800 bg-[#0d121f]/50 rounded-xl p-8 text-center text-slate-500">
        No records found matching the query results.
      </div>
    );
  }

  // Format cell values logically
  const formatCell = (colName: string, val: any): string => {
    if (val === null || val === undefined) return '-';
    
    const key = colName.toLowerCase();
    
    // Check if column is numeric
    if (typeof val === 'number') {
      if (key.includes('revenue') || key.includes('profit') || key.includes('price') || key.includes('unit_price') || key.includes('value')) {
        return new Intl.NumberFormat('en-IN', {
          style: 'currency',
          currency: 'INR',
          maximumFractionDigits: 0
        }).format(val);
      }
      if (key.includes('discount')) {
        return `${Math.round(val * 100)}%`;
      }
      if (key.includes('quantity') || key.includes('count') || key.includes('order_id') || key.includes('orders') || key.includes('customers')) {
        return val.toLocaleString();
      }
      return val.toString();
    }
    
    return val.toString();
  };

  // Filter rows based on search term
  const filteredRows = rows.filter((row) =>
    columns.some((col) => {
      const cellVal = row[col];
      return cellVal ? cellVal.toString().toLowerCase().includes(searchTerm.toLowerCase()) : false;
    })
  );

  // Pagination logic
  const totalPages = Math.ceil(filteredRows.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedRows = filteredRows.slice(startIndex, startIndex + pageSize);

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  return (
    <div className="border border-slate-800 bg-[#0d121f]/40 rounded-xl overflow-hidden shadow-lg">
      {/* Table toolbar */}
      <div className="px-6 py-4 bg-[#0d121f]/60 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <FileSpreadsheet className="h-5 w-5 text-indigo-400" />
          <h3 className="font-bold text-sm text-slate-200 tracking-wide uppercase">{title}</h3>
          <span className="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full font-medium">
            {filteredRows.length} rows
          </span>
        </div>

        {/* Search input field */}
        <div className="relative max-w-xs w-full">
          <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
            <Search className="h-4 w-4" />
          </span>
          <input
            type="text"
            placeholder="Search within results..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1); // Reset page on search
            }}
            className="w-full bg-[#080b13] border border-slate-700/80 rounded-lg py-1.5 pl-9 pr-4 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-all"
          />
        </div>
      </div>

      {/* Responsive Table Scroll pane */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-[#090d16] border-b border-slate-800/80 text-slate-400 font-semibold uppercase tracking-wider">
              {columns.map((col) => (
                <th key={col} className="px-6 py-3 font-medium">
                  {col.replace(/_/g, ' ')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {paginatedRows.map((row, rowIndex) => (
              <tr key={rowIndex} className="hover:bg-slate-800/10 transition-colors text-slate-300">
                {columns.map((col) => (
                  <td key={col} className="px-6 py-3 font-mono text-slate-300">
                    {formatCell(col, row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Table Pagination Footer */}
      {totalPages > 1 && (
        <div className="px-6 py-4 bg-[#0d121f]/40 border-t border-slate-800 flex items-center justify-between">
          <span className="text-xs text-slate-500">
            Showing <span className="text-slate-400 font-semibold">{startIndex + 1}</span> to{' '}
            <span className="text-slate-400 font-semibold">
              {Math.min(startIndex + pageSize, filteredRows.length)}
            </span>{' '}
            of <span className="text-slate-400 font-semibold">{filteredRows.length}</span> records
          </span>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="p-1.5 rounded-lg border border-slate-700/60 bg-slate-800/50 text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:hover:text-slate-400 transition"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="text-xs font-semibold text-slate-400 px-3">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="p-1.5 rounded-lg border border-slate-700/60 bg-slate-800/50 text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:hover:text-slate-400 transition"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

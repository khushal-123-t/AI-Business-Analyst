import React, { useState } from 'react';
import { Code2, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';

interface SQLViewerProps {
  sql: string;
}

export default function SQLViewer({ sql }: SQLViewerProps) {
  const [expanded, setExpanded] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text', err);
    }
  };

  return (
    <div className="border border-slate-800 bg-[#0d121f]/50 rounded-xl overflow-hidden">
      {/* Header section toggle */}
      <div
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between px-6 py-4 cursor-pointer hover:bg-slate-800/20 transition-all select-none"
      >
        <div className="flex items-center gap-3 text-slate-300 font-semibold text-sm">
          <Code2 className="h-5 w-5 text-indigo-400" />
          <span>View Generated SQL Query</span>
        </div>
        <div className="text-slate-500">
          {expanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
        </div>
      </div>

      {/* Code expansion container */}
      {expanded && (
        <div className="border-t border-slate-800/80 bg-[#090c15] p-6 relative">
          {/* Copy Button */}
          <button
            onClick={handleCopy}
            className="absolute top-4 right-4 p-2 bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-slate-100 rounded-lg border border-slate-700/60 transition flex items-center gap-1.5 text-xs font-semibold"
            title="Copy SQL Query"
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-400" />
                <span className="text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5" />
                <span>Copy</span>
              </>
            )}
          </button>

          {/* Raw pre-formatted SQL */}
          <pre className="text-xs text-indigo-200/90 font-mono overflow-x-auto pt-2 pr-12 max-h-60 leading-relaxed tab-size-4">
            <code>{sql}</code>
          </pre>
        </div>
      )}
    </div>
  );
}

import React, { useEffect, useState } from 'react';
import { Bot, CheckCircle2, Loader2, Circle } from 'lucide-react';

interface LoadingStage {
  id: number;
  label: string;
  subLabel: string;
}

const STAGES: LoadingStage[] = [
  { id: 0, label: 'Understanding your question', subLabel: 'Extracting categories, regions, and dates...' },
  { id: 1, label: 'Generating SQLite query', subLabel: 'Asking Gemini to write optimized SQL...' },
  { id: 2, label: 'Running database analysis', subLabel: 'Executing SQL against sales warehouse...' },
  { id: 3, label: 'Creating visualization', subLabel: 'Auto-mapping fields to charts...' },
  { id: 4, label: 'Generating insights', subLabel: 'Synthesizing executive actions...' },
];

export default function LoadingState() {
  const [currentStage, setCurrentStage] = useState<number>(0);

  useEffect(() => {
    // Stagger through stages to give a premium, thoughtful loading feel
    const interval = setInterval(() => {
      setCurrentStage((prev) => {
        if (prev < STAGES.length - 1) {
          return prev + 1;
        }
        return prev;
      });
    }, 1200);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="glass-panel p-8 rounded-xl max-w-xl mx-auto flex flex-col items-center justify-center space-y-8 my-12 border border-indigo-500/10 shadow-2xl shadow-indigo-950/20">
      <div className="h-16 w-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/25 flex items-center justify-center relative">
        <Bot className="h-8 w-8 text-indigo-400 animate-bounce" />
        <span className="absolute -top-1 -right-1 flex h-4 w-4">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-4 w-4 bg-indigo-500 flex items-center justify-center text-[8px] text-white font-bold">
            i
          </span>
        </span>
      </div>

      <div className="text-center space-y-2">
        <h3 className="text-lg font-bold text-slate-100">AI Analyst is Processing</h3>
        <p className="text-sm text-slate-400 max-w-sm">Generating SQL, parsing datasets, and formulating business recommendations.</p>
      </div>

      <div className="w-full space-y-4 max-w-md">
        {STAGES.map((stage) => {
          const isCompleted = currentStage > stage.id;
          const isCurrent = currentStage === stage.id;
          
          return (
            <div
              key={stage.id}
              className={`flex items-start gap-4 p-3 rounded-lg border transition-all duration-300 ${
                isCurrent
                  ? 'bg-indigo-500/5 border-indigo-500/20 shadow-md'
                  : 'bg-transparent border-transparent'
              }`}
            >
              <div className="mt-0.5">
                {isCompleted ? (
                  <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                ) : isCurrent ? (
                  <Loader2 className="h-5 w-5 text-indigo-400 animate-spin" />
                ) : (
                  <Circle className="h-5 w-5 text-slate-700" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-semibold ${isCurrent ? 'text-indigo-300' : isCompleted ? 'text-slate-300' : 'text-slate-500'}`}>
                  {stage.label}
                </p>
                <p className={`text-xs truncate ${isCurrent ? 'text-indigo-400/80' : 'text-slate-600'}`}>
                  {stage.subLabel}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

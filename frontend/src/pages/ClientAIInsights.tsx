import React, { useState, useRef, useEffect } from 'react';
import { api } from '../services/api';
import type { AskResponse, Dataset } from '../types';
import { 
  Send, Sparkles, Bot, AlertTriangle, ArrowRight, 
  Database, FilePlus, CheckCircle2, Loader2 
} from 'lucide-react';
import LoadingState from '../components/LoadingState';
import SQLViewer from '../components/SQLViewer';
import DataTable from '../components/DataTable';
import ChartsWrapper from '../components/charts/ChartsWrapper';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  response?: AskResponse;
  error?: string;
  reportSaved?: boolean;
}

export default function ClientAIInsights() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | null>(null);
  
  const [question, setQuestion] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId] = useState<string>(() => `session_${Math.random().toString(36).substr(2, 9)}`);
  const [savingReportId, setSavingReportId] = useState<string | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);

  const loadDatasets = async () => {
    try {
      const res = await api.getClientDatasets();
      setDatasets(res);
      
      const storedActiveId = localStorage.getItem('activeDatasetId');
      const targetId = storedActiveId ? parseInt(storedActiveId) : null;
      const matched = res.find((d) => d.id === targetId);
      if (matched && targetId) {
        setSelectedDatasetId(targetId);
      } else if (res.length > 0) {
        const active = res.find((d) => d.status === 'ACTIVE') || res[0];
        if (active) {
          setSelectedDatasetId(active.id);
          localStorage.setItem('activeDatasetId', active.id.toString());
          localStorage.setItem('activeDatasetName', active.name);
        }
      } else {
        setSelectedDatasetId(null);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadDatasets();
    
    const handleActiveChange = () => {
      loadDatasets();
      const storedId = localStorage.getItem('activeDatasetId');
      if (storedId) {
        setSelectedDatasetId(parseInt(storedId));
      } else {
        setSelectedDatasetId(null);
      }
    };

    const handleDatasetsUpdated = () => {
      loadDatasets();
    };

    window.addEventListener('activeDatasetChanged', handleActiveChange);
    window.addEventListener('datasetsUpdated', handleDatasetsUpdated);
    return () => {
      window.removeEventListener('activeDatasetChanged', handleActiveChange);
      window.removeEventListener('datasetsUpdated', handleDatasetsUpdated);
    };
  }, []);

  const handleDatasetSwitch = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = parseInt(e.target.value);
    setSelectedDatasetId(id);
    const dataset = datasets.find((d) => d.id === id);
    if (dataset) {
      localStorage.setItem('activeDatasetId', id.toString());
      localStorage.setItem('activeDatasetName', dataset.name);
      window.dispatchEvent(new Event('activeDatasetChanged'));
    }
  };

  const handleSend = async (textToSend: string) => {
    const qText = textToSend.trim();
    if (!qText || !selectedDatasetId) return;

    const userMsg: ChatMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: qText,
    };

    setMessages((prev) => [...prev, userMsg]);
    setQuestion('');
    setLoading(true);

    try {
      const response = await api.askQuestion({
        question: qText,
        session_id: sessionId,
      }, selectedDatasetId);

      const assistantMsg: ChatMessage = {
        id: `assistant_${Date.now()}`,
        role: 'assistant',
        content: response.summary,
        response: response,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const assistantMsg: ChatMessage = {
        id: `assistant_${Date.now()}`,
        role: 'assistant',
        content: 'I encountered an error while trying to process your question.',
        error: err.message || 'Network error. Ensure backend is running.',
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveReport = async (msg: ChatMessage) => {
    if (!msg.response || !selectedDatasetId) return;
    setSavingReportId(msg.id);
    
    try {
      const title = `AI Analysis: ${msg.response.question.length > 35 ? msg.response.question.slice(0, 35) + '...' : msg.response.question}`;
      
      const content = `
### EXECUTIVE SUMMARY
${msg.response.summary}

### KEY FINDINGS
${msg.response.key_findings.map(f => `- ${f}`).join('\n')}

### BUSINESS IMPACT
${msg.response.business_impact}

### RECOMMENDED ACTIONS
${msg.response.recommendations.map(r => `- ${r}`).join('\n')}

### EXECUTED SQL
\`\`\`sql
${msg.response.sql}
\`\`\`
      `.trim();

      await api.createReport({
        name: title,
        report_type: 'AI Analysis',
        dataset_id: selectedDatasetId,
        content: content
      });

      // Update message status
      setMessages((prev) => 
        prev.map((m) => m.id === msg.id ? { ...m, reportSaved: true } : m)
      );
    } catch (err: any) {
      alert(`Error saving report: ${err.message}`);
    } finally {
      setSavingReportId(null);
    }
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const suggestedQuestions = [
    'What trends do you see in my data?',
    'Which products are performing best?',
    'Who are my most valuable customers?',
    'What region has the highest profit margin?',
    'Give me a summary of total sales.',
    'Which category is lagging in growth?'
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] bg-[#0b0f19]">
      {/* Upper header / dataset select */}
      <div className="h-16 border-b border-slate-800/80 px-8 flex items-center justify-between bg-[#0d121f]/40 backdrop-blur-sm shrink-0 z-30">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-indigo-400" />
          <span className="text-xs font-bold text-slate-300">AI Analytics Assistant</span>
        </div>

        {datasets.length > 0 && (
          <div className="flex items-center gap-2 bg-[#0c111e]/90 border border-slate-800/80 rounded-lg px-3 py-1.5">
            <Database className="h-3.5 w-3.5 text-indigo-400" />
            <select
              value={selectedDatasetId || ''}
              onChange={handleDatasetSwitch}
              className="bg-transparent border-none text-[11px] text-slate-200 focus:outline-none font-bold"
            >
              {datasets.map((ds) => (
                <option key={ds.id} value={ds.id} className="bg-[#0b0f19] text-slate-300">
                  {ds.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-8 space-y-8 min-h-0">
        {datasets.length === 0 ? (
          <div className="max-w-md mx-auto py-20 text-center space-y-4">
            <Database className="h-10 w-10 text-slate-700 mx-auto" />
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">No Dataset Selected</h3>
            <p className="text-xs text-slate-500 leading-normal">
              You must upload a dataset or choose one from the library under 'My Data' before asking AI questions.
            </p>
          </div>
        ) : messages.length === 0 ? (
          /* Splash suggested questions screen */
          <div className="max-w-2xl mx-auto py-12 text-center space-y-8">
            <div className="h-16 w-16 rounded-2xl bg-gradient-to-tr from-indigo-500 to-violet-600 flex items-center justify-center mx-auto shadow-lg shadow-indigo-500/20">
              <Bot className="h-8 w-8 text-white" />
            </div>
            <div className="space-y-3">
              <h2 className="text-lg font-bold text-slate-100 tracking-tight">Ask anything about your uploaded dataset...</h2>
              <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
                Gemini will inspect your custom schemas, execute safe SQLite analytical queries, draw charts, and write business action reports.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-xl mx-auto pt-4 text-left">
              {suggestedQuestions.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(q)}
                  className="p-3 text-xs bg-[#0d1220]/40 hover:bg-[#111728]/60 text-slate-300 hover:text-slate-100 rounded-xl border border-slate-800/80 hover:border-indigo-500/30 transition text-left flex items-center justify-between group cursor-pointer"
                >
                  <span>{q}</span>
                  <ArrowRight className="h-3.5 w-3.5 text-slate-600 group-hover:text-indigo-400 group-hover:translate-x-0.5 transition-all" />
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Chat Bubble Stream */
          <div className="max-w-4xl mx-auto space-y-8">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'assistant' && (
                  <div className="h-9 w-9 rounded-lg bg-slate-850 border border-slate-800 flex items-center justify-center shrink-0">
                    <Bot className="h-5 w-5 text-indigo-400" />
                  </div>
                )}

                <div className={`max-w-3xl space-y-4 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                  {/* Bubble header indicator */}
                  <div className="flex items-center gap-2 text-[10px] text-slate-500 uppercase tracking-wider font-bold">
                    {msg.role === 'user' ? (
                      <>
                        <span>User Query</span>
                        <div className="h-1.5 w-1.5 rounded-full bg-slate-700" />
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-3 w-3 text-indigo-400" />
                        <span className="text-indigo-400">Gemini Analyst</span>
                        <div className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
                      </>
                    )}
                  </div>

                  {/* Main text box */}
                  <div className={`inline-block p-4 rounded-2xl text-sm leading-relaxed border ${
                    msg.role === 'user'
                      ? 'bg-indigo-600/10 border-indigo-500/20 text-indigo-200'
                      : 'bg-[#0d1222] border-slate-800 text-slate-200'
                  }`}>
                    {msg.content}
                  </div>

                  {/* SQL validation or execution errors */}
                  {msg.error && (
                    <div className="p-4 bg-rose-500/5 border border-rose-500/25 text-rose-300 rounded-xl text-xs flex items-start gap-3">
                      <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
                      <div>
                        <p className="font-semibold mb-1">Execution Blocked</p>
                        <p className="opacity-95">{msg.error}</p>
                      </div>
                    </div>
                  )}

                  {/* Rich response payload */}
                  {msg.response && (
                    <div className="space-y-6 pt-2 text-left">
                      {/* SQL script viewer */}
                      {msg.response.sql && <SQLViewer sql={msg.response.sql} />}

                      {/* Chart visualization wrapper */}
                      {msg.response.chart && msg.response.chart.chart_type !== 'none' && (
                        <div className="glass-panel p-6 rounded-xl border border-slate-850">
                          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">
                            Automatic Visualization ({msg.response.chart.chart_type} chart)
                          </h4>
                          <ChartsWrapper
                            chartType={msg.response.chart.chart_type}
                            xAxis={msg.response.chart.x_axis}
                            yAxis={msg.response.chart.y_axis}
                            data={msg.response.chart.data}
                            height={240}
                          />
                        </div>
                      )}

                      {/* Table preview */}
                      {msg.response.rows && msg.response.rows.length > 0 && (
                        <DataTable
                          columns={msg.response.columns}
                          rows={msg.response.rows}
                          title="Query Results Preview"
                          pageSize={5}
                        />
                      )}

                      {/* Report findings cards */}
                      {msg.response.success && (
                        <div className="glass-panel p-6 rounded-xl border border-slate-800 space-y-6 bg-slate-900/10">
                          <div className="flex justify-between items-start border-b border-slate-800/80 pb-3">
                            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Business Impact Analysis</h4>
                            
                            {/* Save Report button */}
                            {msg.reportSaved ? (
                              <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-lg">
                                <CheckCircle2 className="h-3.5 w-3.5" />
                                Saved as Report
                              </span>
                            ) : (
                              <button
                                onClick={() => handleSaveReport(msg)}
                                disabled={savingReportId !== null}
                                className="px-2.5 py-1 border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded-lg text-[10px] font-bold tracking-wide uppercase flex items-center gap-1.5 transition cursor-pointer disabled:opacity-50"
                              >
                                {savingReportId === msg.id ? (
                                  <>
                                    <Loader2 className="h-3 w-3 animate-spin" />
                                    Saving...
                                  </>
                                ) : (
                                  <>
                                    <FilePlus className="h-3.5 w-3.5" />
                                    Save Report
                                  </>
                                )}
                              </button>
                            )}
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Key findings */}
                            <div className="space-y-2">
                              <h5 className="text-xs font-bold text-indigo-400 uppercase tracking-wider">Key Findings</h5>
                              <ul className="list-disc pl-4 space-y-1.5 text-xs text-slate-300 font-medium">
                                {msg.response.key_findings.map((f, i) => (
                                  <li key={i}>{f}</li>
                                ))}
                              </ul>
                            </div>

                            {/* Recommendations */}
                            <div className="space-y-2">
                              <h5 className="text-xs font-bold text-emerald-400 uppercase tracking-wider">Recommendations</h5>
                              <ul className="list-disc pl-4 space-y-1.5 text-xs text-slate-300 font-medium">
                                {msg.response.recommendations.map((r, i) => (
                                  <li key={i}>{r}</li>
                                ))}
                              </ul>
                            </div>
                          </div>

                          {/* Business impact */}
                          <div className="space-y-2 pt-4 border-t border-slate-800/80">
                            <h5 className="text-xs font-bold text-amber-400 uppercase tracking-wider">Business Impact</h5>
                            <p className="text-xs text-slate-300 leading-relaxed font-semibold">
                              {msg.response.business_impact}
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && <LoadingState />}
            <div ref={chatEndRef} />
          </div>
        )}
      </div>

      {/* Input panel block */}
      {datasets.length > 0 && (
        <div className="p-6 border-t border-slate-800/80 bg-[#070a13]/60 backdrop-blur-md shrink-0">
          <div className="max-w-4xl mx-auto flex gap-4">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend(question)}
              placeholder="Ask a question about your active dataset (e.g. 'What is the top category by revenue?')"
              className="flex-1 px-4 py-3 bg-[#0d1222]/80 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/50"
              disabled={loading}
            />
            <button
              onClick={() => handleSend(question)}
              disabled={loading || !question.trim()}
              className="px-5 py-3 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/10 flex items-center gap-1.5 cursor-pointer disabled:opacity-50 disabled:pointer-events-none active:scale-98 transition-all"
            >
              <Send className="h-4 w-4" />
              Analyze
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

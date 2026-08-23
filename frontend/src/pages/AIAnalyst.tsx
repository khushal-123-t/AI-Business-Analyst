import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, Bot, AlertTriangle, HelpCircle, ArrowRight, User } from 'lucide-react';
import { api } from '../services/api';
import type { AskResponse } from '../types';
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
}

interface AIAnalystProps {
  initialQuestion: string | null;
  clearInitialQuestion: () => void;
}

export default function AIAnalyst({ initialQuestion, clearInitialQuestion }: AIAnalystProps) {
  const [question, setQuestion] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  // Use a random UUID or persistent session ID for conversational memory
  const [sessionId] = useState<string>(() => `session_${Math.random().toString(36).substr(2, 9)}`);
  
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-run initial question if passed from history page
  useEffect(() => {
    if (initialQuestion) {
      handleSend(initialQuestion);
      clearInitialQuestion();
    }
  }, [initialQuestion]);

  const suggestedQuestions = [
    'Why did revenue drop in March?',
    'Which category generates the most revenue?',
    'Who are our top customers?',
    'Which region has the highest profit?',
    'Show monthly revenue.',
    'Compare North and South.',
    'Which product is most profitable?',
    'What should we do to improve revenue?',
  ];

  const handleSend = async (textToSend: string) => {
    const qText = textToSend.trim();
    if (!qText) return;

    // Create user message
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
      });

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
        error: err.message || 'Network error or service unavailable. Please check your backend connection.',
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Scroll to the bottom of the chat on new messages
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] bg-[#0b0f19]">
      {/* Messages List Area */}
      <div className="flex-1 overflow-y-auto p-8 space-y-8">
        {messages.length === 0 ? (
          /* Empty Chat Splash Screen */
          <div className="max-w-2xl mx-auto py-12 text-center space-y-8">
            <div className="h-16 w-16 rounded-2xl bg-gradient-to-tr from-indigo-500 to-violet-600 flex items-center justify-center mx-auto shadow-lg shadow-indigo-500/20">
              <Bot className="h-8 w-8 text-white animate-pulse" />
            </div>
            <div className="space-y-3">
              <h2 className="text-xl font-bold text-slate-100 tracking-tight">Ask anything about your business data...</h2>
              <p className="text-sm text-slate-400 max-w-md mx-auto">
                I can write SQLite queries, analyze metrics, draw charts, and offer corporate-level insights on your sales warehouse.
              </p>
            </div>

            {/* Quick Suggestions Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-xl mx-auto pt-4 text-left">
              {suggestedQuestions.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(q)}
                  className="p-3 text-xs bg-slate-900/40 hover:bg-slate-800/60 text-slate-300 hover:text-slate-100 rounded-xl border border-slate-800/80 hover:border-indigo-500/30 transition text-left flex items-center justify-between group"
                >
                  <span>{q}</span>
                  <ArrowRight className="h-3.5 w-3.5 text-slate-600 group-hover:text-indigo-400 group-hover:translate-x-0.5 transition-all" />
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Chat Streams */
          <div className="max-w-4xl mx-auto space-y-8">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="h-9 w-9 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                    <Bot className="h-5 w-5 text-indigo-400" />
                  </div>
                )}

                <div className={`max-w-3xl space-y-4 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                  {/* Message Bubble Header */}
                  <div className="flex items-center gap-2 text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
                    {msg.role === 'user' ? (
                      <>
                        <span>User Query</span>
                        <div className="h-1.5 w-1.5 rounded-full bg-slate-600" />
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-3 w-3 text-indigo-400" />
                        <span className="text-indigo-400">AI Analyst Response</span>
                        <div className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
                      </>
                    )}
                  </div>

                  {/* Text Content */}
                  <div
                    className={`inline-block p-4 rounded-xl text-sm leading-relaxed border ${
                      msg.role === 'user'
                        ? 'bg-indigo-600/10 border-indigo-500/25 text-indigo-200'
                        : 'bg-[#0e1423] border-slate-800 text-slate-200 shadow-lg'
                    }`}
                  >
                    {msg.content}
                  </div>

                  {/* Database execution errors */}
                  {msg.error && (
                    <div className="p-4 bg-rose-500/5 border border-rose-500/20 text-rose-300 rounded-xl text-xs flex items-start gap-3">
                      <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
                      <div>
                        <p className="font-semibold mb-1">Execution Blocked</p>
                        <p className="opacity-90">{msg.error}</p>
                      </div>
                    </div>
                  )}

                  {/* Rich response container (SQL, Table, Chart, Insights) */}
                  {msg.response && (
                    <div className="space-y-6 pt-2">
                      {/* 1. Collapsible SQL query viewer */}
                      {msg.response.sql && (
                        <SQLViewer sql={msg.response.sql} />
                      )}

                      {/* 2. Dynamic visual chart */}
                      {msg.response.chart && msg.response.chart.chart_type !== 'none' && (
                        <div className="glass-panel p-6 rounded-xl border border-slate-800">
                          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">
                            Automatic Visualization ({msg.response.chart.chart_type} chart)
                          </h4>
                          <ChartsWrapper
                            chartType={msg.response.chart.chart_type}
                            xAxis={msg.response.chart.x_axis}
                            yAxis={msg.response.chart.y_axis}
                            data={msg.response.chart.data}
                            height={280}
                          />
                        </div>
                      )}

                      {/* 3. Output Data Table */}
                      {msg.response.columns && msg.response.columns.length > 0 && (
                        <DataTable
                          columns={msg.response.columns}
                          rows={msg.response.rows}
                          title="SQL Query Execution Results"
                          pageSize={6}
                        />
                      )}

                      {/* 4. Structured AI Business Analysis Insights */}
                      {msg.response.success && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          {/* Key Findings Card */}
                          <div className="glass-panel p-6 rounded-xl border border-slate-800 bg-[#0e1423]/50">
                            <h4 className="text-xs font-bold text-indigo-400 uppercase tracking-wider mb-3">
                              Key Findings
                            </h4>
                            <ul className="space-y-2 text-xs text-slate-300">
                              {msg.response.key_findings.map((f, i) => (
                                <li key={i} className="flex items-start gap-2 leading-relaxed">
                                  <span className="text-indigo-500 font-semibold mt-0.5">•</span>
                                  <span>{f}</span>
                                </li>
                              ))}
                            </ul>
                          </div>

                          {/* Business Impact Card */}
                          <div className="glass-panel p-6 rounded-xl border border-slate-800 bg-[#0e1423]/50">
                            <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider mb-3">
                              Business Impact
                            </h4>
                            <p className="text-xs text-slate-300 leading-relaxed">
                              {msg.response.business_impact}
                            </p>
                          </div>

                          {/* Recommended Actions Card */}
                          <div className="glass-panel p-6 rounded-xl border border-slate-800 bg-[#0e1423]/50 md:col-span-2">
                            <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-3">
                              Recommended Actions
                            </h4>
                            <ul className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-slate-300">
                              {msg.response.recommendations.map((rec, i) => (
                                <li key={i} className="flex items-start gap-2 bg-[#080c14]/40 p-2.5 rounded-lg border border-slate-800/80 hover:border-emerald-500/10 transition leading-relaxed">
                                  <span className="text-emerald-500 font-bold mt-0.5">✓</span>
                                  <span>{rec}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {msg.role === 'user' && (
                  <div className="h-9 w-9 rounded-lg bg-indigo-600/10 border border-indigo-500/25 flex items-center justify-center shrink-0">
                    <User className="h-5 w-5 text-indigo-400" />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Thinking loader */}
        {loading && <LoadingState />}
        <div ref={chatEndRef} />
      </div>

      {/* Floating user input panel */}
      <div className="p-6 border-t border-slate-800/80 bg-[#090d16]/90 backdrop-blur-md">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !loading) {
                handleSend(question);
              }
            }}
            placeholder="Ask anything about your business data... (e.g. 'Show revenue by product category')"
            disabled={loading}
            className="flex-1 bg-[#0b0f19] border border-slate-800 rounded-xl py-3.5 px-5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/80 disabled:opacity-50 transition-all font-medium"
          />
          <button
            onClick={() => handleSend(question)}
            disabled={loading || !question.trim()}
            className="h-[46px] px-5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:opacity-40 disabled:pointer-events-none text-white font-bold rounded-xl shadow-lg shadow-indigo-600/15 flex items-center justify-center gap-2 text-sm transition-all"
          >
            <Send className="h-4 w-4" />
            <span>Submit</span>
          </button>
        </div>
      </div>
    </div>
  );
}

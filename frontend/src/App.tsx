import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import AIAnalyst from './pages/AIAnalyst';
import DataExplorer from './pages/DataExplorer';
import HistoryPage from './pages/History';

export default function App() {
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [autoRunQuestion, setAutoRunQuestion] = useState<string | null>(null);

  const handleSelectQuestion = (q: string) => {
    setAutoRunQuestion(q);
    setActiveTab('analyst');
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0b0f19]">
      {/* Navigation Sidebar Panel */}
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      
      {/* Primary Content View Pane */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header activeTab={activeTab} />
        
        <main className="flex-1 overflow-hidden">
          {activeTab === 'dashboard' && <Dashboard />}
          {activeTab === 'analyst' && (
            <AIAnalyst 
              initialQuestion={autoRunQuestion} 
              clearInitialQuestion={() => setAutoRunQuestion(null)} 
            />
          )}
          {activeTab === 'explorer' && <DataExplorer />}
          {activeTab === 'history' && (
            <HistoryPage onSelectQuestion={handleSelectQuestion} />
          )}
        </main>
      </div>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  TrendingUp,
  Brain,
  Sparkles,
  Database,
  BarChart3,
  ShieldCheck,
  Code2,
  FileSpreadsheet,
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  Menu,
  X,
  Layers,
  LineChart,
  PieChart,
  Lock,
  Zap,
  HelpCircle,
  PlayCircle,
  ExternalLink,
  DollarSign,
  Users,
  ShoppingCart,
  ArrowUpRight,
  Terminal,
  FileText
} from 'lucide-react';

export default function LandingPage() {
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeQuestionIdx, setActiveQuestionIdx] = useState(0);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userRole, setUserRole] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const role = localStorage.getItem('role');
    if (token && role && token !== 'undefined' && token !== 'null') {
      setIsAuthenticated(true);
      setUserRole(role);
    }
  }, []);

  const handleDashboardRedirect = () => {
    if (userRole === 'ADMIN') {
      navigate('/admin/dashboard');
    } else {
      navigate('/client/dashboard');
    }
  };

  const sampleQuestions = [
    {
      q: "What are my top-selling products?",
      category: "Product Performance",
      sql: "SELECT product_name, SUM(revenue) AS total_sales, SUM(quantity) AS units_sold\nFROM dataset_sales\nGROUP BY product_name\nORDER BY total_sales DESC LIMIT 5;",
      result: "Top product 'Wireless Noise-Cancelling Headphones' generated $482,900 across 3,210 units, leading sales by 24% over runner-up items.",
      metric: "$482.9K Top Item"
    },
    {
      q: "Which category generated the highest revenue?",
      category: "Category Breakdown",
      sql: "SELECT category, SUM(revenue) AS total_revenue,\n       ROUND(SUM(revenue) * 100.0 / (SELECT SUM(revenue) FROM dataset_sales), 1) AS share_pct\nFROM dataset_sales\nGROUP BY category\nORDER BY total_revenue DESC LIMIT 1;",
      result: "Electronics contributed 43.6% of overall gross revenue ($1.42M), followed by Home & Kitchen ($890K).",
      metric: "43.6% Market Share"
    },
    {
      q: "What trends do you see in my data?",
      category: "Trend Analysis",
      sql: "SELECT strftime('%Y-%m', order_date) AS month, SUM(revenue) AS monthly_sales\nFROM dataset_sales\nGROUP BY month\nORDER BY month ASC;",
      result: "Consistent upward momentum of +18.4% quarter-over-quarter, with peak purchasing concentrated around promotional holiday weekends.",
      metric: "+18.4% QoQ Growth"
    },
    {
      q: "Show me monthly sales performance.",
      category: "Temporal Breakdown",
      sql: "SELECT substr(order_date, 1, 7) AS month,\n       SUM(revenue) AS revenue, COUNT(DISTINCT order_id) AS total_orders\nFROM dataset_sales\nGROUP BY month ORDER BY month DESC LIMIT 6;",
      result: "Last month recorded $324,500 across 1,840 distinct customer transactions, outperforming targets by 11.2%.",
      metric: "1,840 Mo. Orders"
    },
    {
      q: "Which region is performing best?",
      category: "Geographic Distribution",
      sql: "SELECT region, SUM(revenue) AS regional_sales,\n       AVG(order_value) AS avg_basket_size\nFROM dataset_sales\nGROUP BY region ORDER BY regional_sales DESC LIMIT 1;",
      result: "North America generated $1.85M in total volume with an average order value of $245.80, leading all international territories.",
      metric: "$1.85M North America"
    },
    {
      q: "What is my total sales?",
      category: "Macro Aggregation",
      sql: "SELECT SUM(revenue) AS total_sales, COUNT(*) AS total_rows\nFROM dataset_sales;",
      result: "Total commercial sales recorded across all historical transactions reach $32,866,573.74 across 142,850 completed orders.",
      metric: "$32.8M Total Sales"
    }
  ];

  return (
    <div className="min-h-screen bg-[#070a13] text-slate-100 font-sans selection:bg-indigo-500/30 selection:text-indigo-200 relative overflow-x-hidden">
      {/* Background Ambient Glow Gradients */}
      <div className="fixed top-[-15%] left-[-10%] w-[600px] h-[600px] rounded-full bg-indigo-600/10 blur-[140px] pointer-events-none -z-10" />
      <div className="fixed top-[30%] right-[-15%] w-[700px] h-[700px] rounded-full bg-violet-600/10 blur-[160px] pointer-events-none -z-10" />
      <div className="fixed bottom-[-10%] left-[20%] w-[600px] h-[600px] rounded-full bg-cyan-600/10 blur-[150px] pointer-events-none -z-10" />

      {/* ========================================================================= */}
      {/* 1. TOP NAVIGATION BAR */}
      {/* ========================================================================= */}
      <nav className="sticky top-0 z-50 backdrop-blur-xl bg-[#070a13]/80 border-b border-slate-800/60 transition-all duration-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-18 flex items-center justify-between">
          {/* Logo & Project Name */}
          <a href="#hero" className="flex items-center gap-3 group cursor-pointer">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-500 via-indigo-600 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/25 group-hover:scale-105 transition-transform duration-200">
              <TrendingUp className="h-5 w-5 text-white" />
            </div>
            <div>
              <span className="text-lg font-bold tracking-tight text-white flex items-center gap-1.5">
                AI Business Analyst
                <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  SaaS
                </span>
              </span>
              <p className="text-[11px] text-slate-400 font-medium -mt-0.5">Automated Intelligence & SQL Analytics</p>
            </div>
          </a>

          {/* Desktop Navigation Links */}
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-300">
            <a href="#hero" className="hover:text-white transition-colors">Home</a>
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-white transition-colors">How It Works</a>
            <a href="#sample-questions" className="hover:text-white transition-colors">Sample Questions</a>
            <a href="#preview" className="hover:text-white transition-colors">Dashboard Preview</a>
          </div>

          {/* Right Action Buttons */}
          <div className="hidden md:flex items-center gap-3.5">
            {isAuthenticated ? (
              <button
                onClick={handleDashboardRedirect}
                className="px-4 py-2 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 shadow-md shadow-indigo-500/20 flex items-center gap-2 cursor-pointer transition-all hover:scale-[1.02] active:scale-[0.98]"
              >
                <BarChart3 className="h-4 w-4" />
                Go to Dashboard
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            ) : (
              <>
                <button
                  onClick={() => navigate('/login')}
                  className="px-4 py-2 rounded-xl text-sm font-semibold text-slate-300 hover:text-white hover:bg-slate-800/60 border border-transparent hover:border-slate-700/60 transition-all cursor-pointer"
                >
                  Login
                </button>
                <button
                  onClick={() => navigate('/signup')}
                  className="px-4 py-2 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 shadow-lg shadow-indigo-600/20 hover:shadow-indigo-500/30 flex items-center gap-2 cursor-pointer transition-all hover:scale-[1.02] active:scale-[0.98]"
                >
                  Get Started
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden flex items-center">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800/60 transition"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>

        {/* Mobile menu dropdown */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-[#0a0f1d] border-b border-slate-800 px-4 pt-3 pb-6 space-y-3">
            <a
              href="#hero"
              onClick={() => setMobileMenuOpen(false)}
              className="block py-2 text-sm font-medium text-slate-200 hover:text-indigo-400"
            >
              Home
            </a>
            <a
              href="#features"
              onClick={() => setMobileMenuOpen(false)}
              className="block py-2 text-sm font-medium text-slate-200 hover:text-indigo-400"
            >
              Features
            </a>
            <a
              href="#how-it-works"
              onClick={() => setMobileMenuOpen(false)}
              className="block py-2 text-sm font-medium text-slate-200 hover:text-indigo-400"
            >
              How It Works
            </a>
            <a
              href="#sample-questions"
              onClick={() => setMobileMenuOpen(false)}
              className="block py-2 text-sm font-medium text-slate-200 hover:text-indigo-400"
            >
              Sample Questions
            </a>
            <a
              href="#preview"
              onClick={() => setMobileMenuOpen(false)}
              className="block py-2 text-sm font-medium text-slate-200 hover:text-indigo-400"
            >
              Dashboard Preview
            </a>
            <div className="pt-3 border-t border-slate-800/80 flex flex-col gap-2">
              {isAuthenticated ? (
                <button
                  onClick={handleDashboardRedirect}
                  className="w-full py-2.5 rounded-xl text-sm font-semibold text-center text-white bg-indigo-600 hover:bg-indigo-500 transition"
                >
                  Go to Dashboard
                </button>
              ) : (
                <>
                  <button
                    onClick={() => navigate('/login')}
                    className="w-full py-2.5 rounded-xl text-sm font-semibold text-center text-slate-200 bg-slate-800/80 hover:bg-slate-700/80 transition"
                  >
                    Login
                  </button>
                  <button
                    onClick={() => navigate('/signup')}
                    className="w-full py-2.5 rounded-xl text-sm font-semibold text-center text-white bg-gradient-to-r from-indigo-600 to-violet-600 transition"
                  >
                    Get Started
                  </button>
                </>
              )}
            </div>
          </div>
        )}
      </nav>

      {/* ========================================================================= */}
      {/* 2. HERO SECTION */}
      {/* ========================================================================= */}
      <section id="hero" className="relative pt-12 pb-20 md:pt-20 md:pb-32 overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto space-y-6">
            {/* Pill Announcement */}
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold backdrop-blur-md">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              Powered by Google Gemini & Instant SQLite Translation
            </div>

            {/* Main Headline */}
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.15]">
              Turn Your Business Data Into{' '}
              <span className="bg-gradient-to-r from-indigo-400 via-violet-300 to-cyan-400 bg-clip-text text-transparent">
                Smarter Decisions
              </span>
            </h1>

            {/* Supporting Text */}
            <p className="text-base sm:text-lg text-slate-300 leading-relaxed max-w-2xl mx-auto">
              An AI-powered Business Analyst that transforms your business data into meaningful insights,
              interactive dashboards, SQL analytics and actionable recommendations.
            </p>

            {/* Hero CTAs */}
            <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3.5">
              <button
                onClick={() => navigate('/signup')}
                className="w-full sm:w-auto px-8 py-3.5 rounded-xl text-base font-semibold text-white bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 shadow-xl shadow-indigo-600/25 hover:shadow-indigo-500/40 active:scale-[0.98] transition-all flex items-center justify-center gap-2.5 cursor-pointer"
              >
                Get Started
                <ArrowRight className="h-4 w-4" />
              </button>
              <button
                onClick={() => navigate('/login')}
                className="w-full sm:w-auto px-8 py-3.5 rounded-xl text-base font-semibold text-slate-200 bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/80 hover:border-slate-600 transition-all flex items-center justify-center gap-2 cursor-pointer"
              >
                <Lock className="h-4 w-4 text-slate-400" />
                Login
              </button>
            </div>

            {/* Hero Trust Micro-Features */}
            <div className="pt-4 flex flex-wrap items-center justify-center gap-y-2 gap-x-6 text-xs text-slate-400">
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                No credit card required
              </span>
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                Instant CSV & Excel upload
              </span>
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                Isolated multi-tenant security
              </span>
            </div>
          </div>

          {/* Hero Visual: Interactive Mockup Displaying Sales, Revenue, Growth, Customers */}
          <div className="mt-14 max-w-5xl mx-auto">
            <div className="glass-panel p-2 sm:p-4 rounded-2xl border border-slate-800 shadow-2xl shadow-indigo-950/40 relative">
              {/* Top Window Bar */}
              <div className="flex items-center justify-between px-3 py-2 border-b border-slate-800/80 mb-4 text-xs text-slate-400">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-rose-500/80" />
                    <span className="h-2.5 w-2.5 rounded-full bg-amber-500/80" />
                    <span className="h-2.5 w-2.5 rounded-full bg-emerald-500/80" />
                  </div>
                  <span className="text-[11px] font-mono text-slate-500 ml-2">app.aianalyst.com/analytics</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    <Database className="h-2.5 w-2.5" />
                    Dataset: Retail_Sales_Q3.csv (Demo)
                  </span>
                </div>
              </div>

              {/* Mockup KPIs */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                <div className="bg-[#0b101e] p-3.5 rounded-xl border border-slate-800/90">
                  <div className="flex justify-between items-start text-xs text-slate-400">
                    <span>Total Sales</span>
                    <span className="text-emerald-400 font-semibold flex items-center text-[10px]">
                      +18.4%
                      <ArrowUpRight className="h-3 w-3" />
                    </span>
                  </div>
                  <div className="text-xl font-bold text-white mt-1">$32,866,573</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Full fiscal period revenue</div>
                </div>

                <div className="bg-[#0b101e] p-3.5 rounded-xl border border-slate-800/90">
                  <div className="flex justify-between items-start text-xs text-slate-400">
                    <span>Total Orders</span>
                    <span className="text-emerald-400 font-semibold flex items-center text-[10px]">
                      +12.1%
                      <ArrowUpRight className="h-3 w-3" />
                    </span>
                  </div>
                  <div className="text-xl font-bold text-white mt-1">142,850</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Processed transactions</div>
                </div>

                <div className="bg-[#0b101e] p-3.5 rounded-xl border border-slate-800/90">
                  <div className="flex justify-between items-start text-xs text-slate-400">
                    <span>Active Customers</span>
                    <span className="text-indigo-400 font-semibold flex items-center text-[10px]">
                      +9.7%
                      <ArrowUpRight className="h-3 w-3" />
                    </span>
                  </div>
                  <div className="text-xl font-bold text-white mt-1">38,420</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Verified purchasers</div>
                </div>

                <div className="bg-[#0b101e] p-3.5 rounded-xl border border-slate-800/90">
                  <div className="flex justify-between items-start text-xs text-slate-400">
                    <span>Avg Order Value</span>
                    <span className="text-emerald-400 font-semibold flex items-center text-[10px]">
                      +5.2%
                      <ArrowUpRight className="h-3 w-3" />
                    </span>
                  </div>
                  <div className="text-xl font-bold text-white mt-1">$230.10</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Basket average size</div>
                </div>
              </div>

              {/* Mockup Charts + Gemini Prompt Interaction */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {/* Sales & Growth Trends Graphic */}
                <div className="lg:col-span-2 bg-[#0b101e] p-4 rounded-xl border border-slate-800/90 flex flex-col justify-between">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h4 className="text-sm font-semibold text-white">Monthly Sales & Revenue Growth</h4>
                      <p className="text-[11px] text-slate-400">Dynamic SQL aggregation: 24-month historical trend</p>
                    </div>
                    <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-medium">
                      +28% High Season
                    </span>
                  </div>

                  {/* Visual Bar Trend Demo */}
                  <div className="h-36 w-full flex items-end gap-2 pt-4 px-2 border-b border-slate-800/60 pb-2">
                    {[
                      { m: 'Jan', h: '45%' }, { m: 'Feb', h: '52%' }, { m: 'Mar', h: '60%' },
                      { m: 'Apr', h: '58%' }, { m: 'May', h: '68%' }, { m: 'Jun', h: '75%' },
                      { m: 'Jul', h: '70%' }, { m: 'Aug', h: '82%' }, { m: 'Sep', h: '88%' },
                      { m: 'Oct', h: '80%' }, { m: 'Nov', h: '94%' }, { m: 'Dec', h: '100%' }
                    ].map((bar, i) => (
                      <div key={i} className="flex-1 flex flex-col items-center gap-1.5 group">
                        <div className="w-full bg-slate-800 rounded-t h-full flex items-end">
                          <div
                            style={{ height: bar.h }}
                            className="w-full bg-gradient-to-t from-indigo-600 via-indigo-500 to-violet-400 rounded-t group-hover:brightness-125 transition-all duration-300"
                          />
                        </div>
                        <span className="text-[9px] text-slate-500">{bar.m}</span>
                      </div>
                    ))}
                  </div>

                  <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
                    <span className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-indigo-500" />
                      Monthly Revenue Volume
                    </span>
                    <span className="text-[11px] text-slate-500">Sample Demonstration Dataset</span>
                  </div>
                </div>

                {/* Gemini AI Live Prompt Simulation Box */}
                <div className="bg-gradient-to-b from-[#0f172a] to-[#0b101e] p-4 rounded-xl border border-indigo-500/30 flex flex-col justify-between shadow-lg">
                  <div>
                    <div className="flex items-center gap-2 text-indigo-300 text-xs font-bold mb-2.5">
                      <Sparkles className="h-4 w-4 text-indigo-400" />
                      Gemini Natural Language Q&A
                    </div>
                    <div className="p-2.5 bg-slate-900/90 rounded-lg border border-slate-800 text-xs text-slate-300 font-medium mb-3">
                      "What are my top product categories by total sales?"
                    </div>

                    <div className="space-y-2">
                      <div className="text-[10px] uppercase font-mono tracking-wider text-slate-500 flex items-center gap-1">
                        <Terminal className="h-3 w-3" />
                        Generated SQL Query
                      </div>
                      <pre className="text-[10px] font-mono p-2 bg-[#060912] rounded-md border border-slate-800/80 text-emerald-400 overflow-x-auto">
                        SELECT category, SUM(revenue){'\n'}FROM dataset_client_4{'\n'}GROUP BY category{'\n'}ORDER BY 2 DESC;
                      </pre>
                    </div>
                  </div>

                  <div className="mt-3 pt-3 border-t border-slate-800 text-xs text-slate-300">
                    <span className="font-semibold text-white">AI Executive Summary:</span>
                    <p className="text-[11px] text-slate-400 mt-1 leading-snug">
                      Electronics generated $1.42M (43.6%), followed by Home & Kitchen ($890K). 2 categories represent 71% of gross revenue.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 3. TRUST & VALUE STATEMENT */}
      {/* ========================================================================= */}
      <section className="py-14 border-y border-slate-800/80 bg-slate-900/30">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-6">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
            "From raw data to business decisions — in minutes."
          </h2>
          <p className="text-sm sm:text-base text-slate-300 max-w-3xl mx-auto leading-relaxed">
            Eliminate complex SQL queries, static spreadsheets, and reporting delays. Upload your custom business datasets
            and simply talk to your data using normal conversational English.
          </p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4">
            <div className="p-4 rounded-xl glass-panel border border-slate-800 text-center">
              <div className="text-xl font-bold text-indigo-400">Zero SQL</div>
              <div className="text-xs text-slate-400 mt-0.5">Plain English Queries</div>
            </div>
            <div className="p-4 rounded-xl glass-panel border border-slate-800 text-center">
              <div className="text-xl font-bold text-violet-400">Google Gemini</div>
              <div className="text-xs text-slate-400 mt-0.5">Schema-Aware Translation</div>
            </div>
            <div className="p-4 rounded-xl glass-panel border border-slate-800 text-center">
              <div className="text-xl font-bold text-cyan-400">100% Isolated</div>
              <div className="text-xs text-slate-400 mt-0.5">Client Multi-Tenancy</div>
            </div>
            <div className="p-4 rounded-xl glass-panel border border-slate-800 text-center">
              <div className="text-xl font-bold text-emerald-400">Real-Time</div>
              <div className="text-xs text-slate-400 mt-0.5">Interactive Visualizations</div>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 4. FEATURES SECTION (6 CARDS) */}
      {/* ========================================================================= */}
      <section id="features" className="py-20 md:py-28 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16 space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-indigo-400">Core Capabilities</h2>
            <h3 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Everything You Need To Understand Your Business Data
            </h3>
            <p className="text-slate-400 text-sm sm:text-base">
              Engineered with advanced language model technology and automated analytics pipelines.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* FEATURE 1 */}
            <div className="glass-card glass-card-hover p-6 rounded-2xl border border-slate-800 relative group flex flex-col justify-between">
              <div>
                <div className="h-12 w-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-5 group-hover:bg-indigo-500/20 group-hover:scale-105 transition-all">
                  <Database className="h-6 w-6" />
                </div>
                <h4 className="text-lg font-bold text-white mb-2">Intelligent Data Analysis</h4>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Upload CSV or Excel datasets and automatically understand your business data, structure and key metrics.
                </p>
              </div>
              <div className="pt-4 text-xs font-semibold text-indigo-400 flex items-center gap-1">
                Automatic schema mapping <ArrowRight className="h-3 w-3" />
              </div>
            </div>

            {/* FEATURE 2 */}
            <div className="glass-card glass-card-hover p-6 rounded-2xl border border-slate-800 relative group flex flex-col justify-between">
              <div>
                <div className="h-12 w-12 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400 mb-5 group-hover:bg-violet-500/20 group-hover:scale-105 transition-all">
                  <Brain className="h-6 w-6" />
                </div>
                <h4 className="text-lg font-bold text-white mb-2">AI Business Analyst</h4>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Ask questions about your business data using natural language instead of manually writing complex queries.
                </p>
              </div>
              <div className="pt-4 text-xs font-semibold text-violet-400 flex items-center gap-1">
                Conversational BI analyst <ArrowRight className="h-3 w-3" />
              </div>
            </div>

            {/* FEATURE 3 */}
            <div className="glass-card glass-card-hover p-6 rounded-2xl border border-slate-800 relative group flex flex-col justify-between">
              <div>
                <div className="h-12 w-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 mb-5 group-hover:bg-cyan-500/20 group-hover:scale-105 transition-all">
                  <Code2 className="h-6 w-6" />
                </div>
                <h4 className="text-lg font-bold text-white mb-2">Natural Language to SQL</h4>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Gemini converts your business questions into SQL queries using the actual schema of your selected dataset.
                </p>
              </div>
              <div className="pt-4 text-xs font-semibold text-cyan-400 flex items-center gap-1">
                Safe read-only execution <ArrowRight className="h-3 w-3" />
              </div>
            </div>

            {/* FEATURE 4 */}
            <div className="glass-card glass-card-hover p-6 rounded-2xl border border-slate-800 relative group flex flex-col justify-between">
              <div>
                <div className="h-12 w-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-5 group-hover:bg-emerald-500/20 group-hover:scale-105 transition-all">
                  <BarChart3 className="h-6 w-6" />
                </div>
                <h4 className="text-lg font-bold text-white mb-2">Interactive Dashboards</h4>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Transform your data into clear KPIs, charts, trends and interactive visualizations.
                </p>
              </div>
              <div className="pt-4 text-xs font-semibold text-emerald-400 flex items-center gap-1">
                Responsive chart configs <ArrowRight className="h-3 w-3" />
              </div>
            </div>

            {/* FEATURE 5 */}
            <div className="glass-card glass-card-hover p-6 rounded-2xl border border-slate-800 relative group flex flex-col justify-between">
              <div>
                <div className="h-12 w-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 mb-5 group-hover:bg-amber-500/20 group-hover:scale-105 transition-all">
                  <Sparkles className="h-6 w-6" />
                </div>
                <h4 className="text-lg font-bold text-white mb-2">Actionable Business Insights</h4>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Discover patterns, trends and important information that can help you make better business decisions.
                </p>
              </div>
              <div className="pt-4 text-xs font-semibold text-amber-400 flex items-center gap-1">
                Structured executive reports <ArrowRight className="h-3 w-3" />
              </div>
            </div>

            {/* FEATURE 6 */}
            <div className="glass-card glass-card-hover p-6 rounded-2xl border border-slate-800 relative group flex flex-col justify-between">
              <div>
                <div className="h-12 w-12 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 mb-5 group-hover:bg-rose-500/20 group-hover:scale-105 transition-all">
                  <ShieldCheck className="h-6 w-6" />
                </div>
                <h4 className="text-lg font-bold text-white mb-2">Secure Client Data</h4>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Keep client datasets separated using authenticated user and client-level access controls.
                </p>
              </div>
              <div className="pt-4 text-xs font-semibold text-rose-400 flex items-center gap-1">
                Tenant schema isolation <ArrowRight className="h-3 w-3" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 5. HOW IT WORKS (5 STEPS) */}
      {/* ========================================================================= */}
      <section id="how-it-works" className="py-20 md:py-28 bg-slate-900/40 border-y border-slate-800/80 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16 space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-indigo-400">Streamlined Workflow</h2>
            <h3 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              How It Works
            </h3>
            <p className="text-slate-400 text-sm sm:text-base">
              From raw dataset ingestion to executive visualizations in 5 straightforward steps.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 relative">
            {/* Step 1 */}
            <div className="glass-panel p-5 rounded-2xl border border-slate-800 relative flex flex-col justify-between">
              <div>
                <span className="text-xs font-extrabold text-indigo-400 tracking-wider">01</span>
                <h4 className="text-sm font-bold text-white mt-2 mb-1.5 uppercase tracking-wide">
                  UPLOAD YOUR DATA
                </h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Upload CSV or Excel business datasets.
                </p>
              </div>
              <div className="pt-4 flex justify-end">
                <FileSpreadsheet className="h-5 w-5 text-slate-600" />
              </div>
            </div>

            {/* Step 2 */}
            <div className="glass-panel p-5 rounded-2xl border border-slate-800 relative flex flex-col justify-between">
              <div>
                <span className="text-xs font-extrabold text-violet-400 tracking-wider">02</span>
                <h4 className="text-sm font-bold text-white mt-2 mb-1.5 uppercase tracking-wide">
                  AI UNDERSTANDS YOUR DATA
                </h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  The system detects the dataset structure and available metrics.
                </p>
              </div>
              <div className="pt-4 flex justify-end">
                <Database className="h-5 w-5 text-slate-600" />
              </div>
            </div>

            {/* Step 3 */}
            <div className="glass-panel p-5 rounded-2xl border border-slate-800 relative flex flex-col justify-between">
              <div>
                <span className="text-xs font-extrabold text-cyan-400 tracking-wider">03</span>
                <h4 className="text-sm font-bold text-white mt-2 mb-1.5 uppercase tracking-wide">
                  ASK QUESTIONS
                </h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Ask questions in normal business language.
                  <span className="block mt-1 font-mono text-[10px] text-slate-400 italic">"Which product has the highest sales?"</span>
                </p>
              </div>
              <div className="pt-4 flex justify-end">
                <HelpCircle className="h-5 w-5 text-slate-600" />
              </div>
            </div>

            {/* Step 4 */}
            <div className="glass-panel p-5 rounded-2xl border border-slate-800 relative flex flex-col justify-between">
              <div>
                <span className="text-xs font-extrabold text-emerald-400 tracking-wider">04</span>
                <h4 className="text-sm font-bold text-white mt-2 mb-1.5 uppercase tracking-wide">
                  GET ANSWERS
                </h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Gemini generates SQL using your actual dataset schema and retrieves the required results.
                </p>
              </div>
              <div className="pt-4 flex justify-end">
                <Code2 className="h-5 w-5 text-slate-600" />
              </div>
            </div>

            {/* Step 5 */}
            <div className="glass-panel p-5 rounded-2xl border border-slate-800 relative flex flex-col justify-between">
              <div>
                <span className="text-xs font-extrabold text-amber-400 tracking-wider">05</span>
                <h4 className="text-sm font-bold text-white mt-2 mb-1.5 uppercase tracking-wide">
                  VISUALIZE & ACT
                </h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  View KPIs, charts, trends and business insights.
                </p>
              </div>
              <div className="pt-4 flex justify-end">
                <BarChart3 className="h-5 w-5 text-slate-600" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 6. SAMPLE AI QUESTIONS ("Ask Your Data Anything") */}
      {/* ========================================================================= */}
      <section id="sample-questions" className="py-20 md:py-28 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-14 space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-indigo-400">Instant Natural Language Analytics</h2>
            <h3 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Ask Your Data Anything
            </h3>
            <p className="text-slate-400 text-sm sm:text-base">
              Click any question below to inspect how Gemini generates clean SQL and extracts data-driven answers.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Left: Questions selector list */}
            <div className="lg:col-span-5 space-y-2.5">
              {sampleQuestions.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => setActiveQuestionIdx(idx)}
                  className={`w-full p-4 rounded-xl text-left border transition-all flex items-center justify-between cursor-pointer ${
                    activeQuestionIdx === idx
                      ? 'bg-indigo-600/15 border-indigo-500/50 shadow-md shadow-indigo-900/20'
                      : 'bg-[#0d1222]/60 border-slate-800 hover:border-slate-700 hover:bg-slate-800/40'
                  }`}
                >
                  <div className="space-y-1">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500">
                      {item.category}
                    </span>
                    <p className="text-sm font-semibold text-slate-200">
                      "{item.q}"
                    </p>
                  </div>
                  <ChevronRight className={`h-4 w-4 transition-transform ${activeQuestionIdx === idx ? 'text-indigo-400 translate-x-1' : 'text-slate-600'}`} />
                </button>
              ))}
            </div>

            {/* Right: Live Answer & SQL Demonstration Panel */}
            <div className="lg:col-span-7 glass-panel p-6 rounded-2xl border border-slate-800 shadow-xl space-y-5">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-indigo-400" />
                  <span className="text-xs font-bold text-white uppercase tracking-wider">
                    Query Translation Preview
                  </span>
                </div>
                <span className="text-xs px-2.5 py-1 rounded-full bg-indigo-500/15 text-indigo-300 font-semibold border border-indigo-500/25">
                  {sampleQuestions[activeQuestionIdx].metric}
                </span>
              </div>

              <div>
                <span className="text-xs text-slate-400 block mb-1 font-medium">Selected Question:</span>
                <p className="text-base font-bold text-white">
                  "{sampleQuestions[activeQuestionIdx].q}"
                </p>
              </div>

              <div>
                <span className="text-[11px] font-mono uppercase text-slate-400 block mb-1.5 flex items-center gap-1.5">
                  <Terminal className="h-3.5 w-3.5 text-emerald-400" />
                  Generated SQLite SQL (Schema-Aware):
                </span>
                <pre className="p-3 bg-[#070b16] rounded-xl border border-slate-800/90 text-xs font-mono text-emerald-400 leading-relaxed overflow-x-auto">
                  {sampleQuestions[activeQuestionIdx].sql}
                </pre>
              </div>

              <div className="p-4 bg-slate-900/80 rounded-xl border border-slate-800 space-y-1.5">
                <span className="text-xs font-bold text-indigo-300 uppercase tracking-wider block">
                  AI Business Insight:
                </span>
                <p className="text-sm text-slate-300 leading-relaxed">
                  {sampleQuestions[activeQuestionIdx].result}
                </p>
              </div>

              {/* Profit Integrity Callout Banner */}
              <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200/90 flex items-start gap-2.5">
                <ShieldCheck className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold text-amber-300">Strict Financial & Profit Integrity: </span>
                  Profit is calculated only when an actual profit column or margin exists in the dataset schema,
                  or when explicitly specified by the user. Our models never fabricate or assume an arbitrary 18% margin.
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 7. DASHBOARD PREVIEW SECTION */}
      {/* ========================================================================= */}
      <section id="preview" className="py-20 md:py-28 bg-slate-900/30 border-t border-slate-800/80 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16 space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-widest text-indigo-400">Enterprise Dashboard Preview</h2>
            <h3 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Real-Time Visual Analytics At A Glance
            </h3>
            <p className="text-slate-400 text-sm sm:text-base">
              A unified interface designed for executives, analysts, and business owners.
            </p>
          </div>

          <div className="glass-panel p-6 rounded-2xl border border-slate-800 shadow-2xl space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
              <div>
                <h4 className="text-lg font-bold text-white flex items-center gap-2">
                  Client Business Overview
                  <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/25">
                    Live Demo
                  </span>
                </h4>
                <p className="text-xs text-slate-400">Simulated dataset analytics and category revenue trends</p>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Active Dataset:</span>
                <span className="text-xs font-mono px-2.5 py-1 rounded bg-slate-800 border border-slate-700 text-slate-200">
                  Global_ECommerce_2026.csv
                </span>
              </div>
            </div>

            {/* Preview Grid: 4 Metric Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-[#0b101e] border border-slate-800">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>Total Sales</span>
                  <DollarSign className="h-4 w-4 text-indigo-400" />
                </div>
                <div className="text-2xl font-bold text-white mt-2">$32,866,573</div>
                <div className="text-[11px] text-emerald-400 mt-1 flex items-center gap-1 font-medium">
                  <ArrowUpRight className="h-3 w-3" /> +18.4% period over period
                </div>
              </div>

              <div className="p-4 rounded-xl bg-[#0b101e] border border-slate-800">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>Total Orders</span>
                  <ShoppingCart className="h-4 w-4 text-violet-400" />
                </div>
                <div className="text-2xl font-bold text-white mt-2">142,850</div>
                <div className="text-[11px] text-emerald-400 mt-1 flex items-center gap-1 font-medium">
                  <ArrowUpRight className="h-3 w-3" /> +12.1% higher volume
                </div>
              </div>

              <div className="p-4 rounded-xl bg-[#0b101e] border border-slate-800">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>Total Customers</span>
                  <Users className="h-4 w-4 text-cyan-400" />
                </div>
                <div className="text-2xl font-bold text-white mt-2">38,420</div>
                <div className="text-[11px] text-emerald-400 mt-1 flex items-center gap-1 font-medium">
                  <ArrowUpRight className="h-3 w-3" /> +9.7% customer acquisition
                </div>
              </div>

              <div className="p-4 rounded-xl bg-[#0b101e] border border-slate-800">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>Growth Velocity</span>
                  <TrendingUp className="h-4 w-4 text-emerald-400" />
                </div>
                <div className="text-2xl font-bold text-white mt-2">+24.8%</div>
                <div className="text-[11px] text-emerald-400 mt-1 flex items-center gap-1 font-medium">
                  <ArrowUpRight className="h-3 w-3" /> Exceeding quarterly forecast
                </div>
              </div>
            </div>

            {/* Preview Charts Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Sales Trend Bar Visual */}
              <div className="p-4 rounded-xl bg-[#0b101e] border border-slate-800 flex flex-col justify-between">
                <div>
                  <h5 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">Sales Trend</h5>
                  <p className="text-[11px] text-slate-500">Monthly aggregate sales progression</p>
                </div>
                <div className="h-28 flex items-end gap-1.5 pt-4">
                  {[35, 42, 50, 48, 65, 70, 75, 85, 90, 80, 95, 100].map((val, i) => (
                    <div key={i} className="flex-1 bg-slate-800 rounded-t h-full flex items-end">
                      <div style={{ height: `${val}%` }} className="w-full bg-indigo-500 rounded-t" />
                    </div>
                  ))}
                </div>
                <div className="text-[10px] text-slate-500 flex justify-between mt-2">
                  <span>Jan</span>
                  <span>Jun</span>
                  <span>Dec</span>
                </div>
              </div>

              {/* Category Performance */}
              <div className="p-4 rounded-xl bg-[#0b101e] border border-slate-800 flex flex-col justify-between">
                <div>
                  <h5 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">Category Performance</h5>
                  <p className="text-[11px] text-slate-500">Share of revenue by business category</p>
                </div>
                <div className="space-y-2 py-2">
                  <div>
                    <div className="flex justify-between text-[11px] text-slate-300 mb-0.5">
                      <span>Electronics</span>
                      <span className="font-semibold text-white">43.6%</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                      <div className="h-full bg-indigo-500 rounded-full w-[43.6%]" />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-[11px] text-slate-300 mb-0.5">
                      <span>Home & Kitchen</span>
                      <span className="font-semibold text-white">27.2%</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                      <div className="h-full bg-violet-500 rounded-full w-[27.2%]" />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-[11px] text-slate-300 mb-0.5">
                      <span>Fashion & Apparel</span>
                      <span className="font-semibold text-white">18.1%</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                      <div className="h-full bg-cyan-500 rounded-full w-[18.1%]" />
                    </div>
                  </div>
                </div>
                <div className="text-[10px] text-slate-500 mt-1">Top 3 represent 88.9% of volume</div>
              </div>

              {/* Regional Performance */}
              <div className="p-4 rounded-xl bg-[#0b101e] border border-slate-800 flex flex-col justify-between">
                <div>
                  <h5 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-1">Regional Performance</h5>
                  <p className="text-[11px] text-slate-500">Global territory revenue contribution</p>
                </div>
                <div className="space-y-2 py-2">
                  <div className="flex items-center justify-between text-xs p-2 rounded bg-slate-900/60 border border-slate-800/80">
                    <span className="text-slate-300">North America</span>
                    <span className="font-bold text-white">$1,850,200</span>
                  </div>
                  <div className="flex items-center justify-between text-xs p-2 rounded bg-slate-900/60 border border-slate-800/80">
                    <span className="text-slate-300">Europe & UK</span>
                    <span className="font-bold text-white">$920,400</span>
                  </div>
                  <div className="flex items-center justify-between text-xs p-2 rounded bg-slate-900/60 border border-slate-800/80">
                    <span className="text-slate-300">Asia Pacific</span>
                    <span className="font-bold text-white">$642,800</span>
                  </div>
                </div>
                <div className="text-[10px] text-slate-500 mt-1">3 key operating territories</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 8. CALL TO ACTION SECTION */}
      {/* ========================================================================= */}
      <section className="py-20 md:py-28 relative overflow-hidden">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="glass-panel p-8 sm:p-14 rounded-3xl border border-indigo-500/30 text-center relative overflow-hidden shadow-2xl shadow-indigo-950/50">
            <div className="absolute -top-24 -right-24 w-60 h-60 rounded-full bg-indigo-500/20 blur-[100px] pointer-events-none" />
            <div className="absolute -bottom-24 -left-24 w-60 h-60 rounded-full bg-violet-600/20 blur-[100px] pointer-events-none" />

            <h3 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight mb-4">
              Ready to Understand Your Data?
            </h3>
            <p className="text-base sm:text-lg text-slate-300 max-w-xl mx-auto mb-8 leading-relaxed">
              Start turning your business data into actionable insights with enterprise-grade natural language AI.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <button
                onClick={() => navigate('/signup')}
                className="w-full sm:w-auto px-9 py-4 rounded-xl text-base font-semibold text-white bg-gradient-to-r from-indigo-600 via-indigo-500 to-violet-600 hover:from-indigo-500 hover:to-violet-500 shadow-xl shadow-indigo-600/30 hover:shadow-indigo-500/50 active:scale-[0.98] transition-all flex items-center justify-center gap-2.5 cursor-pointer"
              >
                Get Started
                <ArrowRight className="h-4 w-4" />
              </button>
              <button
                onClick={() => navigate('/login')}
                className="w-full sm:w-auto px-8 py-4 rounded-xl text-base font-semibold text-slate-200 bg-slate-800/90 hover:bg-slate-700 border border-slate-700 hover:border-slate-600 transition-all cursor-pointer"
              >
                Sign In to Existing Account
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 9. FOOTER */}
      {/* ========================================================================= */}
      <footer className="border-t border-slate-800/80 bg-[#05070e] py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-violet-600 flex items-center justify-center">
                <TrendingUp className="h-4 w-4 text-white" />
              </div>
              <div>
                <span className="text-sm font-bold text-white">AI Business Analyst</span>
                <p className="text-[11px] text-slate-500">Commercial Business Intelligence & SQL Analytics Platform</p>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-6 text-xs text-slate-400">
              <a href="#hero" className="hover:text-white transition">Home</a>
              <a href="#features" className="hover:text-white transition">Features</a>
              <a href="#how-it-works" className="hover:text-white transition">How It Works</a>
              <a href="#sample-questions" className="hover:text-white transition">Sample Questions</a>
              <button onClick={() => navigate('/login')} className="hover:text-white transition cursor-pointer">Login</button>
              <button onClick={() => navigate('/signup')} className="hover:text-white transition cursor-pointer">Sign Up</button>
            </div>

            <div className="text-xs text-slate-500 text-center md:text-right">
              &copy; {new Date().getFullYear()} AI Business Analyst. All rights reserved.
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

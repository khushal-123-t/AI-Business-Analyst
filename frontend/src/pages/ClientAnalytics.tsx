import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DollarSign, Percent, ShoppingCart, Users, TrendingUp, AlertCircle, Loader2, Database } from 'lucide-react';
import { api } from '../services/api';
import type { DashboardResponse, Dataset } from '../types';
import KPICard from '../components/KPICard';
import ChartsWrapper from '../components/charts/ChartsWrapper';
import DataTable from '../components/DataTable';

export default function ClientAnalytics() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | null>(() => {
    const stored = localStorage.getItem('activeDatasetId');
    return stored ? parseInt(stored) : null;
  });
  const [datasetsLoaded, setDatasetsLoaded] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();

  const fetchDashboardData = async (datasetId: number | null) => {
    if (!datasetId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.getDashboard(datasetId);
      setData(res);
    } catch (err: any) {
      if (err.message && (err.message.includes('not found') || err.message.includes('unauthorized') || err.message.includes('404'))) {
        localStorage.removeItem('activeDatasetId');
        localStorage.removeItem('activeDatasetName');
        loadDatasets();
      } else {
        setError(err.message || 'Failed to load dashboard data.');
      }
    } finally {
      setLoading(false);
    }
  };

  const loadDatasets = async () => {
    try {
      const res = await api.getClientDatasets();
      setDatasets(res);
      setDatasetsLoaded(true);
      
      if (res.length === 0) {
        setSelectedDatasetId(null);
        setData(null);
        setLoading(false);
        return;
      }

      const storedActiveId = localStorage.getItem('activeDatasetId');
      const targetId: number | null = storedActiveId ? parseInt(storedActiveId) : null;

      // Validate targetId exists in res
      const matched = res.find((d) => d.id === targetId);
      if (matched && targetId) {
        setSelectedDatasetId(targetId);
        fetchDashboardData(targetId);
      } else {
        const active = res.find((d) => d.status === 'ACTIVE') || res[0];
        if (active) {
          localStorage.setItem('activeDatasetId', active.id.toString());
          localStorage.setItem('activeDatasetName', active.name);
          setSelectedDatasetId(active.id);
          fetchDashboardData(active.id);
        } else {
          setSelectedDatasetId(null);
          setLoading(false);
        }
      }
    } catch (e: any) {
      console.error('Error fetching datasets:', e);
      setError(e.message || 'Failed to connect to datasets');
      setDatasetsLoaded(true);
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDatasets();

    // Listen for custom events when active dataset is switched or new dataset is uploaded
    const handleActiveChange = () => {
      loadDatasets();
      const storedId = localStorage.getItem('activeDatasetId');
      if (storedId) {
        const id = parseInt(storedId);
        setSelectedDatasetId(id);
        fetchDashboardData(id);
      } else {
        setSelectedDatasetId(null);
        setData(null);
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
    fetchDashboardData(id);
  };

  if (loading || (!datasetsLoaded && !data)) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-80px)]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
          <p className="text-sm text-slate-400 font-semibold">Compiling business analytics...</p>
        </div>
      </div>
    );
  }

  if (datasetsLoaded && datasets.length === 0) {
    return (
      <div className="p-8 max-w-lg mx-auto my-20 glass-panel rounded-xl border border-slate-800 text-center space-y-5">
        <Database className="h-12 w-12 text-slate-600 mx-auto" />
        <div className="space-y-2">
          <h3 className="text-sm font-bold text-slate-200 tracking-wide uppercase">No Analytics Data</h3>
          <p className="text-xs text-slate-400 leading-normal">
            You need to upload a dataset or import one from the library to view executive business analytics.
          </p>
        </div>
        <button
          onClick={() => navigate('/client/data')}
          className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-indigo-600/10 cursor-pointer"
        >
          Go to Dataset Explorer
        </button>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 max-w-xl mx-auto my-12 glass-panel rounded-xl border border-rose-500/10 text-center space-y-4">
        <AlertCircle className="h-10 w-10 text-rose-400 mx-auto" />
        <h3 className="font-bold text-slate-100">Dashboard Loading Error</h3>
        <p className="text-sm text-slate-400 leading-relaxed">{error}</p>
        <button
          onClick={() => fetchDashboardData(selectedDatasetId)}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold border border-slate-700 transition"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  const { metrics } = data;

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0
    }).format(val);
  };

  return (
    <div className="p-8 space-y-8 overflow-y-auto h-[calc(100vh-80px)]">
      {/* Header and Dataset Selector */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-slate-100 tracking-tight">Business Analytics</h2>
          <p className="text-xs text-slate-400 font-medium">Interactive charts generated from your active database</p>
        </div>
        {/* Workspace Swapper Selector */}
        <div className="flex items-center gap-2 bg-[#0c111e]/90 border border-slate-800/80 rounded-xl px-3.5 py-2">
          <Database className="h-4 w-4 text-indigo-400" />
          <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Active Dataset:</span>
          <select
            value={selectedDatasetId || ''}
            onChange={handleDatasetSwitch}
            className="bg-transparent border-none text-xs text-slate-200 focus:outline-none font-bold"
          >
            {datasets.map((ds) => (
              <option key={ds.id} value={ds.id} className="bg-[#0b0f19] text-slate-300">
                {ds.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        <KPICard
          title="Total Revenue"
          value={formatCurrency(metrics.total_revenue)}
          icon={DollarSign}
          description="Gross warehouse value"
          color="indigo"
        />
        <KPICard
          title="Total Profit"
          value={metrics.total_profit !== null ? formatCurrency(metrics.total_profit) : "Not available"}
          icon={TrendingUp}
          description={
            metrics.total_profit !== null && metrics.total_revenue > 0
              ? (metrics.profit_note || `Profit Margin: ${Math.round((metrics.total_profit / metrics.total_revenue) * 100)}%`)
              : "Cannot be calculated from available data"
          }
          color="emerald"
        />
        <KPICard
          title="Total Orders"
          value={metrics.total_orders.toLocaleString()}
          icon={ShoppingCart}
          description="Fulfillments processed"
          color="sky"
        />
        <KPICard
          title="Total Customers"
          value={metrics.total_customers.toLocaleString()}
          icon={Users}
          description="Unique buyers segment"
          color="amber"
        />
        <KPICard
          title="Average Order Value"
          value={formatCurrency(metrics.average_order_value)}
          icon={Percent}
          description="Mean transaction value"
          color="rose"
        />
      </div>

      {/* Analytics Charts */}
      {data.revenue_trend.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="glass-panel p-6 rounded-xl border border-slate-800">
            <div className="mb-4">
              <h3 className="text-sm font-bold text-slate-200 tracking-wide uppercase">Revenue Trend</h3>
              <span className="text-[10px] text-slate-500 font-medium">Monthly revenue totals</span>
            </div>
            <ChartsWrapper
              chartType="line"
              xAxis="month"
              yAxis="revenue"
              data={data.revenue_trend}
              height={260}
            />
          </div>

          <div className="glass-panel p-6 rounded-xl border border-slate-800">
            <div className="mb-4">
              <h3 className="text-sm font-bold text-slate-200 tracking-wide uppercase">Monthly Order Volume</h3>
              <span className="text-[10px] text-slate-500 font-medium">Unique transactions count per month</span>
            </div>
            <ChartsWrapper
              chartType="bar"
              xAxis="month"
              yAxis="orders"
              data={data.monthly_orders}
              height={260}
            />
          </div>
        </div>
      )}

      {/* Category Breaks */}
      {data.revenue_by_category.length > 0 && (
        <div className={`grid grid-cols-1 ${data.profit_by_category && data.profit_by_category.length > 0 ? "lg:grid-cols-3" : "lg:grid-cols-2"} gap-8`}>
          <div className="glass-panel p-6 rounded-xl border border-slate-800">
            <div className="mb-4">
              <h3 className="text-sm font-bold text-slate-200 tracking-wide uppercase">Revenue by Category</h3>
              <span className="text-[10px] text-slate-500 font-medium">Proportional category share</span>
            </div>
            <ChartsWrapper
              chartType="donut"
              xAxis="category"
              yAxis="revenue"
              data={data.revenue_by_category}
              height={260}
            />
          </div>

          {data.profit_by_category && data.profit_by_category.length > 0 && (
            <div className="glass-panel p-6 rounded-xl border border-slate-800">
              <div className="mb-4">
                <h3 className="text-sm font-bold text-slate-200 tracking-wide uppercase">Profit by Category</h3>
                <span className="text-[10px] text-slate-500 font-medium">Absolute margins per category</span>
              </div>
              <ChartsWrapper
                chartType="bar"
                xAxis="category"
                yAxis="profit"
                data={data.profit_by_category}
                height={260}
              />
            </div>
          )}

          <div className="glass-panel p-6 rounded-xl border border-slate-800">
            <div className="mb-4">
              <h3 className="text-sm font-bold text-slate-200 tracking-wide uppercase">Revenue by Region</h3>
              <span className="text-[10px] text-slate-500 font-medium">Regional sales distribution</span>
            </div>
            <ChartsWrapper
              chartType="bar"
              xAxis="region"
              yAxis="revenue"
              data={data.revenue_by_region}
              height={260}
            />
          </div>
        </div>
      )}

      {/* Top 10 Customers */}
      {data.top_customers.length > 0 && (
        <div className="grid grid-cols-1 gap-8">
          <DataTable
            columns={metrics.total_profit !== null ? ['customer_name', 'revenue', 'profit'] : ['customer_name', 'revenue']}
            rows={data.top_customers}
            title="Top 10 Customers by Revenue"
            pageSize={5}
          />
        </div>
      )}
    </div>
  );
}

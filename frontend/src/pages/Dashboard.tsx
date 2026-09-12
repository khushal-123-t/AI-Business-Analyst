import React, { useEffect, useState } from 'react';
import { DollarSign, Percent, ShoppingCart, Users, TrendingUp, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import type { DashboardResponse } from '../types';
import KPICard from '../components/KPICard';
import ChartsWrapper from '../components/charts/ChartsWrapper';
import DataTable from '../components/DataTable';

export default function Dashboard() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getDashboard();
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard data. Ensure the backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center h-full min-h-[500px]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
          <p className="text-sm text-slate-400 font-semibold">Loading dashboard indicators...</p>
        </div>
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
          onClick={fetchDashboardData}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold border border-slate-700 transition"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  const { metrics } = data;

  // Format currency value helper
  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(val);
  };

  return (
    <div className="p-8 space-y-8 overflow-y-auto h-[calc(100vh-80px)]">
      {/* Skipped Visualizations Notice if any */}
      {data.skipped_visualizations && data.skipped_visualizations.length > 0 && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl px-4 py-3 flex items-start gap-3 text-xs text-slate-400">
          <AlertCircle className="h-4 w-4 text-amber-400/80 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-slate-200">Dataset Adaptation Notice: </span>
            {data.skipped_visualizations.join(" ")}
          </div>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        <KPICard
          title={metrics.metric_labels?.revenue_title || metrics.metric_labels?.primary_metric_title || "Total Revenue"}
          value={formatCurrency(metrics.total_revenue)}
          icon={DollarSign}
          description="Total revenue"
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
          title={metrics.metric_labels?.count_title || "Total Orders"}
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
          title={metrics.metric_labels?.average_title || "Average Order Value"}
          value={formatCurrency(metrics.average_order_value)}
          icon={Percent}
          description="Mean gross transaction"
          color="rose"
        />
      </div>

      {/* Primary Analytical Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Revenue Trend Line */}
        <div className="glass-panel p-6 rounded-xl border border-slate-800/80">
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

        {/* Monthly Orders Bar */}
        <div className="glass-panel p-6 rounded-xl border border-slate-800/80">
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

      {/* Category Breakdowns Row */}
      <div className={`grid grid-cols-1 ${data.profit_by_category && data.profit_by_category.length > 0 ? "lg:grid-cols-3" : "lg:grid-cols-2"} gap-8`}>
        {/* Revenue by Category (Pie/Donut) */}
        <div className="glass-panel p-6 rounded-xl border border-slate-800/80">
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

        {/* Profit by Category (Bar) - Only render if profit data exists */}
        {data.profit_by_category && data.profit_by_category.length > 0 && (
          <div className="glass-panel p-6 rounded-xl border border-slate-800/80">
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

        {/* Revenue by Region (Bar) */}
        <div className="glass-panel p-6 rounded-xl border border-slate-800/80">
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

      {/* Top 10 Customers DataTable */}
      <div className="grid grid-cols-1 gap-8">
        <DataTable
          columns={metrics.total_profit !== null ? ['customer_name', 'revenue', 'profit'] : ['customer_name', 'revenue']}
          rows={data.top_customers}
          title="Top 10 Customers by Revenue"
          pageSize={5}
        />
      </div>
    </div>
  );
}

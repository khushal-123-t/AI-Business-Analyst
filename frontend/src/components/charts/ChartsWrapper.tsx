import React from 'react';
import {
  ResponsiveContainer,
  LineChart, Line,
  BarChart, Bar,
  PieChart, Pie, Cell,
  ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend
} from 'recharts';

interface ChartsWrapperProps {
  chartType: 'line' | 'bar' | 'donut' | 'scatter' | 'none';
  xAxis: string | null;
  yAxis: string | null;
  data: Record<string, any>[];
  height?: number;
}

const COLORS = [
  '#6366f1', // Indigo
  '#8b5cf6', // Violet
  '#10b981', // Emerald
  '#f59e0b', // Amber
  '#ef4444', // Rose
  '#0ea5e9', // Sky
];

export default function ChartsWrapper({ chartType, xAxis, yAxis, data, height = 320 }: ChartsWrapperProps) {
  if (chartType === 'none' || !xAxis || !yAxis || !data || data.length === 0) {
    return null;
  }

  // Label formatting helper for tooltips
  const formatValue = (value: any, name: string) => {
    const key = name.toLowerCase();
    if (typeof value === 'number') {
      if (key.includes('revenue') || key.includes('profit') || key.includes('price') || key.includes('value') || key.includes('rev') || key.includes('aov')) {
        return [`₹${value.toLocaleString('en-IN')}`, name.replace(/_/g, ' ')];
      }
      if (key.includes('discount')) {
        return [`${Math.round(value * 100)}%`, name.replace(/_/g, ' ')];
      }
      return [value.toLocaleString(), name.replace(/_/g, ' ')];
    }
    return [value, name];
  };

  // Y-axis tick formatting helper
  const formatYAxis = (value: any) => {
    if (typeof value === 'number') {
      if (value >= 10000000) {
        return `₹${(value / 10000000).toFixed(1)}Cr`;
      }
      if (value >= 100000) {
        return `₹${(value / 100000).toFixed(0)}L`;
      }
      if (value >= 1000) {
        return `₹${(value / 100).toFixed(0)}K`;
      }
      return `₹${value}`;
    }
    return value;
  };

  const renderChart = () => {
    switch (chartType) {
      case 'line':
        return (
          <LineChart data={data} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
            <defs>
              <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#6366f1" />
                <stop offset="100%" stopColor="#8b5cf6" />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey={xAxis}
              stroke="#64748b"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              dy={10}
            />
            <YAxis
              stroke="#64748b"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              tickFormatter={formatYAxis}
              dx={-5}
            />
            <Tooltip
              formatter={formatValue}
              contentStyle={{ background: '#0d121f', borderColor: '#1e293b', borderRadius: '8px', fontSize: '12px' }}
              labelStyle={{ color: '#94a3b8', fontWeight: 'bold' }}
            />
            <Line
              type="monotone"
              dataKey={yAxis}
              stroke="url(#lineGrad)"
              strokeWidth={3}
              activeDot={{ r: 6, stroke: '#0b0f19', strokeWidth: 2 }}
              dot={data.length < 50 ? { r: 3 } : false}
            />
          </LineChart>
        );

      case 'bar':
        return (
          <BarChart data={data} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
            <defs>
              <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#6366f1" stopOpacity={0.9} />
                <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0.6} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey={xAxis}
              stroke="#64748b"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              dy={10}
            />
            <YAxis
              stroke="#64748b"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              tickFormatter={formatYAxis}
              dx={-5}
            />
            <Tooltip
              formatter={formatValue}
              contentStyle={{ background: '#0d121f', borderColor: '#1e293b', borderRadius: '8px', fontSize: '12px' }}
              labelStyle={{ color: '#94a3b8', fontWeight: 'bold' }}
            />
            <Bar
              dataKey={yAxis}
              fill="url(#barGrad)"
              radius={[4, 4, 0, 0]}
              maxBarSize={50}
            />
          </BarChart>
        );

      case 'donut':
        return (
          <PieChart margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
            <Tooltip
              formatter={formatValue}
              contentStyle={{ background: '#0d121f', borderColor: '#1e293b', borderRadius: '8px', fontSize: '12px' }}
            />
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={90}
              paddingAngle={4}
              dataKey={yAxis}
              nameKey={xAxis}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Legend
              verticalAlign="bottom"
              height={36}
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: '10px', color: '#64748b' }}
            />
          </PieChart>
        );

      case 'scatter':
        return (
          <ScatterChart margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              type="number"
              dataKey={xAxis}
              name={xAxis}
              stroke="#64748b"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              tickFormatter={formatYAxis}
            />
            <YAxis
              type="number"
              dataKey={yAxis}
              name={yAxis}
              stroke="#64748b"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              tickFormatter={formatYAxis}
            />
            <Tooltip
              formatter={formatValue}
              cursor={{ strokeDasharray: '3 3' }}
              contentStyle={{ background: '#0d121f', borderColor: '#1e293b', borderRadius: '8px', fontSize: '12px' }}
            />
            <Scatter name="Data Distribution" data={data} fill="#6366f1" />
          </ScatterChart>
        );

      default:
        return null;
    }
  };

  return (
    <div className="w-full" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        {renderChart() || <div>Chart rendering unsupported</div>}
      </ResponsiveContainer>
    </div>
  );
}

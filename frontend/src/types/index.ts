export interface AskRequest {
  question: string;
  session_id?: string;
}

export interface ChartConfig {
  chart_type: 'line' | 'bar' | 'donut' | 'scatter' | 'none';
  x_axis: string | null;
  y_axis: string | null;
  data: Record<string, any>[];
}

export interface AskResponse {
  question: string;
  sql: string;
  columns: string[];
  rows: Record<string, any>[];
  chart: ChartConfig;
  summary: string;
  key_findings: string[];
  business_impact: string;
  recommendations: string[];
  error: string | null;
  success: boolean;
}

export interface DashboardMetrics {
  total_revenue: number;
  total_profit: number;
  total_orders: number;
  total_customers: number;
  average_order_value: number;
}

export interface DashboardResponse {
  metrics: DashboardMetrics;
  revenue_trend: Record<string, any>[];
  revenue_by_category: Record<string, any>[];
  revenue_by_region: Record<string, any>[];
  profit_by_category: Record<string, any>[];
  top_customers: Record<string, any>[];
  monthly_orders: Record<string, any>[];
}

export interface ColumnInfo {
  name: string;
  type: string;
}

export interface TableInfo {
  name: string;
  row_count: number;
  columns: ColumnInfo[];
  preview: Record<string, any>[];
}

export interface SchemaResponse {
  tables: TableInfo[];
}

export interface HistoryItem {
  id: string;
  question: string;
  timestamp: string;
  sql: string;
  chart_type: string;
}

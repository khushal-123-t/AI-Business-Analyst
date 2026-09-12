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
  revenue?: number;
  total_profit: number | null;
  profit_available?: boolean;
  profit_source?: string | null;
  profit_note?: string | null;
  total_orders: number;
  total_customers: number;
  average_order_value: number;
  metric_labels?: {
    primary_metric_title?: string;
    revenue_title?: string;
    count_title?: string;
    average_title?: string;
    category_title?: string;
    region_title?: string;
  };
}

export interface DashboardResponse {
  metrics: DashboardMetrics;
  revenue_trend: Record<string, any>[];
  revenue_by_category: Record<string, any>[];
  revenue_by_region: Record<string, any>[];
  profit_by_category: Record<string, any>[];
  profit_available?: boolean;
  top_customers: Record<string, any>[];
  monthly_orders: Record<string, any>[];
  skipped_visualizations?: string[];
  metric_labels?: {
    primary_metric_title?: string;
    revenue_title?: string;
    count_title?: string;
    average_title?: string;
    category_title?: string;
    region_title?: string;
  };
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

export interface User {
  id: number;
  name: string;
  email: string;
  role: 'ADMIN' | 'CLIENT';
  client_id?: number | null;
  is_active: boolean;
  created_at: string;
  last_login?: string | null;
}

export interface Client {
  id: number;
  company_name: string;
  contact_name: string;
  email: string;
  phone?: string | null;
  industry?: string | null;
  plan?: string | null;
  status: 'ACTIVE' | 'INACTIVE' | 'SUSPENDED';
  created_at: string;
  last_login?: string | null;
}

export interface Dataset {
  id: number;
  client_id: number;
  name: string;
  filename: string;
  table_name: string;
  row_count: number;
  col_count: number;
  status: string;
  created_at: string;
}

export interface Report {
  id: number;
  client_id: number;
  dataset_id: number;
  name: string;
  report_type: string;
  status: string;
  created_at: string;
  content?: string | null;
}

export interface AdminDashboardMetrics {
  total_clients: number;
  active_clients: number;
  inactive_clients: number;
  suspended_clients: number;
  total_datasets: number;
  total_analyses: number;
  reports_generated: number;
  active_users: number;
}

export interface AdminDashboardResponse {
  metrics: AdminDashboardMetrics;
  client_growth: Record<string, any>[];
  client_usage: Record<string, any>[];
  recent_activity: Record<string, any>[];
}

export interface ClientProfileResponse {
  user: User;
  client?: Client | null;
}

export interface LibraryDataset {
  id: string;
  name: string;
  description: string;
  category: string;
  rows: number;
  columns: number;
  filename: string;
}


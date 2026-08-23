from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# --- Q&A /api/ask models ---

class AskRequest(BaseModel):
    question: str
    session_id: Optional[str] = "default_session"

class ChartConfig(BaseModel):
    chart_type: str  # 'line' | 'bar' | 'donut' | 'scatter' | 'none'
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    data: List[Dict[str, Any]] = []

class AskResponse(BaseModel):
    question: str
    sql: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    chart: ChartConfig
    summary: str
    key_findings: List[str]
    business_impact: str
    recommendations: List[str]
    error: Optional[str] = None
    success: bool = True

# --- Dashboard /api/dashboard models ---

class DashboardMetrics(BaseModel):
    total_revenue: float
    total_profit: float
    total_orders: int
    total_customers: int
    average_order_value: float

class DashboardResponse(BaseModel):
    metrics: DashboardMetrics
    revenue_trend: List[Dict[str, Any]]
    revenue_by_category: List[Dict[str, Any]]
    revenue_by_region: List[Dict[str, Any]]
    profit_by_category: List[Dict[str, Any]]
    top_customers: List[Dict[str, Any]]
    monthly_orders: List[Dict[str, Any]]

# --- Data Explorer /api/schema models ---

class ColumnInfo(BaseModel):
    name: str
    type: str

class TableInfo(BaseModel):
    name: str
    row_count: int
    columns: List[ColumnInfo]
    preview: List[Dict[str, Any]]

# --- History /api/history models ---

class HistoryItem(BaseModel):
    id: str
    question: str
    timestamp: str
    sql: str
    chart_type: str

class SchemaResponse(BaseModel):
    tables: List[TableInfo]

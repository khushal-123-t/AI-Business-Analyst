from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

# --- Q&A /api/ask models ---

class AskRequest(BaseModel):
    question: str
    session_id: Optional[str] = "default_session"
    dataset_id: Optional[int] = None

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
    gross_sales: Optional[float] = None
    total_discounts: Optional[float] = None
    total_tax: Optional[float] = None
    total_shipping: Optional[float] = None
    total_quantity: Optional[float] = None
    total_cost: Optional[float] = None
    average_price: Optional[float] = None
    total_orders: int
    total_customers: int
    average_order_value: float
    total_profit: Optional[float] = None
    profit_margin: Optional[float] = None
    profit_available: bool = True
    profit_source: Optional[str] = None
    profit_note: Optional[str] = None
    metric_labels: Optional[Dict[str, str]] = None

class DashboardResponse(BaseModel):
    metrics: DashboardMetrics
    revenue_trend: List[Dict[str, Any]]
    revenue_by_category: List[Dict[str, Any]]
    revenue_by_region: List[Dict[str, Any]]
    profit_by_category: List[Dict[str, Any]] = []
    top_customers: List[Dict[str, Any]]
    monthly_orders: List[Dict[str, Any]]
    profit_available: bool = True
    skipped_visualizations: List[str] = []
    metric_labels: Optional[Dict[str, str]] = None

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

# --- Auth schemas ---
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str
    company_name: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    name: str

# --- Client schemas ---
class ClientBase(BaseModel):
    company_name: str
    contact_name: str
    email: str
    phone: Optional[str] = None
    industry: Optional[str] = None
    plan: Optional[str] = "FREE"
    status: Optional[str] = "ACTIVE"

class ClientCreate(ClientBase):
    password: str

class ClientUpdate(BaseModel):
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    industry: Optional[str] = None
    plan: Optional[str] = None
    status: Optional[str] = None
    password: Optional[str] = None

class ClientOut(ClientBase):
    id: int
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- User schemas ---
class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    client_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    industry: Optional[str] = None
    password: Optional[str] = None

class ClientProfileResponse(BaseModel):
    user: UserOut
    client: Optional[ClientOut] = None

# --- Dataset schemas ---
class DatasetOut(BaseModel):
    id: int
    client_id: int
    name: str
    filename: str
    table_name: str
    row_count: int
    col_count: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- Report schemas ---
class ReportCreate(BaseModel):
    name: str
    report_type: str
    dataset_id: int
    content: str

class ReportOut(BaseModel):
    id: int
    client_id: int
    dataset_id: int
    name: str
    report_type: str
    status: str
    created_at: datetime
    content: Optional[str] = None

    class Config:
        from_attributes = True

# --- Admin Dashboard KPI schemas ---
class AdminDashboardMetrics(BaseModel):
    total_clients: int
    active_clients: int
    inactive_clients: int
    suspended_clients: int
    total_datasets: int
    total_analyses: int
    reports_generated: int
    active_users: int

class AdminDashboardResponse(BaseModel):
    metrics: AdminDashboardMetrics
    client_growth: List[Dict[str, Any]]
    client_usage: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]

# --- Library Dataset schemas ---
class LibraryDatasetOut(BaseModel):
    id: str
    name: str
    description: str
    category: str
    rows: int
    columns: int
    filename: str

class ImportLibraryRequest(BaseModel):
    library_id: str
    custom_name: Optional[str] = None


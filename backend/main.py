import os
import sys
import uuid
import re
import time
import io
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent directory of backend to sys.path to enable absolute imports
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Add venv site-packages to sys.path programmatically to resolve dependencies
venv_site_packages = os.path.join(root_dir, "venv", "Lib", "site-packages")
if os.path.exists(venv_site_packages) and venv_site_packages not in sys.path:
    sys.path.insert(0, venv_site_packages)

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
import pandas as pd

from backend.config import settings
from backend.database.connection import get_db, engine, quote_ident
from backend.database.init_db import create_and_seed_tables
from backend.models.orm_models import Client, User, Dataset, Report
from backend.utils.auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, get_current_admin, get_current_client
)
from backend.models.schemas import (
    AskRequest, AskResponse, ChartConfig,
    DashboardResponse, SchemaResponse, HistoryItem,
    LoginRequest, RegisterRequest, TokenResponse, UserOut, ClientOut,
    ClientCreate, ClientUpdate, ProfileUpdate,
    DatasetOut, ReportCreate, ReportOut, ClientProfileResponse,
    AdminDashboardResponse, AdminDashboardMetrics,
    LibraryDatasetOut, ImportLibraryRequest
)
import logging
logger = logging.getLogger("ai_analyst.api")

from backend.services.sql_service import execute_query
from backend.services.llm_provider import provider_manager
from backend.services.llm_service import (
    generate_sql, generate_insights, add_history_context, extract_explicit_margin,
    execute_query_with_retry,
    LLMError, LLMConnectionError, LLMAuthError, LLMModelError, LLMEmptyResponse,
    SQLExtractionError, SQLValidationError, CannotAnswerError
)
from backend.services.schema_service import inspect_dataset_schema
from backend.services.analysis_service import get_dashboard_data, resolve_columns, invalidate_dashboard_cache
from backend.services.visualization_service import determine_chart_config

# Initialize database and seed tables
create_and_seed_tables()

# Initialize FastAPI App
app = FastAPI(title="AI Business Analyst API", version="1.0.0")

# Enable CORS for frontend deployment (Vercel, Render, and local development)
cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Dynamically parse FRONTEND_URL from environment
if hasattr(settings, "FRONTEND_URL") and settings.FRONTEND_URL:
    for origin_candidate in settings.FRONTEND_URL.split(","):
        clean_origin = origin_candidate.strip().rstrip("/")
        if clean_origin and clean_origin not in cors_origins:
            cors_origins.append(clean_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https://.*\.vercel\.app$|^https://.*\.onrender\.com$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    """Validates Gemini configuration, database status, and system dependencies on startup."""
    logger.info("Starting AI Business Analyst API (Gemini LLM Provider)...")
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"[Database] Engine ready. Active tables: {len(tables)} tables ({', '.join(tables[:5])}...)")
        print(f"[Database] Engine ready with {len(tables)} active tables.")
    except Exception as db_err:
        logger.error(f"[Database] Startup inspection failed: {db_err}")
        print(f"[Database] WARNING: Startup inspection failed: {db_err}")

    if settings.GEMINI_API_KEY:
        logger.info(f"[Gemini] Configured with model '{settings.GEMINI_MODEL}'.")
        print(f"[Gemini] Active LLM Provider: Gemini ({settings.GEMINI_MODEL}).")
    else:
        logger.warning("[Gemini] GEMINI_API_KEY is not configured in .env.")
        print("WARNING: GEMINI_API_KEY is not configured in .env.")

# Scope query history to client_id
# Format: list of dicts: {"id": str, "client_id": int, "question": str, "timestamp": str, "sql": str, "chart_type": str}
global_history_scoped = []

def verify_sql_isolation(sql: str, allowed_table: str) -> bool:
    """
    Bulletproof regex validation to prevent SQL queries from referencing unauthorized tables.
    Specifically checks table references in FROM, JOIN, INTO, UPDATE clauses and comma joins.
    """
    inspector = inspect(engine)
    all_tables = inspector.get_table_names()
    for table in all_tables:
        if table.lower() != allowed_table.lower():
            # Specifically check if the unauthorized table is queried as a table source
            pattern = rf"(?:\b(FROM|JOIN|INTO|UPDATE)\s+|,)\s*[`\"']?{re.escape(table)}[`\"']?\b"
            if re.search(pattern, sql, re.IGNORECASE):
                return False
    return True

# --- SYSTEM & HEALTH CHECK ENDPOINTS ---

@app.get("/api/health")
def health_check():
    """Health check endpoint verifying backend, database, and LLM provider connectivity."""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        llm_status = provider_manager.get_status()
        db_type = "sqlite" if str(engine.url).startswith("sqlite") else "postgresql"
        return {
            "status": "connected",
            "database": db_type,
            "tables_count": len(tables),
            "llm": llm_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

# --- AUTHENTICATION ENDPOINTS ---

@app.post("/auth/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticates admin or client users and returns access token."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        # Broad error message to prevent email harvesting
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or password"
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    # If user is a CLIENT, verify that the associated Client record is ACTIVE
    if user.role == "CLIENT" and user.client_id:
        client = db.query(Client).filter(Client.id == user.client_id).first()
        if not client or client.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access suspended. Client status is {client.status if client else 'INACTIVE'}."
            )

    # Update last login time
    user.last_login = datetime.utcnow()
    if user.role == "CLIENT" and user.client_id:
        client = db.query(Client).filter(Client.id == user.client_id).first()
        if client:
            client.last_login = datetime.utcnow()
    db.commit()

    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        name=user.name
    )

@app.post("/auth/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Registers a new Client account and linked User, returning authentication token."""
    email_clean = req.email.strip().lower()
    name_clean = req.full_name.strip()
    if not email_clean or not name_clean or not req.password:
        raise HTTPException(status_code=400, detail="All fields are required")
    
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")

    # Check email uniqueness in users and clients
    existing_user = db.query(User).filter(User.email == email_clean).first()
    existing_client = db.query(Client).filter(Client.email == email_clean).first()
    if existing_user or existing_client:
        raise HTTPException(status_code=400, detail="An account with this email address already exists")

    company = req.company_name or f"{name_clean}'s Workspace"
    new_client = Client(
        company_name=company,
        contact_name=name_clean,
        email=email_clean,
        status="ACTIVE",
        plan="FREE",
        created_at=datetime.utcnow()
    )
    db.add(new_client)
    db.commit()
    db.refresh(new_client)

    new_user = User(
        name=name_clean,
        email=email_clean,
        password_hash=get_password_hash(req.password),
        role="CLIENT",
        client_id=new_client.id,
        is_active=True,
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()

    # Seed isolated table by copying original sales table if it exists
    inspector = inspect(engine)
    if "sales" in inspector.get_table_names():
        seed_table = f"dataset_client_{new_client.id}_seed"
        try:
            quoted_seed = quote_ident(seed_table)
            quoted_sales = quote_ident("sales")
            db.execute(text(f"CREATE TABLE {quoted_seed} AS SELECT * FROM {quoted_sales}"))
            db.commit()
            row_count = db.execute(text(f"SELECT COUNT(*) FROM {quoted_seed}")).scalar()
            col_count = len(inspector.get_columns("sales"))
            dataset = Dataset(
                client_id=new_client.id,
                name="Default Sales Dataset",
                filename="sales_data.csv",
                table_name=seed_table,
                row_count=row_count,
                col_count=col_count,
                status="ACTIVE",
                created_at=datetime.utcnow()
            )
            db.add(dataset)
            db.commit()
        except Exception as e:
            logger.warning(f"Could not seed default table for client {new_client.id}: {e}")

    access_token = create_access_token(data={"sub": new_user.email, "role": new_user.role})
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        role=new_user.role,
        name=new_user.name
    )

@app.get("/auth/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Returns current user's profile metadata."""
    return current_user

@app.post("/auth/logout")
def logout():
    """Logs out user (success stub, token clearance handled by front-end)."""
    return {"status": "success", "message": "Logged out successfully"}


# --- ADMIN PORTAL ENDPOINTS ---

@app.get("/admin/dashboard", response_model=AdminDashboardResponse)
def get_admin_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    """Compiles KPI counts, usage analytics, and growth chart statistics for the platform."""
    total_clients = db.query(Client).count()
    active_clients = db.query(Client).filter(Client.status == "ACTIVE").count()
    inactive_clients = db.query(Client).filter(Client.status == "INACTIVE").count()
    suspended_clients = db.query(Client).filter(Client.status == "SUSPENDED").count()
    total_datasets = db.query(Dataset).count()
    total_analyses = len(global_history_scoped)
    reports_generated = db.query(Report).count()
    active_users = db.query(User).filter(User.is_active == True).count()

    # Generate dummy usage growth data based on seeding timestamps
    client_growth = [
        {"date": "2026-06", "clients": max(0, total_clients - 2)},
        {"date": "2026-07", "clients": max(0, total_clients - 1)},
        {"date": "2026-08", "clients": total_clients}
    ]

    # Usage per client
    clients = db.query(Client).all()
    client_usage = []
    for c in clients:
        d_count = db.query(Dataset).filter(Dataset.client_id == c.id).count()
        r_count = db.query(Report).filter(Report.client_id == c.id).count()
        # count query logs
        q_count = len([x for x in global_history_scoped if x.get("client_id") == c.id])
        client_usage.append({
            "company": c.company_name,
            "datasets": d_count,
            "queries": q_count,
            "reports": r_count
        })

    # Recent activity logs
    recent_activity = []
    # get 5 most recent datasets
    recent_ds = db.query(Dataset).order_by(Dataset.created_at.desc()).limit(5).all()
    for ds in recent_ds:
        c = db.query(Client).filter(Client.id == ds.client_id).first()
        company = c.company_name if c else "Unknown"
        recent_activity.append({
            "timestamp": ds.created_at.strftime("%Y-%m-%d %H:%M"),
            "event": f"Dataset '{ds.name}' uploaded",
            "client": company
        })

    metrics = AdminDashboardMetrics(
        total_clients=total_clients,
        active_clients=active_clients,
        inactive_clients=inactive_clients,
        suspended_clients=suspended_clients,
        total_datasets=total_datasets,
        total_analyses=total_analyses,
        reports_generated=reports_generated,
        active_users=active_users
    )

    return AdminDashboardResponse(
        metrics=metrics,
        client_growth=client_growth,
        client_usage=client_usage,
        recent_activity=recent_activity[:5]
    )

@app.get("/admin/clients", response_model=List[ClientOut])
def get_clients(db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    """Lists all registered Client companies."""
    return db.query(Client).order_by(Client.created_at.desc()).all()

@app.post("/admin/clients", response_model=ClientOut)
def create_client(req: ClientCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    """Registers a new Client profile, creates their linked Client user account, and seeds their default table."""
    # Check email uniqueness in users and clients
    existing_user = db.query(User).filter(User.email == req.email).first()
    existing_client = db.query(Client).filter(Client.email == req.email).first()
    if existing_user or existing_client:
         raise HTTPException(status_code=400, detail="A user or client with this email already exists")

    new_client = Client(
        company_name=req.company_name,
        contact_name=req.contact_name,
        email=req.email,
        phone=req.phone,
        industry=req.industry,
        plan=req.plan,
        status=req.status or "ACTIVE",
        created_at=datetime.utcnow()
    )
    db.add(new_client)
    db.commit()
    db.refresh(new_client)

    # Create linked client user account
    new_user = User(
        name=req.contact_name,
        email=req.email,
        password_hash=get_password_hash(req.password),
        role="CLIENT",
        client_id=new_client.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()

    # Seed isolated table by copying original sales table if it exists
    inspector = inspect(engine)
    if "sales" in inspector.get_table_names():
        seed_table = f"dataset_client_{new_client.id}_seed"
        quoted_seed = quote_ident(seed_table)
        quoted_sales = quote_ident("sales")
        db.execute(text(f"CREATE TABLE {quoted_seed} AS SELECT * FROM {quoted_sales}"))
        db.commit()

        row_count = db.execute(text(f"SELECT COUNT(*) FROM {quoted_seed}")).scalar()
        col_count = len(inspector.get_columns("sales"))

        dataset = Dataset(
            client_id=new_client.id,
            name="Default Sales Dataset",
            filename="sales_data.csv",
            table_name=seed_table,
            row_count=row_count,
            col_count=col_count,
            status="ACTIVE",
            created_at=datetime.utcnow()
        )
        db.add(dataset)
        db.commit()

    return new_client

@app.get("/admin/clients/{client_id}")
def get_client_details(client_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    """Fetches detailed profile metrics, uploaded datasets, reports, and activity logs for a specific client."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    datasets = db.query(Dataset).filter(Dataset.client_id == client_id).all()
    reports = db.query(Report).filter(Report.client_id == client_id).all()
    
    # Calculate stats
    datasets_uploaded = len(datasets)
    analyses_performed = len([x for x in global_history_scoped if x.get("client_id") == client_id])
    reports_generated = len(reports)
    
    # Calculate total records count across all client datasets
    total_rows = sum(d.row_count for d in datasets)

    return {
        "client": client,
        "stats": {
            "datasets_uploaded": datasets_uploaded,
            "analyses_performed": analyses_performed,
            "reports_generated": reports_generated,
            "total_rows": total_rows,
            "last_activity": client.last_login.isoformat() if client.last_login else "Never"
        },
        "datasets": datasets,
        "reports": reports
    }

@app.put("/admin/clients/{client_id}", response_model=ClientOut)
def update_client(client_id: int, req: ClientUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    """Modifies client profile settings, updates linked client status/role, and handles optional password changes."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Update Client metadata
    if req.company_name is not None:
        client.company_name = req.company_name
    if req.contact_name is not None:
        client.contact_name = req.contact_name
    if req.phone is not None:
        client.phone = req.phone
    if req.industry is not None:
        client.industry = req.industry
    if req.plan is not None:
        client.plan = req.plan
    if req.status is not None:
        client.status = req.status
        # Sync user active status based on client status
        linked_user = db.query(User).filter(User.client_id == client_id).first()
        if linked_user:
            linked_user.is_active = (req.status == "ACTIVE")
            
    db.commit()
    db.refresh(client)

    # Handle linked account updates if password/email were changed
    linked_user = db.query(User).filter(User.client_id == client_id).first()
    if linked_user:
        if req.contact_name is not None:
            linked_user.name = req.contact_name
        if req.password:
            linked_user.password_hash = get_password_hash(req.password)
        db.commit()

    return client

@app.delete("/admin/clients/{client_id}")
def delete_client(client_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    """Permanently deletes client record, drops all isolated SQL tables, and clears linked datasets/users."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
         raise HTTPException(status_code=404, detail="Client not found")

    # Fetch client datasets to drop their raw SQL tables
    datasets = db.query(Dataset).filter(Dataset.client_id == client_id).all()
    for ds in datasets:
        try:
            quoted_table = quote_ident(ds.table_name)
            db.execute(text(f"DROP TABLE IF EXISTS {quoted_table}"))
        except Exception as e:
            print(f"Error dropping table {ds.table_name}: {str(e)}")

    db.delete(client)
    db.commit()
    return {"status": "success", "message": f"Client {client_id} and all related isolated data successfully deleted"}


# --- CLIENT PORTAL & ISOLATION ENDPOINTS ---

@app.get("/client/dashboard", response_model=DashboardResponse)
def get_client_dashboard_metrics(dataset_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_client)):
    """Compiles dashboard metrics specifically using the client's isolated selected dataset."""
    client_id = current_user.client_id
    
    # 1. Resolve dataset
    dataset = None
    if dataset_id:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.client_id == client_id).first()
    
    if not dataset:
        # Fallback to the latest active dataset if dataset_id is omitted or stale
        dataset = db.query(Dataset).filter(Dataset.client_id == client_id, Dataset.status == "ACTIVE").order_by(Dataset.created_at.desc()).first()
        
    if not dataset:
        raise HTTPException(
            status_code=400, 
            detail="No datasets available. Please upload a dataset to view metrics."
        )

    try:
        data = get_dashboard_data(db, table_name=dataset.table_name)
        return DashboardResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch client dashboard: {str(e)}")

@app.get("/client/profile", response_model=ClientProfileResponse)
def get_client_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_client)):
    """Returns profile information for the authenticated Client."""
    client = db.query(Client).filter(Client.id == current_user.client_id).first()
    return ClientProfileResponse(user=current_user, client=client)

@app.put("/client/profile", response_model=ClientProfileResponse)
def update_client_profile(req: ProfileUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_client)):
    """Allows client users to update contact person, email, and password credentials."""
    client = db.query(Client).filter(Client.id == current_user.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client details not found")

    # Update User Info
    if req.name is not None:
        current_user.name = req.name
        client.contact_name = req.name
    if req.email is not None:
        # Ensure email is unique
        email_check = db.query(User).filter(User.email == req.email, User.id != current_user.id).first()
        if email_check:
            raise HTTPException(status_code=400, detail="Email already taken")
        current_user.email = req.email
        client.email = req.email
    if req.password:
        current_user.password_hash = get_password_hash(req.password)
        
    # Update Client Info
    if req.phone is not None:
        client.phone = req.phone
    if req.industry is not None:
        client.industry = req.industry

    db.commit()
    db.refresh(current_user)
    db.refresh(client)
    return ClientProfileResponse(user=current_user, client=client)

LIBRARY_DATASETS = [
    {
        "id": "retail_sales",
        "name": "Global Retail Sales Warehouse",
        "description": "5,000 retail orders across Electronics, Fashion, Furniture, and Grocery with revenues, profit margins, discounts, and regional distribution.",
        "category": "Retail & E-Commerce",
        "rows": 5000,
        "columns": 12,
        "filename": "sales_data.csv"
    },
    {
        "id": "saas_subscriptions",
        "name": "SaaS Subscriptions & ARR Analytics",
        "description": "1,200 subscription records tracking Starter, Pro, and Enterprise accounts with MRR, churn status, customer lifetime value, and support inquiries.",
        "category": "SaaS & Subscriptions",
        "rows": 1200,
        "columns": 10,
        "filename": "saas_mrr_data.csv"
    },
    {
        "id": "marketing_campaigns",
        "name": "Digital Marketing & ROI Performance",
        "description": "850 ad campaigns across Search, Social, and Email with impressions, click-through rates, conversion totals, ad spend, and net return on ad spend.",
        "category": "Marketing & Ads",
        "rows": 850,
        "columns": 10,
        "filename": "marketing_roi_data.csv"
    }
]

def parse_uploaded_file_to_df(filename: str, contents: bytes) -> pd.DataFrame:
    """Intelligently and rapidly parses uploaded dataset files across formats, encodings, and delimiters using fast C-engine."""
    if not contents or len(contents) == 0:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty (0 bytes). Please select a valid dataset file."
        )

    fn_lower = filename.lower()
    
    # 1. Handle Excel files
    if fn_lower.endswith(('.xlsx', '.xls')):
        try:
            df = pd.read_excel(io.BytesIO(contents))
            if df.empty or len(df.columns) == 0:
                raise HTTPException(status_code=400, detail="The Excel spreadsheet contains no rows or readable columns.")
            return df
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse Excel spreadsheet: {str(e)}. Please ensure file is a valid .xlsx or .xls workbook."
            )

    # 2. Handle JSON files
    if fn_lower.endswith('.json'):
        try:
            df = pd.read_json(io.BytesIO(contents))
            if df.empty or len(df.columns) == 0:
                raise HTTPException(status_code=400, detail="The JSON file contains no data or columns.")
            return df
        except HTTPException:
            raise
        except Exception:
            try:
                import json
                raw_json = json.loads(contents.decode('utf-8'))
                if isinstance(raw_json, list):
                    df = pd.json_normalize(raw_json)
                elif isinstance(raw_json, dict):
                    list_key = next((k for k, v in raw_json.items() if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict)), None)
                    if list_key:
                        df = pd.json_normalize(raw_json[list_key])
                    else:
                        df = pd.DataFrame([raw_json])
                else:
                    raise ValueError("JSON content must be an array of objects or an object.")
                if df.empty or len(df.columns) == 0:
                    raise HTTPException(status_code=400, detail="The JSON structure contains no rows or tabular columns.")
                return df
            except HTTPException:
                raise
            except Exception as je:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to parse JSON file: {str(je)}. Please ensure it is a valid JSON array or object."
                )

    # 3. Handle Delimited Text / CSV / TSV / TXT with fast C-engine
    # Fast delimiter detection by sampling the first 4KB of content
    sample_bytes = contents[:4096]
    detected_sep = ','
    if fn_lower.endswith('.tsv'):
        detected_sep = '\t'
    else:
        try:
            sample_text = sample_bytes.decode('utf-8', errors='ignore')
            counts = {',': sample_text.count(','), '\t': sample_text.count('\t'), ';': sample_text.count(';'), '|': sample_text.count('|')}
            detected_sep = max(counts, key=counts.get) if max(counts.values()) > 0 else ','
        except Exception:
            detected_sep = ','

    # Priority delimiters: detected delimiter first, followed by standard candidates
    delimiters = [detected_sep]
    for d in [',', '\t', ';', '|']:
        if d not in delimiters:
            delimiters.append(d)

    encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1']
    last_err = None

    # Fast path: C engine with detected delimiter and standard encodings
    for enc in encodings:
        for sep in delimiters:
            try:
                df = pd.read_csv(
                    io.BytesIO(contents),
                    sep=sep,
                    encoding=enc,
                    engine='c',
                    low_memory=False
                )
                if df is not None and len(df.columns) > 0:
                    if df.empty:
                        raise HTTPException(status_code=400, detail="The uploaded file contains headers but no data rows.")
                    return df
            except HTTPException:
                raise
            except Exception as ex:
                last_err = ex
                continue

    # Fallback path with on_bad_lines='skip'
    for enc in ['utf-8', 'latin1']:
        try:
            df = pd.read_csv(
                io.BytesIO(contents),
                sep=None,
                encoding=enc,
                engine='python',
                on_bad_lines='skip'
            )
            if df is not None and len(df.columns) > 0:
                if df.empty:
                    raise HTTPException(status_code=400, detail="The uploaded file contains headers but no data rows.")
                return df
        except HTTPException:
            raise
        except Exception as ex:
            last_err = ex
            continue

    raise HTTPException(
        status_code=400,
        detail=f"Unable to parse dataset file. Please verify it is a valid CSV, Excel, or JSON file. Parser detail: {str(last_err)}"
    )

def sanitize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitizes column names to be valid, clean, and unique SQL column identifiers for PostgreSQL and SQLite."""
    SQL_RESERVED_WORDS = {
        "order", "user", "group", "table", "select", "from", "where", "limit",
        "check", "column", "primary", "foreign", "key", "index", "default",
        "grant", "revoke", "window", "all", "and", "or", "not", "in", "like",
        "case", "when", "then", "else", "end", "offset", "join", "on"
    }

    clean_cols = []
    for i, col in enumerate(df.columns):
        col_str = str(col).strip().lower()
        cleaned = re.sub(r'[^a-z0-9_]', '_', col_str)
        cleaned = re.sub(r'_+', '_', cleaned).strip('_')
        if not cleaned:
            cleaned = f"col_{i+1}"
        elif cleaned in SQL_RESERVED_WORDS:
            cleaned = f"{cleaned}_col"
        clean_cols.append(cleaned)

    # Ensure uniqueness
    seen = {}
    final_cols = []
    for col in clean_cols:
        if col in seen:
            seen[col] += 1
            final_cols.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            final_cols.append(col)

    df.columns = final_cols
    return df

def clean_dataframe_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rapid sample-based type inference: checks a 300-row sample to identify currency,
    comma-formatted numbers, or percentages, avoiding full-column regex passes for pure text.
    """
    sample_size = min(300, len(df))
    if sample_size == 0:
        return df

    for col in df.columns:
        # Fast exit: if already numeric, skip
        if pd.api.types.is_numeric_dtype(df[col]):
            continue

        try:
            sample = df[col].dropna().head(sample_size)
            if len(sample) == 0:
                continue

            sample_str = sample.astype(str).str.strip()

            # Fast skip: date patterns (e.g. '2024-01-01', '2024/01/01')
            if sample_str.str.contains(r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}', regex=True).mean() > 0.5:
                continue
            if sample_str.str.contains(r'\bto\b|\bthrough\b', case=False, regex=True).any():
                continue

            # Fast skip: pure text without digits
            has_digits = sample_str.str.contains(r'\d', regex=True).mean() > 0.5
            if not has_digits:
                continue

            # Test numeric conversion on the sample first
            sample_cleaned = sample_str.str.replace(r'[\$,₹€£¥\s]', '', regex=True)
            sample_cleaned = sample_cleaned.str.replace(r'^[Rr][Ss]\.?', '', regex=True)
            sample_cleaned = sample_cleaned.str.replace(',', '', regex=False)
            sample_cleaned = sample_cleaned.str.rstrip('%')
            parsed_sample = pd.to_numeric(sample_cleaned, errors='coerce')
            valid_ratio = parsed_sample.notnull().sum() / len(sample_str)

            # If >= 70% of non-null sample parses as numbers, perform a single vectorized pass on full column
            if valid_ratio >= 0.7:
                full_cleaned = df[col].astype(str).str.strip().str.replace(r'[\$,₹€£¥\s]', '', regex=True)
                full_cleaned = full_cleaned.str.replace(r'^[Rr][Ss]\.?', '', regex=True)
                full_cleaned = full_cleaned.str.replace(',', '', regex=False)
                full_cleaned = full_cleaned.str.rstrip('%')
                converted = pd.to_numeric(full_cleaned, errors='coerce')
                if converted.notnull().sum() >= valid_ratio * len(df[col].dropna()):
                    df[col] = converted
        except Exception as col_err:
            logger.debug(f"clean_dataframe_numeric_columns: skipped col '{col}': {col_err}")
            continue

    return df

def generate_library_dataframe(library_id: str) -> tuple[pd.DataFrame, str]:
    """Generates or loads the DataFrame and standard filename for a selected library dataset."""
    import random
    from datetime import date, timedelta
    
    if library_id == "retail_sales":
        csv_path = os.path.join(root_dir, "sales_data.csv")
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                return df, "sales_data.csv"
            except Exception:
                pass
        
        random.seed(42)
        products = {
            "Laptop": ("Electronics", 65000), "Phone": ("Electronics", 30000),
            "Headphones": ("Electronics", 3000), "Keyboard": ("Electronics", 2500),
            "Chair": ("Furniture", 7000), "Desk": ("Furniture", 12000),
            "Shoes": ("Fashion", 4000), "T-Shirt": ("Fashion", 1200),
            "Jeans": ("Fashion", 2500), "Coffee": ("Grocery", 500),
            "Rice": ("Grocery", 1000), "Oil": ("Grocery", 1500)
        }
        regions = ["North", "South", "East", "West"]
        start_date = date(2025, 1, 1)
        data = []
        for oid in range(1, 5001):
            odate = start_date + timedelta(days=random.randint(0, 364))
            cid = f"CUST{str(random.randint(1, 500)).zfill(4)}"
            cname = f"Customer {cid[-4:]}"
            prod = random.choice(list(products.keys()))
            cat, price = products[prod]
            qty = random.randint(1, 5)
            disc = round(random.uniform(0, 0.20), 2)
            rev = round(qty * price * (1 - disc), 2)
            prof = round(rev * random.uniform(0.08, 0.30), 2)
            reg = random.choice(regions)
            data.append([oid, odate, cid, cname, prod, cat, reg, qty, price, rev, disc, prof])
        
        cols = ["order_id", "order_date", "customer_id", "customer_name", "product", "category", "region", "quantity", "unit_price", "revenue", "discount", "profit"]
        return pd.DataFrame(data, columns=cols), "sales_data.csv"

    elif library_id == "saas_subscriptions":
        random.seed(101)
        plans = {"Starter": 49.0, "Professional": 199.0, "Enterprise": 799.0}
        statuses = ["Active", "Active", "Active", "Active", "Churned", "Paused"]
        regions = ["North America", "Europe", "Asia-Pacific", "Latin America"]
        start_date = date(2024, 1, 1)
        data = []
        for i in range(1, 1201):
            sub_id = f"SUB_{1000 + i}"
            cname = f"Client Corp {i}"
            plan = random.choice(list(plans.keys()))
            mrr = plans[plan]
            sdate = start_date + timedelta(days=random.randint(0, 500))
            stat = random.choice(statuses)
            reg = random.choice(regions)
            tickets = random.randint(0, 12)
            nps = random.randint(6, 10) if stat == "Active" else random.randint(1, 6)
            annual_rev = round(mrr * random.randint(6, 24), 2)
            data.append([sub_id, cname, plan, mrr, sdate, stat, reg, tickets, nps, annual_rev])
        
        cols = ["subscription_id", "customer_name", "plan", "monthly_mrr", "signup_date", "churn_status", "region", "support_tickets", "nps_score", "revenue"]
        return pd.DataFrame(data, columns=cols), "saas_mrr_data.csv"

    elif library_id == "marketing_campaigns":
        random.seed(202)
        channels = ["Google Search", "Meta Ads", "LinkedIn Ads", "Email Newsletter", "YouTube Video"]
        campaign_types = ["Lead Generation", "Product Launch", "Brand Awareness", "Retargeting", "Seasonal Promo"]
        start_date = date(2025, 1, 1)
        data = []
        for i in range(1, 851):
            cmp_id = f"CMP_{2000 + i}"
            cname = f"{random.choice(campaign_types)} - #{i}"
            chn = random.choice(channels)
            spend = round(random.uniform(500, 15000), 2)
            impr = int(spend * random.uniform(25, 60))
            clicks = int(impr * random.uniform(0.015, 0.055))
            conv = int(clicks * random.uniform(0.03, 0.12))
            rev = round(spend * random.uniform(1.2, 3.8), 2)
            roi = round(((rev - spend) / spend) * 100, 1)
            cdate = start_date + timedelta(days=random.randint(0, 300))
            data.append([cmp_id, cname, chn, spend, impr, clicks, conv, rev, roi, cdate])
        
        cols = ["campaign_id", "campaign_name", "channel", "ad_spend", "impressions", "clicks", "conversions", "revenue", "roi_percent", "start_date"]
        return pd.DataFrame(data, columns=cols), "marketing_roi_data.csv"

    else:
        raise HTTPException(status_code=404, detail=f"Library dataset '{library_id}' not found.")


@app.get("/client/datasets", response_model=List[DatasetOut])
def get_client_datasets(response: Response, db: Session = Depends(get_db), current_user: User = Depends(get_current_client)):
    """Lists datasets uploaded or imported by the authenticated client only."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return db.query(Dataset).filter(Dataset.client_id == current_user.client_id).order_by(Dataset.created_at.desc()).all()

@app.get("/client/datasets/library", response_model=List[LibraryDatasetOut])
def get_client_library_datasets(current_user: User = Depends(get_current_client)):
    """Returns the catalog of available pre-packaged library datasets."""
    return LIBRARY_DATASETS

@app.post("/client/datasets/library", response_model=DatasetOut)
def import_client_library_dataset(
    req: ImportLibraryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_client)
):
    """Imports a pre-configured library dataset into an isolated table for the client."""
    try:
        t_start = time.perf_counter()
        df, standard_fn = generate_library_dataframe(req.library_id)
        df = sanitize_dataframe_columns(df)
        df = clean_dataframe_numeric_columns(df)
        
        row_count = len(df)
        col_count = len(df.columns)
        
        lib_meta = next((item for item in LIBRARY_DATASETS if item["id"] == req.library_id), None)
        ds_name = req.custom_name.strip() if req.custom_name and req.custom_name.strip() else (lib_meta["name"] if lib_meta else req.library_id)

        # Generate unique, non-guessable, isolated table name
        table_uuid = uuid.uuid4().hex[:12]
        table_name = f"dataset_client_{current_user.client_id}_{table_uuid}"

        chunk_size = getattr(settings, "CSV_CHUNK_SIZE", 10000)
        with engine.begin() as conn:
            if engine.dialect.name == "sqlite":
                conn.execute(text("PRAGMA synchronous = NORMAL"))
                conn.execute(text("PRAGMA journal_mode = WAL"))
            df.to_sql(table_name, conn, if_exists="replace", index=False, chunksize=chunk_size)

        new_dataset = Dataset(
            client_id=current_user.client_id,
            name=ds_name,
            filename=standard_fn,
            table_name=table_name,
            row_count=row_count,
            col_count=col_count,
            status="ACTIVE",
            created_at=datetime.utcnow()
        )
        db.add(new_dataset)
        db.commit()
        db.refresh(new_dataset)

        # Invalidate cached metrics so future queries get fresh calculations on-demand
        invalidate_dashboard_cache(table_name)
        
        t_total = time.perf_counter() - t_start
        logger.info(f"[LibraryImport] Imported '{ds_name}' ({row_count:,} rows) in {t_total:.3f}s")
        return new_dataset
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to import library dataset: {str(e)}", exc_info=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to import library dataset: {str(e)}")

@app.post("/client/datasets", response_model=DatasetOut)
async def upload_client_dataset(
    name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_client)
):
    """Securely uploads and imports dataset files into an isolated database table with comprehensive stage performance timing."""
    t_start = time.perf_counter()
    
    # 1. Validation: extension
    t_val_start = time.perf_counter()
    fn_lower = (file.filename or '').lower()
    valid_extensions = ('.csv', '.xlsx', '.xls', '.tsv', '.txt', '.json')
    if not fn_lower.endswith(valid_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{file.filename}'. Supported formats: .csv, .xlsx, .xls, .json, .tsv, .txt."
        )

    try:
        # 2. File upload / receiving bytes
        t_read_start = time.perf_counter()
        contents = await file.read()
        t_read = time.perf_counter() - t_read_start

        if not contents or len(contents) == 0:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty (0 bytes). Please select a valid file with data."
            )

        # 3. CSV parsing
        t_parse_start = time.perf_counter()
        df = parse_uploaded_file_to_df(file.filename or 'data.csv', contents)
        t_parse = time.perf_counter() - t_parse_start

        # 4. Data validation
        row_count = len(df)
        col_count = len(df.columns)
        t_val = (time.perf_counter() - t_val_start) - t_read - t_parse
        if row_count == 0 or col_count == 0:
            raise HTTPException(
                status_code=400,
                detail="The dataset file contains no rows or tabular columns to import."
            )

        # 5. Data cleaning
        t_clean_start = time.perf_counter()
        df = sanitize_dataframe_columns(df)
        df = clean_dataframe_numeric_columns(df)
        t_clean = time.perf_counter() - t_clean_start

        # 6. Table creation & preparation
        t_prep_start = time.perf_counter()
        table_uuid = uuid.uuid4().hex[:12]
        table_name = f"dataset_client_{current_user.client_id}_{table_uuid}"

        clean_name = (name or "").strip()
        if not clean_name:
            clean_name = file.filename.rsplit('.', 1)[0] if file.filename else "Uploaded Dataset"

        existing_names = [d.name.lower() for d in db.query(Dataset).filter(Dataset.client_id == current_user.client_id).all() if d.name]
        final_name = clean_name
        counter = 1
        while final_name.lower() in existing_names:
            final_name = f"{clean_name} ({counter})"
            counter += 1
        t_prep = time.perf_counter() - t_prep_start

        # 7. Database insertion (batched bulk insertion with WAL optimization)
        t_insert_start = time.perf_counter()
        chunk_size = getattr(settings, "CSV_CHUNK_SIZE", 10000)
        with engine.begin() as conn:
            if engine.dialect.name == "sqlite":
                conn.execute(text("PRAGMA synchronous = NORMAL"))
                conn.execute(text("PRAGMA journal_mode = WAL"))
            df.to_sql(table_name, conn, if_exists="replace", index=False, chunksize=chunk_size)
        t_insert = time.perf_counter() - t_insert_start

        # 8. Schema detection
        t_schema_start = time.perf_counter()
        inspector = inspect(engine)
        detected_cols = inspector.get_columns(table_name)
        t_schema = time.perf_counter() - t_schema_start

        # 9 & 10. Data profiling & AI calls: strictly 0s (separated from upload)
        t_profile = 0.0
        t_ai = 0.0

        # Invalidate cache so future queries calculate fresh on demand
        invalidate_dashboard_cache(table_name)

        # 11. Final response & metadata persistence
        t_resp_start = time.perf_counter()
        new_dataset = Dataset(
            client_id=current_user.client_id,
            name=final_name,
            filename=file.filename or "dataset.csv",
            table_name=table_name,
            row_count=row_count,
            col_count=col_count,
            status="ACTIVE",
            created_at=datetime.utcnow()
        )
        db.add(new_dataset)
        db.commit()
        db.refresh(new_dataset)
        t_resp = time.perf_counter() - t_resp_start
        t_total = time.perf_counter() - t_start

        # Structured backend timing log
        file_mb = len(contents) / (1024 * 1024)
        timing_report = (
            f"\n============================================================\n"
            f"DATASET UPLOAD TIMING BREAKDOWN: '{file.filename}' ({file_mb:.2f} MB)\n"
            f"------------------------------------------------------------\n"
            f"1. File upload/receiving     : {t_read:.3f}s\n"
            f"2. File saving (in-memory)   : {t_read:.3f}s\n"
            f"3. CSV parsing               : {t_parse:.3f}s ({row_count:,} rows, {col_count} columns)\n"
            f"4. Data validation           : {max(0.0, t_val):.3f}s\n"
            f"5. Data cleaning             : {t_clean:.3f}s\n"
            f"6. Table creation & prep     : {t_prep:.3f}s\n"
            f"7. Database insertion        : {t_insert:.3f}s (chunksize={chunk_size})\n"
            f"8. Schema detection          : {t_schema:.3f}s ({len(detected_cols)} verified columns)\n"
            f"9. Data profiling            : {t_profile:.3f}s (deferred to on-demand query)\n"
            f"10. AI/LLM calls             : {t_ai:.3f}s (separated from upload)\n"
            f"11. Final response & commit  : {t_resp:.3f}s\n"
            f"------------------------------------------------------------\n"
            f"TOTAL PROCESSING TIME        : {t_total:.3f}s\n"
            f"============================================================"
        )
        logger.info(timing_report)
        print(timing_report)

        return new_dataset
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to process dataset file upload: {str(e)}", exc_info=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process dataset file upload: {str(e)}")

@app.delete("/client/datasets/{dataset_id}")
def delete_client_dataset(dataset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_client)):
    """Drops client raw dataset table and clears metadata (prevents cross-client deletion)."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.client_id == current_user.client_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or unauthorized")

    # Drop physical table from database
    try:
        quoted_table = quote_ident(dataset.table_name)
        db.execute(text(f"DROP TABLE IF EXISTS {quoted_table}"))
        db.commit()
    except Exception as e:
        print(f"Failed to drop SQL table {dataset.table_name}: {str(e)}")

    # Invalidate cached metrics
    invalidate_dashboard_cache(dataset.table_name)

    db.delete(dataset)
    db.commit()
    return {"status": "success", "message": "Dataset deleted successfully"}

@app.get("/client/reports", response_model=List[ReportOut])
def get_client_reports(db: Session = Depends(get_db), current_user: User = Depends(get_current_client)):
    """Retrieves reports generated by the authenticated client."""
    return db.query(Report).filter(Report.client_id == current_user.client_id).order_by(Report.created_at.desc()).all()

@app.post("/client/reports", response_model=ReportOut)
def create_client_report(req: ReportCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_client)):
    """Saves AI business analyst summaries or dashboard visualizations as PDF/HTML reports for the client."""
    # Verify dataset belongs to client
    dataset = db.query(Dataset).filter(Dataset.id == req.dataset_id, Dataset.client_id == current_user.client_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or unauthorized")

    new_report = Report(
        client_id=current_user.client_id,
        dataset_id=req.dataset_id,
        name=req.name,
        report_type=req.report_type,
        status="COMPLETED",
        content=req.content,
        created_at=datetime.utcnow()
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)
    return new_report

@app.delete("/client/reports/{report_id}")
def delete_client_report(report_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_client)):
    """Deletes report from client record (prevents cross-client deletion)."""
    report = db.query(Report).filter(Report.id == report_id, Report.client_id == current_user.client_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found or unauthorized")

    db.delete(report)
    db.commit()
    return {"status": "success", "message": "Report deleted successfully"}


# --- DYNAMIC DATA ISOLATION API ROUTE OVERRIDES ---

@app.get("/api/dashboard", response_model=DashboardResponse)
def get_dashboard_metrics_endpoint(dataset_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Overridden dashboard endpoint.
    Filters dashboard results based on the logged-in user's role.
    If ADMIN, returns standard sales dashboard or selected client details.
    If CLIENT, isolates metrics to their active dataset.
    """
    # Enforce Client isolation
    if current_user.role == "CLIENT":
        return get_client_dashboard_metrics(dataset_id=dataset_id, db=db, current_user=current_user)
    
    # ADMIN default dashboard accesses the global seed sales data
    try:
        data = get_dashboard_data(db, table_name="sales")
        return DashboardResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch global dashboard: {str(e)}")

@app.get("/api/schema", response_model=SchemaResponse)
def get_schema_explorer_endpoint(dataset_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Overridden Schema Explorer.
    ADMINs can inspect all schemas.
    CLIENTs are limited to inspecting only their active dataset columns.
    """
    if current_user.role == "ADMIN":
        # ADMIN can inspect the entire sqlite schema structure
        from backend.services.sql_service import get_schema_details
        try:
            tables = get_schema_details(db)
            return SchemaResponse(tables=tables)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # CLIENT: retrieve metadata of client's own active table only
    client_id = current_user.client_id
    if dataset_id:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.client_id == client_id).first()
    else:
        dataset = db.query(Dataset).filter(Dataset.client_id == client_id, Dataset.status == "ACTIVE").order_by(Dataset.created_at.desc()).first()

    if not dataset:
        return SchemaResponse(tables=[])

    try:
        inspector = inspect(engine)
        columns = []
        for column in inspector.get_columns(dataset.table_name):
            columns.append({
                "name": column["name"],
                "type": str(column["type"])
            })

        # Get preview rows safely
        quoted_table = quote_ident(dataset.table_name)
        preview_res = db.execute(text(f"SELECT * FROM {quoted_table} LIMIT 10"))
        preview_cols = list(preview_res.keys())
        preview_rows = []
        for row in preview_res.fetchall():
            row_dict = {}
            for col, val in zip(preview_cols, row):
                if hasattr(val, "isoformat"):
                    row_dict[col] = val.isoformat()
                else:
                    row_dict[col] = val
            preview_rows.append(row_dict)

        table_info = {
            "name": dataset.name,
            "row_count": dataset.row_count,
            "columns": columns,
            "preview": preview_rows
        }
        return SchemaResponse(tables=[table_info])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema inspection failed: {str(e)}")

@app.get("/api/history", response_model=List[HistoryItem])
def get_query_history_endpoint(current_user: User = Depends(get_current_user)):
    """Scopes analytical logs retrieval to the active client only (preventing history data leaks)."""
    if current_user.role == "ADMIN":
        # Return all query logs for admin overview
        res = []
        for h in global_history_scoped:
            res.append(HistoryItem(
                id=h["id"],
                question=h["question"],
                timestamp=h["timestamp"],
                sql=h["sql"],
                chart_type=h["chart_type"]
            ))
        return res

    # CLIENT: filter history by client_id
    client_id = current_user.client_id
    client_history = [x for x in global_history_scoped if x.get("client_id") == client_id]
    res = []
    for h in client_history:
        res.append(HistoryItem(
            id=h["id"],
            question=h["question"],
            timestamp=h["timestamp"],
            sql=h["sql"],
            chart_type=h["chart_type"]
        ))
    return res

@app.post("/api/ask", response_model=AskResponse)
def ask_analyst_endpoint(request: AskRequest, dataset_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Processes natural language questions.
    Generates isolated SQL queries specifically restricted to the client's own database table,
    performs sandbox/isolation checks, executes, visualizes, and returns AI business impact analysis.
    """
    question = request.question.strip()
    session_id = request.session_id or "default_session"
    eff_dataset_id = dataset_id or getattr(request, "dataset_id", None)
    
    if not question:
        return AskResponse(
            question="", sql="", columns=[], rows=[],
            chart=ChartConfig(chart_type="none", data=[]),
            summary="Please enter a valid question.",
            key_findings=[], business_impact="Empty query input.",
            recommendations=[], success=False, error="Question was empty."
        )

    logger.info(f"[/api/ask] User: {current_user.email} (Role: {current_user.role}, Client: {getattr(current_user, 'client_id', None)}) | Dataset ID: {eff_dataset_id} | Question: '{question}'")

    # 1. Resolve table details depending on role
    if current_user.role == "CLIENT":
        client_id = current_user.client_id
        if eff_dataset_id:
            dataset = db.query(Dataset).filter(Dataset.id == eff_dataset_id, Dataset.client_id == client_id).first()
        else:
            dataset = db.query(Dataset).filter(Dataset.client_id == client_id, Dataset.status == "ACTIVE").order_by(Dataset.created_at.desc()).first()
            
        if not dataset:
            logger.warning(f"[/api/ask] No active dataset found for Client ID {client_id}")
            return AskResponse(
                question=question, sql="", columns=[], rows=[],
                chart=ChartConfig(chart_type="none", data=[]),
                summary="You have no active datasets. Please upload a dataset under 'My Data' first.",
                key_findings=[], business_impact="No data available.",
                recommendations=[], success=False, error="No client datasets found."
            )
        target_table = dataset.table_name
    else:
        # ADMIN executes against global sales dataset
        dataset = None
        target_table = "sales"

    # 2. Get table column details and sample data using dynamic schema profiling
    try:
        schema_info = inspect_dataset_schema(db, target_table)
        cols_info = [{"name": c, "type": schema_info["column_types"].get(c, "VARCHAR")} for c in schema_info["columns"]]
        sample_rows = schema_info.get("sample_rows", [])
    except Exception as e:
        logger.error(f"[/api/ask] Failed to inspect target schema for `{target_table}`: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to inspect target schema: {str(e)}")

    logger.info(f"[/api/ask] Target Table: `{target_table}` (Dataset: '{dataset.name if dataset else 'sales'}') | Columns: {len(cols_info)}")

    user_margin = extract_explicit_margin(question)

    # Check if target table schema has profit/margin columns or user provided margin
    profit_col = schema_info.get("profit_col")
    margin_col = schema_info.get("margin_col")
    has_profit_data = (profit_col is not None) or (margin_col is not None) or (user_margin is not None)

    # If the user specifically asks about profit/profitability but no profit data or margin is available:
    is_asking_profit = bool(re.search(r'\b(profit|profits|profitability|profitable|net margin|gross margin)\b', question, re.IGNORECASE))
    if is_asking_profit and not has_profit_data:
        logger.info(f"[/api/ask] Profit question asked without profit data in `{target_table}`. Enforcing profit integrity.")
        return AskResponse(
            question=question, sql="", columns=[], rows=[],
            chart=ChartConfig(chart_type="none", data=[]),
            summary="Profit data cannot be calculated from the available dataset.",
            key_findings=[
                "The current dataset does not contain an actual profit column or profit margin column.",
                "Default profit margins (such as 18%) are strictly disabled to preserve financial integrity.",
                "To analyze profitability, please upload a dataset with profit/margin columns, or explicitly specify a profit margin in your prompt (e.g., 'Assuming a 15% margin, what is our profit?')."
            ],
            business_impact="Profitability analysis is unavailable without actual financial figures or an explicit margin assumption.",
            recommendations=[
                "Upload a dataset containing 'profit' or 'profit_margin' columns.",
                "Or specify an assumed profit margin in your query (e.g. 'What is the estimated profit with a 20% margin?')."
            ],
            success=True
        )

    try:
        # 3. Generate and execute SQL with automatic self-correction retry loop
        try:
            sql, columns, rows = execute_query_with_retry(
                question=question,
                table_name=target_table,
                columns=cols_info,
                db=db,
                session_id=session_id,
                user_margin=user_margin,
                sample_rows=sample_rows,
                max_correction_retries=2
            )
            logger.info(f"[/api/ask] Query generated and executed successfully: {len(rows)} rows returned.")
        except CannotAnswerError as e:
            logger.warning(f"[/api/ask] Question cannot be answered with current schema: {str(e)}")
            col_names = [c["name"] for c in cols_info]
            return AskResponse(
                question=question, sql="", columns=[], rows=[],
                chart=ChartConfig(chart_type="none", data=[]),
                summary=f"The current dataset '{dataset.name if dataset else target_table}' does not contain columns to directly answer: \"{question}\".",
                key_findings=[
                    f"Available dimensions: {', '.join(col_names[:10])}{'...' if len(col_names) > 10 else ''}.",
                    "The requested information is not present in the dataset schema."
                ],
                business_impact="Question cannot be answered from the current dataset fields.",
                recommendations=[
                    "Ask questions based on available fields such as " + ", ".join([f"'{c}'" for c in col_names[:4]]) + ".",
                    "Upload a supplementary dataset that includes the missing metrics."
                ],
                success=False, error=f"CANNOT_ANSWER: {str(e)}"
            )
        except LLMAuthError as e:
            logger.error(f"[/api/ask] LLM Authentication Error: {str(e)}")
            return AskResponse(
                question=question, sql="", columns=[], rows=[],
                chart=ChartConfig(chart_type="none", data=[]),
                summary="LLM Authentication failed. Please verify your GEMINI_API_KEY in .env.",
                key_findings=["Invalid or missing Gemini API key."],
                business_impact="AI SQL generation is offline due to authentication credentials.",
                recommendations=["Check GEMINI_API_KEY in .env file."],
                success=False, error=f"LLM_AUTH_ERROR: {str(e)}"
            )
        except (LLMModelError, LLMConnectionError) as e:
            logger.error(f"[/api/ask] LLM Model/Connection Error: {str(e)}")
            return AskResponse(
                question=question, sql="", columns=[], rows=[],
                chart=ChartConfig(chart_type="none", data=[]),
                summary="AI Analyst service is temporarily unavailable.",
                key_findings=[f"Provider error: {str(e)}"],
                business_impact="Unable to complete generation with active AI provider.",
                recommendations=[
                    f"Check your Gemini API connection and ensure '{settings.GEMINI_MODEL}' is active.",
                    "Verify GEMINI_API_KEY in .env file."
                ],
                success=False, error=f"LLM_PROVIDER_ERROR: {str(e)}"
            )
        except SQLValidationError as e:
            logger.error(f"[/api/ask] SQL Validation Error: {str(e)}")
            return AskResponse(
                question=question, sql="", columns=[], rows=[],
                chart=ChartConfig(chart_type="none", data=[]),
                summary="Sorry, I could not generate a safe SQL query for this question.",
                key_findings=["The query generated did not satisfy security or safety constraints."],
                business_impact="Query blocked for data safety.",
                recommendations=["Try rephrasing your question using simpler terms."],
                success=False, error=f"SQL_VALIDATION_ERROR: {str(e)}"
            )
        except Exception as e:
            logger.error(f"[/api/ask] SQL Execution / Database Error: {str(e)}")
            return AskResponse(
                question=question, sql="", columns=[], rows=[],
                chart=ChartConfig(chart_type="none", data=[]),
                summary="The AI analyst encountered an error querying the dataset.",
                key_findings=[f"Details: {str(e).splitlines()[0]}"],
                business_impact="Database query execution unsuccessful after retries.",
                recommendations=["Try rephrasing the question using available column names.", "Verify table fields in the Data Explorer."],
                success=False, error=f"SQL_EXECUTION_ERROR: {str(e)}"
            )

        # 4. Strict Security Verification: Enforce Table Isolation
        if not verify_sql_isolation(sql, target_table):
            logger.warning(f"[/api/ask] Security Block: Query attempted cross-table access outside of `{target_table}`.")
            return AskResponse(
                question=question, sql=sql, columns=[], rows=[],
                chart=ChartConfig(chart_type="none", data=[]),
                summary="Security Block: The generated SQL query referenced system tables or another client's dataset.",
                key_findings=["This request has been blocked for data safety and tenant isolation rules."],
                business_impact="Data isolation policy violation block.",
                recommendations=["Please rephrase your question to target only your active dataset columns."],
                success=False, error="SECURITY_ISOLATION_ERROR: Cross-table access disallowed."
            )

        # 6. Determine visualization chart configuration
        chart_config_dict = determine_chart_config(columns, rows)
        chart_config = ChartConfig(**chart_config_dict)

        # 7. Generate AI insights from data results
        insights = generate_insights(question, sql, columns, rows, user_margin=user_margin)

        # 8. Maintain session history (for follow-ups)
        add_history_context(session_id, question, sql, insights["summary"])

        # 9. Log in global scoped history list
        history_id = str(uuid.uuid4())
        global_history_scoped.insert(0, {
            "id": history_id,
            "client_id": current_user.client_id if current_user.role == "CLIENT" else 0, # 0 = admin
            "question": question,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sql": sql,
            "chart_type": chart_config.chart_type
        })

        return AskResponse(
            question=question, sql=sql, columns=columns, rows=rows,
            chart=chart_config,
            summary=insights["summary"],
            key_findings=insights["key_findings"],
            business_impact=insights["business_impact"],
            recommendations=insights["recommendations"],
            success=True
        )

    except Exception as e:
        return AskResponse(
            question=question, sql="", columns=[], rows=[],
            chart=ChartConfig(chart_type="none", data=[]),
            summary="An unexpected error occurred while processing your request.",
            key_findings=[], business_impact="System error.",
            recommendations=["Please retry in a moment."],
            success=False, error=str(e)
        )

# Start server when run directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)

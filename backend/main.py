import os
import sys
import uuid
from datetime import datetime
from typing import List

# Add parent directory of backend to sys.path to enable absolute imports
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Add venv site-packages to sys.path programmatically to resolve dependencies
venv_site_packages = os.path.join(root_dir, "venv", "Lib", "site-packages")
if os.path.exists(venv_site_packages) and venv_site_packages not in sys.path:
    sys.path.insert(0, venv_site_packages)

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.connection import get_db
from backend.models.schemas import (
    AskRequest, AskResponse, ChartConfig,
    DashboardResponse, SchemaResponse, HistoryItem
)
from backend.services.sql_service import execute_query, get_schema_details
from backend.services.llm_service import generate_sql, generate_insights, add_history_context
from backend.services.analysis_service import get_dashboard_data
from backend.services.visualization_service import determine_chart_config

# Initialize FastAPI App
app = FastAPI(title="AI Business Analyst API", version="1.0.0")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory list for historical queries (mock database storage for history page)
global_history: List[HistoryItem] = []

@app.get("/api/health")
def health_check():
    """Simple API status checker."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/dashboard", response_model=DashboardResponse)
def get_dashboard_metrics_endpoint(db: Session = Depends(get_db)):
    """
    Returns metrics (Total Revenue, Profit, Orders, Customers, Avg Order Value)
    and chart data compiled from SQLite database using Pandas.
    """
    try:
        data = get_dashboard_data(db)
        return DashboardResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard data: {str(e)}")

@app.get("/api/schema", response_model=SchemaResponse)
def get_schema_explorer_endpoint(db: Session = Depends(get_db)):
    """Returns database tables metadata, columns, and previews for the Data Explorer."""
    try:
        tables = get_schema_details(db)
        return SchemaResponse(tables=tables)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to inspect database schema: {str(e)}")

@app.get("/api/history", response_model=List[HistoryItem])
def get_query_history_endpoint():
    """Returns list of previous user questions and queries."""
    return global_history

@app.post("/api/ask", response_model=AskResponse)
def ask_analyst_endpoint(request: AskRequest, db: Session = Depends(get_db)):
    """
    Processes natural language questions.
    Generates SQL, validates it, executes it, analyzes results, selects charts,
    and creates business insights.
    """
    question = request.question.strip()
    session_id = request.session_id or "default_session"
    
    if not question:
        return AskResponse(
            question="",
            sql="",
            columns=[],
            rows=[],
            chart=ChartConfig(chart_type="none", data=[]),
            summary="Please enter a valid question.",
            key_findings=[],
            business_impact="Empty query input.",
            recommendations=[],
            success=False,
            error="Question was empty."
        )

    try:
        # 1. Natural Language -> SQL via Gemini (incorporating schema + follow-up history)
        try:
            sql = generate_sql(question, session_id=session_id)
        except Exception as e:
            return AskResponse(
                question=question,
                sql="",
                columns=[],
                rows=[],
                chart=ChartConfig(chart_type="none", data=[]),
                summary="Sorry, I could not generate a valid SQL query for this question.",
                key_findings=["Please make sure your question references categories, revenue, profit, regions, or customers in the database."],
                business_impact="Unable to parse question context.",
                recommendations=["Try rephrasing your question.", "Use simpler terms e.g., 'What is our total revenue?'"],
                success=False,
                error=f"SQL Generation Error: {str(e)}"
            )

        # 2. SQL Execution against SQLite (handles safety and execution)
        try:
            columns, rows = execute_query(sql, db)
        except Exception as e:
            return AskResponse(
                question=question,
                sql=sql,
                columns=[],
                rows=[],
                chart=ChartConfig(chart_type="none", data=[]),
                summary="The query generated by the AI analyst encountered a database error.",
                key_findings=["This usually happens if the generated SQL syntax is invalid for SQLite or references missing columns."],
                business_impact="SQL Execution blocked or failed.",
                recommendations=["Try rephrasing the question.", "Verify database fields in the Data Explorer."],
                success=False,
                error=f"Database execution error: {str(e)}"
            )

        # 3. Determine visualization chart configuration
        chart_config_dict = determine_chart_config(columns, rows)
        chart_config = ChartConfig(**chart_config_dict)

        # 4. Generate AI insights from data results
        insights = generate_insights(question, sql, columns, rows)

        # 5. Maintain session history (for follow-ups)
        add_history_context(session_id, question, sql, insights["summary"])

        # 6. Log in global history list
        history_item = HistoryItem(
            id=str(uuid.uuid4()),
            question=question,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            sql=sql,
            chart_type=chart_config.chart_type
        )
        global_history.insert(0, history_item)

        # Return full response
        return AskResponse(
            question=question,
            sql=sql,
            columns=columns,
            rows=rows,
            chart=chart_config,
            summary=insights["summary"],
            key_findings=insights["key_findings"],
            business_impact=insights["business_impact"],
            recommendations=insights["recommendations"],
            success=True
        )

    except Exception as e:
        return AskResponse(
            question=question,
            sql="",
            columns=[],
            rows=[],
            chart=ChartConfig(chart_type="none", data=[]),
            summary="An unexpected error occurred while processing your request.",
            key_findings=[],
            business_impact="System error.",
            recommendations=["Please retry in a moment."],
            success=False,
            error=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    # Start server when run directly
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)

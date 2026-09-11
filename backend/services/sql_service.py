import time
import os
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from backend.database.connection import engine, quote_ident
from backend.utils.sql_validator import is_safe_sql

def get_db_schema() -> dict:
    """
    Returns the schema of the SQLite database: table names, column names, and types.
    """
    inspector = inspect(engine)
    schema_info = {}
    
    for table_name in inspector.get_table_names():
        columns = []
        for column in inspector.get_columns(table_name):
            columns.append({
                "name": column["name"],
                "type": str(column["type"])
            })
        schema_info[table_name] = columns
        
    return schema_info

def get_schema_details(db: Session) -> list:
    """
    Returns details for the Data Explorer: tables, column metadata, row counts, and preview data.
    """
    inspector = inspect(engine)
    tables = []
    
    for table_name in inspector.get_table_names():
        columns = []
        for column in inspector.get_columns(table_name):
            columns.append({
                "name": column["name"],
                "type": str(column["type"])
            })
            
        quoted_table = quote_ident(table_name)
        # Get row count
        count_res = db.execute(text(f"SELECT COUNT(*) FROM {quoted_table}"))
        row_count = count_res.scalar()
        
        # Get preview rows
        preview_res = db.execute(text(f"SELECT * FROM {quoted_table} LIMIT 10"))
        preview_cols = list(preview_res.keys())
        preview_rows = []
        for row in preview_res.fetchall():
            row_dict = {}
            for col, val in zip(preview_cols, row):
                # Ensure value is JSON serializable
                if hasattr(val, "isoformat"):
                    row_dict[col] = val.isoformat()
                elif isinstance(val, (bytes, bytearray)):
                    row_dict[col] = str(val)
                else:
                    row_dict[col] = val
            preview_rows.append(row_dict)
        
        tables.append({
            "name": table_name,
            "row_count": row_count,
            "columns": columns,
            "preview": preview_rows
        })
        
    return tables

def execute_query(sql: str, db: Session, limit: int = 500) -> tuple[list[str], list[dict]]:
    """
    Validates and executes a SQL query against the database.
    Returns: (columns, rows_list)
    """
    # 1. Safety check
    is_safe, err_msg = is_safe_sql(sql)
    if not is_safe:
        raise ValueError(err_msg)

    # 2. Clean query and apply row limit if appropriate
    cleaned_sql = sql.strip().rstrip(";")
    
    # Append limit if select and doesn't already have a limit
    if "SELECT" in cleaned_sql.upper() and "LIMIT" not in cleaned_sql.upper():
        cleaned_sql = f"{cleaned_sql} LIMIT {limit}"

    # 3. Execute query with error handling
    try:
        result = db.execute(text(cleaned_sql))
        columns = list(result.keys())
        rows = []
        for row in result.fetchall():
            row_dict = {}
            for col, val in zip(columns, row):
                # Format dates and custom objects for JSON serialization
                if hasattr(val, "isoformat"):
                    row_dict[col] = val.isoformat()
                elif isinstance(val, (bytes, bytearray)):
                    row_dict[col] = str(val)
                else:
                    row_dict[col] = val
            rows.append(row_dict)
        return columns, rows
    except Exception as e:
        # Re-raise standard exception with message
        raise RuntimeError(f"Database execution error: {str(e)}")

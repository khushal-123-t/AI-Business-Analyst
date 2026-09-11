import re
from typing import Dict, Any, List, Optional
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from backend.database.connection import quote_ident, engine

NUMERIC_TYPE_KEYWORDS = ("INT", "FLOAT", "REAL", "DOUBLE", "DECIMAL", "NUMERIC", "BIGINT", "SMALLINT")
DATE_TYPE_KEYWORDS = ("DATE", "TIME", "TIMESTAMP")

def inspect_dataset_schema(db: Session, table_name: str) -> Dict[str, Any]:
    """
    Intelligently profiles an arbitrary database table to detect:
    - column names and types
    - numeric columns
    - categorical columns
    - date/datetime columns
    - ID / primary key columns
    - sample rows (3-5 rows)
    - total row count
    - primary metric, category, and temporal dimensions for analytics
    Never assumes fixed column names such as sales, revenue, date, product, etc.
    """
    bind = getattr(db, "bind", None) or engine
    inspector = inspect(bind)
    quoted_table = quote_ident(table_name)
    dialect_name = bind.dialect.name.lower()

    col_objs = []
    try:
        col_objs = inspector.get_columns(table_name)
    except Exception:
        # Fallback query if inspector fails
        try:
            res = db.execute(text(f"SELECT * FROM {quoted_table} LIMIT 1"))
            col_objs = [{"name": c, "type": "VARCHAR"} for c in res.keys()]
        except Exception:
            col_objs = []

    columns = [c["name"] for c in col_objs]
    col_type_map = {c["name"]: str(c.get("type", "VARCHAR")).upper() for c in col_objs}

    # Fetch total row count
    row_count = 0
    try:
        cnt_res = db.execute(text(f"SELECT COUNT(*) FROM {quoted_table}")).scalar()
        row_count = int(cnt_res) if cnt_res is not None else 0
    except Exception:
        row_count = 0

    # Fetch 5 sample rows
    sample_rows = []
    try:
        sample_res = db.execute(text(f"SELECT * FROM {quoted_table} LIMIT 5"))
        sample_keys = list(sample_res.keys())
        for row in sample_res.fetchall():
            row_dict = {}
            for k, val in zip(sample_keys, row):
                if hasattr(val, "isoformat"):
                    row_dict[k] = val.isoformat()
                elif isinstance(val, (bytes, bytearray)):
                    row_dict[k] = str(val)
                else:
                    row_dict[k] = val
            sample_rows.append(row_dict)
    except Exception:
        sample_rows = []

    # Classify columns dynamically
    numeric_columns = []
    date_columns = []
    categorical_columns = []
    id_columns = []
    nullable_columns = [c["name"] for c in col_objs if c.get("nullable", True)]

    # Date regex patterns for string-stored dates
    date_pattern = re.compile(r"^\d{4}[-/]\d{1,2}([-/]\d{1,2})?(\s+\d{1,2}:\d{2}(:\d{2})?)?$")

    for col in columns:
        col_lower = col.lower()
        ctype = col_type_map.get(col, "")

        # Check for ID columns
        is_id = (
            col_lower == "id" or 
            col_lower.endswith("_id") or 
            col_lower.startswith("id_") or 
            col_lower in ("uuid", "guid", "code", "index")
        )

        # 1. Date/Time Detection
        if any(dk in ctype for dk in DATE_TYPE_KEYWORDS):
            date_columns.append(col)
            continue
        
        # Check sample rows for date-like strings
        if sample_rows and not is_id:
            sample_vals = [str(r[col]).strip() for r in sample_rows if r.get(col) is not None]
            if sample_vals and all(date_pattern.match(v) for v in sample_vals if v):
                date_columns.append(col)
                continue

        # 2. Numeric Detection
        if any(nt in ctype for nt in NUMERIC_TYPE_KEYWORDS):
            if is_id:
                id_columns.append(col)
            else:
                numeric_columns.append(col)
            continue

        # Check sample rows for numeric values stored as strings
        if sample_rows and not is_id:
            sample_vals = [str(r[col]).strip().replace("$", "").replace(",", "").replace("%", "") for r in sample_rows if r.get(col) is not None]
            parsed_count = 0
            for sv in sample_vals:
                try:
                    float(sv)
                    parsed_count += 1
                except ValueError:
                    pass
            if sample_vals and (parsed_count / len(sample_vals)) >= 0.8:
                numeric_columns.append(col)
                continue

        # 3. Categorical / Dimension Detection
        if is_id:
            id_columns.append(col)
        else:
            categorical_columns.append(col)

    # Detect profit and margin columns specifically if present
    PROFIT_KEYWORDS = ("profit", "net_profit", "gross_profit", "profit_amount", "total_profit", "earnings")
    MARGIN_KEYWORDS = ("profit_margin", "margin_percent", "margin_percentage", "margin_pct", "net_margin", "gross_margin", "margin")

    profit_col = next((c for c in columns if any(pk == c.lower() or c.lower().endswith(f"_{pk}") for pk in PROFIT_KEYWORDS)), None)
    margin_col = next((c for c in columns if any(mk == c.lower() or c.lower().endswith(f"_{mk}") for mk in MARGIN_KEYWORDS)), None)

    # Dynamic Selection of Primary Metric (without assuming sales/revenue)
    # Prefer columns with financial / volume / metric keywords if available, else first numeric
    METRIC_PREFERENCE = (
        "revenue", "sales", "total_amount", "amount", "salary", "spend", "spending", "price",
        "value", "cost", "income", "visits", "impressions", "clicks", "conversions", "score",
        "quantity", "units", "count", "stock", "balance", "rate", "points"
    )
    primary_metric = None
    for pref in METRIC_PREFERENCE:
        match = next((c for c in numeric_columns if pref in c.lower()), None)
        if match:
            primary_metric = match
            break
    if not primary_metric and numeric_columns:
        primary_metric = numeric_columns[0]

    # Secondary metric
    secondary_metric = next((c for c in numeric_columns if c != primary_metric), None)

    # Dynamic Selection of Primary Categorical Dimension
    CATEGORY_PREFERENCE = (
        "category", "department", "genre", "segment", "group", "type", "class",
        "status", "tier", "role", "region", "city", "country", "state", "channel"
    )
    primary_category = None
    for pref in CATEGORY_PREFERENCE:
        match = next((c for c in categorical_columns if pref in c.lower()), None)
        if match:
            primary_category = match
            break
    if not primary_category and categorical_columns:
        primary_category = categorical_columns[0]

    # Secondary Category (e.g. region / city / location / second grouping)
    SECONDARY_CAT_PREFERENCE = ("region", "city", "location", "country", "state", "zone", "market", "channel", "platform")
    secondary_category = None
    for pref in SECONDARY_CAT_PREFERENCE:
        match = next((c for c in categorical_columns if pref in c.lower() and c != primary_category), None)
        if match:
            secondary_category = match
            break
    if not secondary_category:
        secondary_category = next((c for c in categorical_columns if c != primary_category), None)

    # Primary Temporal / Date column
    primary_date = date_columns[0] if date_columns else None

    # Primary ID column (for entity counting / distinct records)
    primary_id = id_columns[0] if id_columns else None

    # Primary Entity Name column (for top-N listings, e.g. customer_name, product_name, employee_name, title)
    NAME_PREFERENCE = ("name", "title", "product", "customer", "employee", "client", "item", "user", "label")
    primary_name = None
    for pref in NAME_PREFERENCE:
        match = next((c for c in categorical_columns if pref in c.lower() and c != primary_category), None)
        if match:
            primary_name = match
            break
    if not primary_name:
        primary_name = categorical_columns[0] if categorical_columns else (primary_id or "Item")

    return {
        "table_name": table_name,
        "dialect": dialect_name,
        "row_count": row_count,
        "columns": columns,
        "column_types": col_type_map,
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "date_columns": date_columns,
        "id_columns": id_columns,
        "nullable_columns": nullable_columns,
        "sample_rows": sample_rows,
        "primary_metric": primary_metric,
        "secondary_metric": secondary_metric,
        "primary_category": primary_category,
        "secondary_category": secondary_category,
        "primary_date": primary_date,
        "primary_id": primary_id,
        "primary_name": primary_name,
        "profit_col": profit_col,
        "margin_col": margin_col
    }

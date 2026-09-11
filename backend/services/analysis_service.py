import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from backend.database.connection import quote_ident

def analyze_result_set(columns: list, rows: list) -> dict:
    """
    Performs basic statistics and checks on a dynamic query result set using Pandas.
    """
    if not rows:
        return {"row_count": 0, "numeric_summaries": {}}

    df = pd.DataFrame(rows)
    summary = {
        "row_count": len(df),
        "column_count": len(columns),
        "numeric_summaries": {}
    }

    # Find numeric columns and calculate basic sums/means
    for col in columns:
        if col in df.columns:
            try:
                numeric_col = pd.to_numeric(df[col], errors='coerce')
                if not pd.api.types.is_bool_dtype(numeric_col) and not numeric_col.isna().all():
                    summary["numeric_summaries"][col] = {
                        "sum": float(numeric_col.sum()) if not pd.isna(numeric_col.sum()) else 0.0,
                        "mean": float(numeric_col.mean()) if not pd.isna(numeric_col.mean()) else 0.0,
                        "min": float(numeric_col.min()) if not pd.isna(numeric_col.min()) else 0.0,
                        "max": float(numeric_col.max()) if not pd.isna(numeric_col.max()) else 0.0
                    }
            except (ValueError, TypeError):
                continue

    return summary

def clean_category_name(val) -> str:
    """Cleans complex category strings (e.g. JSON strings or category trees) into clean labels."""
    if val is None:
        return "General"
    s = str(val).strip()
    if s.startswith('["') or s.startswith("['"):
        s = s.strip('[]"\'')
    if ">>" in s:
        s = s.split(">>")[0].strip()
    if "," in s and len(s) > 30:
        s = s.split(",")[0].strip()
    s = s.strip('[]"\'').strip()
    return s if s else "General"

from backend.services.schema_service import inspect_dataset_schema

def clean_numeric_sql(col_expr: str, dialect: str = "sqlite") -> str:
    """
    Wraps a column expression so that currency symbols ($, ₹, €, £, ¥),
    commas, percent signs, and whitespace are safely stripped before numeric casting.
    Works seamlessly across PostgreSQL and SQLite.
    """
    if dialect == "postgresql":
        return f"CAST(NULLIF(REGEXP_REPLACE(CAST({col_expr} AS TEXT), '[$,₹€£¥%\\s]', '', 'g'), '') AS NUMERIC)"
    return f"CAST(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(CAST({col_expr} AS TEXT), '$', ''), '₹', ''), '€', ''), '£', ''), '¥', ''), ',', ''), '%', ''), ' ', '') AS REAL)"

def resolve_columns(db: Session, table_name: str, user_margin: float = None) -> dict:
    """
    Inspects table columns using dynamic schema profiling and maps them to dashboard
    analytics dimensions without assuming any fixed column names or sales-specific structures.
    """
    bind = getattr(db, "bind", db) or db
    dialect_name = getattr(bind, "dialect", None)
    dialect = dialect_name.name.lower() if dialect_name else "sqlite"
    
    schema = inspect_dataset_schema(db, table_name)
    columns = schema["columns"]
    cols_lower = [c.lower() for c in columns]
    col_type_map = schema["column_types"]

    NUMERIC_TYPES = ("FLOAT", "REAL", "INT", "DOUBLE", "DECIMAL", "NUMERIC", "BIGINT", "SMALLINT")
    def safe_col_expr(col_name: str) -> str:
        ctype = col_type_map.get(col_name, "").upper()
        quoted = quote_ident(col_name)
        if any(t in ctype for t in NUMERIC_TYPES):
            return quoted
        return clean_numeric_sql(quoted, dialect=dialect)

    import re

    def find_best_match(keys, default=None):
        for k in keys:
            if k.lower() in cols_lower:
                idx = cols_lower.index(k.lower())
                return columns[idx]
        for col in columns:
            col_norm = re.sub(r'[^a-zA-Z0-9]', '_', col.lower()).strip('_')
            for k in keys:
                if col_norm == k.lower():
                    return col
        return default

    # 1. Resolve Revenue / Primary Metric Column
    rev_col = find_best_match([
        "total_revenue", "totalrevenue", "revenue", "sales", "ordervalue", "net_revenue",
        "gross_revenue", "total_sales", "sales_amount", "total_amount", "final_amount",
        "total_price", "selling_price", "final_price", "net_amount", "amount",
        "salary", "spending_score", "spend", "visits", "website_visits", "price"
    ])
    
    qty_col = find_best_match([
        "quantity_sold", "quantity", "qty", "units_sold", "units", "items_count", "item_count"
    ], default=None)
    
    unit_price_col = find_best_match([
        "discounted_price", "retail_price", "unit_price", "unitprice", "price", "mrp", "value"
    ], default=None)
    
    # Explicit recognized profit and margin keywords
    PROFIT_KEYS = [
        "profit", "net_profit", "gross_profit", "profit_amount", 
        "total_profit", "earnings", "net_earnings", "operating_profit"
    ]
    
    MARGIN_KEYS = [
        "profit_margin", "profit_margin_percent", "profit_margin_percentage",
        "margin_percent", "margin_percentage", "margin_pct", "net_margin",
        "gross_margin", "operating_margin", "margin"
    ]

    profit_col = schema.get("profit_col") or find_best_match(PROFIT_KEYS)
    margin_col = schema.get("margin_col") or find_best_match(MARGIN_KEYS)

    # Summary aggregated metrics (e.g. from dataset statistics / summary tables)
    summary_orders_col = find_best_match([
        "total_transactions", "total_orders", "transactions_count", "orders_count",
        "total_transaction", "total_order", "transactions", "orders"
    ], default=None)

    summary_cust_col = find_best_match([
        "total_customers", "total_users", "total_clients", "total_buyers",
        "unique_customers", "customers_count", "customers", "users_count"
    ], default=None)

    aov_col = find_best_match([
        "average_order_value", "avg_order_value", "avg_order", "aov"
    ], default=None)

    order_col = find_best_match([
        "order_id", "order_no", "order_number", "id", "uniq_id", "pid",
        "show_id", "product_id", "item_id", "invoice_id", "invoice",
        "transaction_id", "transaction", "employee_id", "code"
    ], default=None)

    cust_id_col = find_best_match([
        "customer_id", "cust_id", "user_id", "client_id", "buyer_id",
        "account_id", "member_id", "employee_id", "uniq_id"
    ], default=None)

    cust_name_col = find_best_match([
        "customer_name", "customer", "client_name", "client", "buyer",
        "user_name", "employee_name", "brand", "product_name", "product", "title", "name"
    ], default=None)

    cat_col = find_best_match([
        "category", "department", "product_category_tree", "product_category", "sub_category",
        "listed_in", "genre", "type", "group", "class", "segment"
    ], default=None)

    reg_col = find_best_match([
        "region", "customer_region", "location", "country", "state", "city", "zone",
        "area", "territory", "market"
    ], default=None)

    date_col = find_best_match([
        "order_date", "date", "joining_date", "crawl_timestamp", "date_added", "timestamp",
        "created_at", "time", "date_time", "datetime", "date_range", "year"
    ], default=None)

    # Fallback to schema profiling dimensions if keyword matching didn't yield matches
    if not rev_col and schema.get("primary_metric"):
        rev_col = schema["primary_metric"]
    if not cat_col and schema.get("primary_category"):
        cat_col = schema["primary_category"]
    if not reg_col and schema.get("secondary_category"):
        reg_col = schema["secondary_category"]
    if not date_col and schema.get("primary_date"):
        date_col = schema["primary_date"]
    if not order_col and schema.get("primary_id"):
        order_col = schema["primary_id"]
    if not cust_name_col and schema.get("primary_name"):
        cust_name_col = schema["primary_name"]

    final_mapping = {
        "dialect": dialect,
        "has_real_revenue": bool(rev_col and rev_col in columns),
        "has_real_category": bool(cat_col and cat_col in columns),
        "has_real_region": bool(reg_col and reg_col in columns and reg_col != cat_col),
        "has_real_date": bool(date_col and date_col in columns),
        "has_real_id": bool((order_col and order_col in columns) or (summary_orders_col and summary_orders_col in columns)),
        "raw_rev_col": rev_col,
        "raw_cat_col": cat_col,
        "raw_reg_col": reg_col,
        "raw_date_col": date_col,
        "raw_id_col": order_col,
        "raw_name_col": cust_name_col,
        "aov_col": aov_col if aov_col and aov_col in columns else None
    }

    # 1. Primary Metric / Revenue
    if rev_col and rev_col in columns:
        final_mapping["revenue"] = safe_col_expr(rev_col)
        final_mapping["metric_name"] = rev_col.replace("_", " ").title()
    elif qty_col and unit_price_col and qty_col in columns and unit_price_col in columns:
        final_mapping["revenue"] = f"({safe_col_expr(qty_col)} * {safe_col_expr(unit_price_col)})"
        final_mapping["metric_name"] = "Calculated Revenue"
    elif unit_price_col and unit_price_col in columns:
        final_mapping["revenue"] = safe_col_expr(unit_price_col)
        final_mapping["metric_name"] = unit_price_col.replace("_", " ").title()
    else:
        final_mapping["revenue"] = "1"
        final_mapping["metric_name"] = "Records Count"

    # 2. Profit - STRICTLY DATA-DRIVEN LOGIC:
    if profit_col and profit_col in columns:
        final_mapping["profit"] = safe_col_expr(profit_col)
        final_mapping["profit_source"] = "column"
        final_mapping["profit_col"] = profit_col
        final_mapping["profit_available"] = True
        final_mapping["profit_note"] = None
    elif margin_col and margin_col in columns and final_mapping.get("has_real_revenue"):
        margin_clean = safe_col_expr(margin_col)
        margin_mult = f"(CASE WHEN {margin_clean} > 1.0 THEN ({margin_clean} / 100.0) ELSE {margin_clean} END)"
        final_mapping["profit"] = f"({final_mapping['revenue']} * {margin_mult})"
        final_mapping["profit_source"] = "margin_column"
        final_mapping["margin_col"] = margin_col
        final_mapping["profit_available"] = True
        final_mapping["profit_note"] = f"Calculated using dataset margin column '{margin_col}'"
    elif user_margin is not None and final_mapping.get("has_real_revenue"):
        margin_mult = user_margin / 100.0 if user_margin > 1.0 else user_margin
        final_mapping["profit"] = f"({final_mapping['revenue']} * {margin_mult})"
        final_mapping["profit_source"] = "user_margin"
        final_mapping["user_margin"] = user_margin
        final_mapping["profit_available"] = True
        final_mapping["profit_note"] = f"Estimated using user-provided {user_margin}% profit margin"
    else:
        final_mapping["profit"] = None
        final_mapping["profit_source"] = None
        final_mapping["profit_available"] = False
        final_mapping["profit_note"] = "Profit data unavailable"

    # 3. Order ID & Aggregates
    if summary_orders_col and summary_orders_col in columns:
        final_mapping["orders_aggregate"] = f"SUM({safe_col_expr(summary_orders_col)})"
        final_mapping["order_id"] = "1"
        final_mapping["count_name"] = summary_orders_col.replace("_", " ").title()
    elif order_col and order_col in columns:
        final_mapping["order_id"] = quote_ident(order_col)
        final_mapping["orders_aggregate"] = f"COUNT(DISTINCT {quote_ident(order_col)})"
        final_mapping["count_name"] = order_col.replace("_", " ").title()
    else:
        final_mapping["order_id"] = "1"
        final_mapping["orders_aggregate"] = "COUNT(*)"
        final_mapping["count_name"] = "Total Records"

    # 4. Customer ID & Aggregates
    if summary_cust_col and summary_cust_col in columns:
        final_mapping["customers_aggregate"] = f"SUM({safe_col_expr(summary_cust_col)})"
        final_mapping["customer_id"] = "1"
    elif cust_id_col and cust_id_col in columns:
        final_mapping["customer_id"] = quote_ident(cust_id_col)
        final_mapping["customers_aggregate"] = f"COUNT(DISTINCT {quote_ident(cust_id_col)})"
    else:
        final_mapping["customer_id"] = final_mapping["order_id"]
        final_mapping["customers_aggregate"] = final_mapping["orders_aggregate"]

    # 5. Customer Name / Item Name
    if cust_name_col and cust_name_col in columns:
        final_mapping["customer_name"] = quote_ident(cust_name_col)
        final_mapping["item_label"] = cust_name_col.replace("_", " ").title()
    elif order_col and order_col in columns:
        final_mapping["customer_name"] = quote_ident(order_col)
        final_mapping["item_label"] = order_col.replace("_", " ").title()
    else:
        final_mapping["customer_name"] = "'Item'"
        final_mapping["item_label"] = "Item"

    # 6. Category
    if cat_col and cat_col in columns:
        final_mapping["category"] = quote_ident(cat_col)
        final_mapping["category_name"] = cat_col.replace("_", " ").title()
    else:
        final_mapping["category"] = "'General'"
        final_mapping["category_name"] = "Category"

    # 7. Region
    if reg_col and reg_col in columns:
        final_mapping["region"] = quote_ident(reg_col)
        final_mapping["region_name"] = reg_col.replace("_", " ").title()
    else:
        final_mapping["region"] = "'Global'"
        final_mapping["region_name"] = "Region"

    # 8. Date
    if date_col and date_col in columns:
        final_mapping["order_date"] = quote_ident(date_col)
    else:
        final_mapping["order_date"] = None

    return final_mapping

# In-memory dashboard cache for accelerated instant retrieval
_dashboard_cache: dict = {}

def invalidate_dashboard_cache(table_name: str = None):
    """
    Invalidates cached dashboard metrics for a specific table or all tables.
    Called when new datasets are uploaded, imported, or deleted.
    """
    global _dashboard_cache
    if table_name:
        keys_to_del = [k for k in _dashboard_cache if k == table_name or k.startswith(f"{table_name}_")]
        for k in keys_to_del:
            _dashboard_cache.pop(k, None)
    else:
        _dashboard_cache.clear()

def get_dashboard_data(db: Session, table_name: str = "sales", user_margin: float = None) -> dict:
    """
    Retrieves all dashboard KPIs and chart data using dynamic schema profiling.
    Fully dialect-safe for PostgreSQL and SQLite.
    Each widget is isolated in a try-except block so a single query failure never fails the dashboard.
    """
    global _dashboard_cache
    cache_key = f"{table_name}_m{user_margin}" if user_margin is not None else table_name
    if cache_key in _dashboard_cache:
        return _dashboard_cache[cache_key]

    quoted_table = quote_ident(table_name)
    cols = resolve_columns(db, table_name, user_margin=user_margin)
    skipped_visualizations: list = []

    # Dynamic Metric Titles
    primary_metric_title = f"Total {cols.get('metric_name', 'Metric')}"
    count_title = cols.get('count_name', 'Total Records')
    avg_title = f"Average {cols.get('metric_name', 'Metric')}"
    category_title = f"{cols.get('category_name', 'Category')} Breakdown"
    region_title = f"{cols.get('region_name', 'Regional')} Distribution"

    metric_labels = {
        "primary_metric_title": primary_metric_title,
        "count_title": count_title,
        "average_title": avg_title,
        "category_title": category_title,
        "region_title": region_title
    }

    # 1. Fetch KPI metrics (Isolated Query)
    orders_expr = cols.get("orders_aggregate") or "COUNT(*)"
    customers_expr = cols.get("customers_aggregate") or "COUNT(*)"
    revenue_calc_expr = cols['revenue'] if cols["has_real_revenue"] else "COUNT(*)"

    total_revenue = 0.0
    total_profit = None
    total_orders = 0
    total_customers = 0

    try:
        if cols["profit_available"] and cols["profit"] is not None:
            kpi_query = f"""
            SELECT
                COALESCE(SUM({revenue_calc_expr}), 0) AS total_revenue,
                COALESCE(SUM({cols['profit']}), 0) AS total_profit,
                COALESCE({orders_expr}, 0) AS total_orders,
                COALESCE({customers_expr}, 0) AS total_customers
            FROM {quoted_table}
            """
            kpi_res = db.execute(text(kpi_query)).fetchone()
            total_revenue = float(kpi_res[0]) if kpi_res and kpi_res[0] is not None else 0.0
            total_profit = float(kpi_res[1]) if kpi_res and kpi_res[1] is not None else 0.0
            total_orders = int(kpi_res[2]) if kpi_res and kpi_res[2] is not None else 0
            total_customers = int(kpi_res[3]) if kpi_res and kpi_res[3] is not None else 0
        else:
            kpi_query = f"""
            SELECT
                COALESCE(SUM({revenue_calc_expr}), 0) AS total_revenue,
                COALESCE({orders_expr}, 0) AS total_orders,
                COALESCE({customers_expr}, 0) AS total_customers
            FROM {quoted_table}
            """
            kpi_res = db.execute(text(kpi_query)).fetchone()
            total_revenue = float(kpi_res[0]) if kpi_res and kpi_res[0] is not None else 0.0
            total_profit = None
            total_orders = int(kpi_res[1]) if kpi_res and kpi_res[1] is not None else 0
            total_customers = int(kpi_res[2]) if kpi_res and kpi_res[2] is not None else 0
    except Exception as e:
        # Fallback KPI calculation
        try:
            cnt_res = db.execute(text(f"SELECT COUNT(*) FROM {quoted_table}")).scalar()
            total_orders = int(cnt_res) if cnt_res is not None else 0
            total_customers = total_orders
        except Exception:
            pass

    if cols.get("aov_col"):
        try:
            aov_col_name = cols["aov_col"]
            aov_q = f"SELECT COALESCE(AVG({clean_numeric_sql(quote_ident(aov_col_name), dialect=cols['dialect'])}), 0) FROM {quoted_table}"
            aov_row = db.execute(text(aov_q)).fetchone()
            average_order_value = float(aov_row[0]) if aov_row and aov_row[0] is not None else 0.0
        except Exception:
            average_order_value = (total_revenue / total_orders) if total_orders > 0 else 0.0
    elif total_orders > 0:
        average_order_value = total_revenue / total_orders
    else:
        average_order_value = 0.0

    # 2. Monthly Revenue Trend & Orders (Isolated)
    revenue_trend = []
    monthly_orders = []

    if not cols.get("has_real_date") or not cols.get("order_date"):
        skipped_visualizations.append("Time-series trend chart skipped: dataset does not contain a date or timestamp column.")
    else:
        try:
            date_col_quoted = cols['order_date']
            trend_query = f"""
            SELECT
                SUBSTR(CAST({date_col_quoted} AS TEXT), 1, 7) AS month,
                COALESCE(SUM({revenue_calc_expr}), 0) AS revenue,
                COALESCE({orders_expr}, 0) AS orders
            FROM {quoted_table}
            WHERE {date_col_quoted} IS NOT NULL AND TRIM(CAST({date_col_quoted} AS TEXT)) != ''
            GROUP BY month
            ORDER BY month ASC
            """
            trend_rows = db.execute(text(trend_query)).fetchall()
            valid_sql_trend = (
                len(trend_rows) > 0 and 
                all(row[0] and len(str(row[0])) == 7 and str(row[0])[:4].isdigit() for row in trend_rows)
            )
            if valid_sql_trend:
                for r in trend_rows:
                    revenue_trend.append({"month": str(r[0]), "revenue": round(float(r[1]), 2)})
                    monthly_orders.append({"month": str(r[0]), "orders": int(r[2])})
            else:
                # Pandas fallback for diverse date formats
                raw_trend_query = f"SELECT {date_col_quoted} AS raw_date, {revenue_calc_expr} AS revenue, {cols['order_id']} AS order_id FROM {quoted_table}"
                df_trend = pd.read_sql(raw_trend_query, db.bind)
                if not df_trend.empty:
                    df_trend["revenue"] = pd.to_numeric(df_trend["revenue"], errors="coerce").fillna(0)
                    parsed_dates = pd.to_datetime(df_trend["raw_date"], errors="coerce")
                    df_trend["month"] = parsed_dates.dt.strftime("%Y-%m").fillna("Other")
                    
                    trend_grp = df_trend.groupby("month")
                    rev_series = trend_grp["revenue"].sum().reset_index().sort_values("month")
                    ord_series = trend_grp["order_id"].nunique().reset_index().rename(columns={"order_id": "orders"}).sort_values("month")
                    
                    revenue_trend = [{"month": str(r["month"]), "revenue": round(float(r["revenue"]), 2)} for _, r in rev_series.iterrows() if str(r["month"]) != "Other"]
                    monthly_orders = [{"month": str(r["month"]), "orders": int(r["orders"])} for _, r in ord_series.iterrows() if str(r["month"]) != "Other"]
        except Exception as trend_err:
            revenue_trend = []
            monthly_orders = []
            skipped_visualizations.append(f"Time-series trend chart skipped due to date formatting: {str(trend_err).splitlines()[0]}")

    # 3. Revenue & Profit by Category (Isolated)
    revenue_by_category = []
    profit_by_category = []

    if not cols.get("has_real_category"):
        skipped_visualizations.append("Category distribution chart skipped: dataset does not contain a categorical dimension column.")
    else:
        try:
            cat_col_quoted = cols['category']
            cat_query = f"""
            SELECT
                COALESCE(NULLIF(TRIM(CAST({cat_col_quoted} AS TEXT)), ''), 'General') AS raw_category,
                COALESCE(SUM({revenue_calc_expr}), 0) AS revenue
            FROM {quoted_table}
            WHERE {cat_col_quoted} IS NOT NULL
            GROUP BY raw_category
            ORDER BY revenue DESC
            LIMIT 20
            """
            cat_rows = db.execute(text(cat_query)).fetchall()
            cat_rev_map = {}
            for r in cat_rows:
                clean_name = clean_category_name(r[0])
                rev = float(r[1]) if r[1] is not None else 0.0
                cat_rev_map[clean_name] = cat_rev_map.get(clean_name, 0.0) + rev
            sorted_rev = sorted(cat_rev_map.items(), key=lambda x: x[1], reverse=True)[:8]
            revenue_by_category = [{"category": k, "revenue": round(v, 2)} for k, v in sorted_rev]

            # Profit by Category: ONLY calculate if profit data legitimately exists
            if cols["profit_available"] and cols["profit"] is not None:
                cat_prof_query = f"""
                SELECT
                    COALESCE(NULLIF(TRIM(CAST({cat_col_quoted} AS TEXT)), ''), 'General') AS raw_category,
                    COALESCE(SUM({cols['profit']}), 0) AS profit
                FROM {quoted_table}
                WHERE {cat_col_quoted} IS NOT NULL
                GROUP BY raw_category
                ORDER BY profit DESC
                LIMIT 20
                """
                cat_prof_rows = db.execute(text(cat_prof_query)).fetchall()
                cat_prof_map = {}
                for r in cat_prof_rows:
                    clean_name = clean_category_name(r[0])
                    prof = float(r[1]) if r[1] is not None else 0.0
                    cat_prof_map[clean_name] = cat_prof_map.get(clean_name, 0.0) + prof
                sorted_prof = sorted(cat_prof_map.items(), key=lambda x: x[1], reverse=True)[:8]
                profit_by_category = [{"category": k, "profit": round(v, 2)} for k, v in sorted_prof]
        except Exception as cat_err:
            revenue_by_category = []
            profit_by_category = []
            skipped_visualizations.append(f"Category breakdown skipped: {str(cat_err).splitlines()[0]}")

    # 4. Revenue by Region / Secondary Category (Isolated)
    revenue_by_region = []
    if not cols.get("has_real_region"):
        skipped_visualizations.append("Regional distribution chart skipped: dataset does not contain a secondary regional or location dimension.")
    else:
        try:
            reg_col_quoted = cols['region']
            reg_query = f"""
            SELECT
                COALESCE(NULLIF(TRIM(CAST({reg_col_quoted} AS TEXT)), ''), 'Other') AS region,
                COALESCE(SUM({revenue_calc_expr}), 0) AS revenue
            FROM {quoted_table}
            WHERE {reg_col_quoted} IS NOT NULL
            GROUP BY region
            ORDER BY revenue DESC
            LIMIT 8
            """
            reg_rows = db.execute(text(reg_query)).fetchall()
            revenue_by_region = [{"region": str(r[0]), "revenue": round(float(r[1]), 2)} for r in reg_rows]
        except Exception as reg_err:
            revenue_by_region = []
            skipped_visualizations.append(f"Regional distribution skipped: {str(reg_err).splitlines()[0]}")

    # 5. Top 10 Entities / Customers (Isolated)
    top_customers = []
    try:
        name_col_quoted = cols['customer_name']
        if cols["profit_available"] and cols["profit"] is not None:
            cust_query = f"""
            SELECT
                COALESCE(NULLIF(TRIM(CAST({name_col_quoted} AS TEXT)), ''), 'Item') AS customer_name,
                COALESCE(SUM({revenue_calc_expr}), 0) AS revenue,
                COALESCE(SUM({cols['profit']}), 0) AS profit
            FROM {quoted_table}
            GROUP BY customer_name
            ORDER BY revenue DESC
            LIMIT 10
            """
            cust_rows = db.execute(text(cust_query)).fetchall()
            top_customers = [
                {
                    "customer_name": str(r[0]),
                    "revenue": round(float(r[1]), 2),
                    "profit": round(float(r[2]), 2)
                }
                for r in cust_rows
            ]
        else:
            cust_query = f"""
            SELECT
                COALESCE(NULLIF(TRIM(CAST({name_col_quoted} AS TEXT)), ''), 'Item') AS customer_name,
                COALESCE(SUM({revenue_calc_expr}), 0) AS revenue
            FROM {quoted_table}
            GROUP BY customer_name
            ORDER BY revenue DESC
            LIMIT 10
            """
            cust_rows = db.execute(text(cust_query)).fetchall()
            top_customers = [
                {
                    "customer_name": str(r[0]),
                    "revenue": round(float(r[1]), 2),
                    "profit": None
                }
                for r in cust_rows
            ]
    except Exception:
        top_customers = []

    dashboard_result = {
        "metrics": {
            "total_revenue": round(total_revenue, 2),
            "total_profit": round(total_profit, 2) if total_profit is not None else None,
            "total_orders": total_orders,
            "total_customers": total_customers,
            "average_order_value": round(average_order_value, 2),
            "profit_available": cols["profit_available"],
            "profit_source": cols.get("profit_source"),
            "profit_note": cols.get("profit_note"),
            "metric_labels": metric_labels
        },
        "revenue_trend": revenue_trend,
        "revenue_by_category": revenue_by_category,
        "revenue_by_region": revenue_by_region,
        "profit_by_category": profit_by_category,
        "top_customers": top_customers,
        "monthly_orders": monthly_orders,
        "profit_available": cols["profit_available"],
        "skipped_visualizations": skipped_visualizations,
        "metric_labels": metric_labels
    }

    _dashboard_cache[cache_key] = dashboard_result
    return dashboard_result


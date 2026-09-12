import re
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from backend.database.connection import quote_ident
from backend.services.schema_service import inspect_dataset_schema, is_identifier_column, FinancialRole, resolve_revenue_metric

def format_identifier_count_title(col_name: str) -> str:
    """
    Dynamically formats identifier column names into natural pluralized dashboard count labels.
    e.g.:
      payment_id / Payment ID / paymentid -> "Total Payments"
      order_id / Order ID / orderid -> "Total Orders"
      transaction_id / trans_id -> "Total Transactions"
      invoice_id / invoice_no -> "Total Invoices"
      customer_id / cust_id -> "Total Customers"
      client_id -> "Total Clients"
      user_id -> "Total Users"
      employee_id -> "Total Employees"
    Never produces "Total Payment ID" or "Payment Id".
    """
    if not col_name:
        return "Total Records"

    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', str(col_name).strip()).lower()
    norm = re.sub(r'[^a-z0-9]+', '_', s).strip('_')
    tokens = norm.split('_')

    PLURAL_MAP = {
        "payment": "Payments",
        "order": "Orders",
        "transaction": "Transactions",
        "trans": "Transactions",
        "invoice": "Invoices",
        "customer": "Customers",
        "cust": "Customers",
        "client": "Clients",
        "user": "Users",
        "employee": "Employees",
        "emp": "Employees",
        "member": "Members",
        "account": "Accounts",
        "product": "Products",
        "item": "Items",
        "visitor": "Visitors",
        "visit": "Visits",
        "ticket": "Tickets",
        "receipt": "Receipts",
        "lead": "Leads",
        "deal": "Deals",
        "contract": "Contracts",
        "session": "Sessions",
        "record": "Records",
        "shipment": "Shipments",
        "delivery": "Deliveries",
        "subscription": "Subscriptions",
        "sale": "Sales"
    }

    entity = None
    if len(tokens) >= 2 and tokens[-1] in ("id", "ids", "no", "number", "num", "code", "key"):
        entity = tokens[0]
    elif norm.endswith("id") and len(norm) > 2:
        base = norm[:-2].rstrip('_')
        if base:
            entity = base
    elif tokens[0] in ("id", "code") and len(tokens) >= 2:
        entity = tokens[1]

    if entity and entity in PLURAL_MAP:
        return f"Total {PLURAL_MAP[entity]}"

    if entity:
        if entity.endswith("y") and not entity.endswith(("ay", "ey", "oy", "uy")):
            plural = entity[:-1] + "ies"
        elif entity.endswith(("s", "x", "z", "ch", "sh")):
            plural = entity + "es"
        else:
            plural = entity + "s"
        return f"Total {plural.title()}"

    clean_label = col_name.replace("_", " ").title()
    if clean_label.lower().endswith(" id"):
        base_word = clean_label[:-3].strip()
        if base_word.lower() in PLURAL_MAP:
            return f"Total {PLURAL_MAP[base_word.lower()]}"
        return f"Total {base_word}s"

    return f"Total {clean_label}"

def analyze_result_set(columns: list, rows: list) -> dict:
    """
    Performs basic statistics and checks on a dynamic query result set using Pandas.
    Rule 3: Excludes identifier columns (e.g. payment_id, order_id) from SUM and MEAN calculations.
    """
    if not rows:
        return {"row_count": 0, "numeric_summaries": {}}

    df = pd.DataFrame(rows)
    summary = {
        "row_count": len(df),
        "column_count": len(columns),
        "numeric_summaries": {}
    }

    # Find numeric columns and calculate basic sums/means (excluding identifiers)
    for col in columns:
        if col in df.columns:
            # Rule 3: Identifier columns must NEVER be summed or averaged
            if is_identifier_column(col):
                continue
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

    # Resolve columns using financial roles and schema profiling
    authoritative_rev = schema.get("authoritative_revenue_col")
    gross_sales_col = schema.get("gross_sales_col")
    price_col = schema.get("price_col")
    selling_price_col = schema.get("selling_price_col")
    unit_price_col = schema.get("unit_price_col")
    qty_col = schema.get("quantity_col")
    discount_col = schema.get("discount_col")
    discount_type = schema.get("discount_type")
    tax_col = schema.get("tax_col")
    tax_type = schema.get("tax_type")
    shipping_col = schema.get("shipping_col")
    refund_col = schema.get("refund_col")
    cost_col = schema.get("cost_col")
    payment_amount_col = schema.get("payment_amount_col")

    # Keyword fallbacks if profiler didn't identify candidates
    if not authoritative_rev:
        authoritative_rev = find_best_match([
            "net_revenue", "net_sales", "total_revenue", "totalrevenue", "sales_amount",
            "total_amount", "final_amount", "order_total", "invoice_total", "grand_total",
            "revenue", "sales", "ordervalue", "net_amount", "amount", "line_total", "extended_price"
        ])
        if authoritative_rev and is_identifier_column(authoritative_rev):
            authoritative_rev = None

    if not gross_sales_col:
        gross_sales_col = find_best_match([
            "gross_sales", "sales_value", "gross_revenue", "total_sales", "subtotal", "gross_amount"
        ])
        if gross_sales_col and is_identifier_column(gross_sales_col):
            gross_sales_col = None

    if not price_col:
        price_col = find_best_match([
            "selling_price", "sale_price", "discounted_price", "retail_price",
            "unit_price", "price", "unitprice", "mrp", "cost_per_unit", "item_price", "product_price"
        ])
        if price_col and is_identifier_column(price_col):
            price_col = None

    if not qty_col:
        qty_col = find_best_match([
            "quantity_sold", "quantity", "qty", "units_sold", "units", "items_count", "item_count", "pieces", "volume"
        ])
        if qty_col and is_identifier_column(qty_col):
            qty_col = None

    if not discount_col:
        discount_col = find_best_match([
            "discount_amount", "discount_value", "discount_percent", "discount_percentage", "discount_rate", "promo_discount", "coupon_discount", "discount"
        ])
        if discount_col:
            discount_type = "PERCENT" if any(p in discount_col.lower() for p in ("percent", "percentage", "rate", "pct")) else "AMOUNT"

    if not tax_col:
        tax_col = find_best_match([
            "tax_amount", "tax_value", "tax_rate", "tax_percent", "gst_amount", "gst_rate", "vat_amount", "vat_rate", "tax", "gst", "vat"
        ])
        if tax_col:
            tax_type = "PERCENT" if any(p in tax_col.lower() for p in ("rate", "percent", "percentage", "pct")) else "AMOUNT"

    if not shipping_col:
        shipping_col = find_best_match([
            "shipping_fee", "shipping_cost", "delivery_fee", "delivery_charge", "shipping"
        ])

    if not refund_col:
        refund_col = find_best_match([
            "refund_amount", "refund_value", "return_amount", "chargeback", "refund", "returns"
        ])

    if not cost_col:
        cost_col = find_best_match([
            "cost_of_goods_sold", "cogs", "total_cost", "cost_price", "purchase_price", "unit_cost", "cost", "expenses", "expense"
        ])

    # Summary aggregated metrics (e.g. from dataset statistics / summary tables)
    summary_orders_col = find_best_match([
        "total_payments", "payments_count", "total_transactions", "total_orders",
        "transactions_count", "orders_count", "total_transaction", "total_order",
        "transactions", "orders", "payments"
    ], default=None)

    summary_cust_col = find_best_match([
        "total_customers", "total_users", "total_clients", "total_buyers",
        "unique_customers", "customers_count", "customers", "users_count"
    ], default=None)

    aov_col = find_best_match([
        "average_order_value", "avg_order_value", "avg_order", "aov"
    ], default=None)

    payment_col = find_best_match([
        "payment_id", "payment id", "paymentid", "payment_no", "payment_number"
    ], default=None)

    order_col = find_best_match([
        "payment_id", "payment id", "paymentid", "payment_no", "payment_number",
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

    # -------------------------------------------------------------
    # STRICT REVENUE RESOLUTION (Single Authoritative Function)
    # -------------------------------------------------------------
    roles = schema.get("financial_roles", {})
    if authoritative_rev and roles.get(authoritative_rev) not in (FinancialRole.NET_REVENUE, FinancialRole.PAYMENT_AMOUNT):
        roles[authoritative_rev] = FinancialRole.NET_REVENUE
    if gross_sales_col and roles.get(gross_sales_col) != FinancialRole.GROSS_REVENUE:
        roles[gross_sales_col] = FinancialRole.GROSS_REVENUE

    rev_res = resolve_revenue_metric(
        columns=columns,
        financial_roles=roles,
        dialect=dialect,
        schema=schema
    )

    has_real_revenue = rev_res["has_real_revenue"]
    revenue_expr = rev_res["revenue_expr"]
    gross_sales_expr = rev_res["gross_sales_expr"]
    revenue_source = rev_res["source"]
    metric_name = rev_res["label"] if has_real_revenue else "Revenue"

    # Identify if price_only or quantity_only for separate downstream metrics
    if not has_real_revenue:
        if price_col and not qty_col:
            revenue_source = "price_only"
        elif qty_col and not price_col:
            revenue_source = "quantity_only"

    # -------------------------------------------------------------
    # SEPARATE FINANCIAL METRIC AGGREGATES
    # -------------------------------------------------------------
    # Discounts (Never add to revenue; keep separate)
    discounts_aggregate = None
    if discount_col and discount_col in columns:
        if discount_type == "PERCENT":
            base = gross_sales_expr if gross_sales_expr else revenue_expr
            discounts_aggregate = f"SUM({base} * ({safe_col_expr(discount_col)} / 100.0))"
        else:
            discounts_aggregate = f"SUM({safe_col_expr(discount_col)})"

    # Tax (Never add to revenue; keep separate)
    tax_aggregate = None
    if tax_col and tax_col in columns:
        if tax_type == "PERCENT":
            base = gross_sales_expr if gross_sales_expr else revenue_expr
            tax_aggregate = f"SUM({base} * ({safe_col_expr(tax_col)} / 100.0))"
        else:
            tax_aggregate = f"SUM({safe_col_expr(tax_col)})"

    # Shipping / Delivery Fees (Never add to revenue; keep separate)
    shipping_aggregate = None
    if shipping_col and shipping_col in columns:
        shipping_aggregate = f"SUM({safe_col_expr(shipping_col)})"

    # Quantity Aggregate
    quantity_aggregate = None
    if qty_col and qty_col in columns:
        quantity_aggregate = f"SUM({safe_col_expr(qty_col)})"

    # Average Price Aggregate
    avg_price_aggregate = None
    if price_col and price_col in columns:
        avg_price_aggregate = f"AVG({safe_col_expr(price_col)})"

    # Cost / COGS
    cost_aggregate = None
    if cost_col and cost_col in columns:
        cost_role = roles.get(cost_col)
        if (cost_role == FinancialRole.COST_PRICE or "unit" in cost_col.lower()) and qty_col and qty_col in columns:
            cost_calc_expr = f"({safe_col_expr(cost_col)} * {safe_col_expr(qty_col)})"
        else:
            cost_calc_expr = safe_col_expr(cost_col)
        cost_aggregate = f"SUM({cost_calc_expr})"

    # -------------------------------------------------------------
    # PROFIT & MARGIN LOGIC
    # -------------------------------------------------------------
    profit_col = schema.get("profit_col")
    margin_col = schema.get("margin_col")
    profit_available = False
    profit_source = None
    profit_note = None
    profit_expr = None

    if profit_col and profit_col in columns:
        profit_expr = safe_col_expr(profit_col)
        profit_available = True
        profit_source = "column"
        profit_note = None
    elif cost_col and cost_col in columns and has_real_revenue:
        cost_role = roles.get(cost_col)
        if (cost_role == FinancialRole.COST_PRICE or "unit" in cost_col.lower()) and qty_col and qty_col in columns:
            cost_calc_expr = f"({safe_col_expr(cost_col)} * {safe_col_expr(qty_col)})"
        else:
            cost_calc_expr = safe_col_expr(cost_col)
        profit_expr = f"({revenue_expr} - {cost_calc_expr})"
        profit_available = True
        profit_source = "revenue_minus_cogs"
        profit_note = f"Calculated as Revenue minus COGS/Cost '{cost_col}'"
    elif margin_col and margin_col in columns and has_real_revenue:
        margin_clean = safe_col_expr(margin_col)
        margin_mult = f"(CASE WHEN {margin_clean} > 1.0 THEN ({margin_clean} / 100.0) ELSE {margin_clean} END)"
        profit_expr = f"({revenue_expr} * {margin_mult})"
        profit_available = True
        profit_source = "margin_column"
        profit_note = f"Calculated using dataset margin column '{margin_col}'"
    elif user_margin is not None and has_real_revenue:
        margin_mult = user_margin / 100.0 if user_margin > 1.0 else user_margin
        profit_expr = f"({revenue_expr} * {margin_mult})"
        profit_available = True
        profit_source = "user_margin"
        profit_note = f"Estimated using user-provided {user_margin}% profit margin"
    else:
        profit_expr = None
        profit_available = False
        profit_source = None
        profit_note = "Profit data unavailable"

    # -------------------------------------------------------------
    # ORDERS / TRANSACTIONS / PAYMENTS AGGREGATES
    # -------------------------------------------------------------
    if summary_orders_col and summary_orders_col in columns:
        orders_aggregate = f"SUM({safe_col_expr(summary_orders_col)})"
        order_id_field = "1"
        count_name = format_identifier_count_title(summary_orders_col)
    elif payment_col and payment_col in columns:
        order_id_field = quote_ident(payment_col)
        orders_aggregate = f"COUNT(DISTINCT {order_id_field})"
        count_name = "Total Payments"
    elif order_col and order_col in columns:
        order_id_field = quote_ident(order_col)
        orders_aggregate = f"COUNT(DISTINCT {order_id_field})"
        count_name = format_identifier_count_title(order_col)
    else:
        order_id_field = "1"
        orders_aggregate = "COUNT(*)"
        count_name = "Total Records"

    # Customers Aggregate
    if summary_cust_col and summary_cust_col in columns:
        customers_aggregate = f"SUM({safe_col_expr(summary_cust_col)})"
        customer_id_field = "1"
    elif cust_id_col and cust_id_col in columns:
        customer_id_field = quote_ident(cust_id_col)
        customers_aggregate = f"COUNT(DISTINCT {customer_id_field})"
    else:
        customer_id_field = order_id_field
        customers_aggregate = orders_aggregate

    # Customer / Item Name
    if cust_name_col and cust_name_col in columns:
        customer_name_field = quote_ident(cust_name_col)
        item_label = cust_name_col.replace("_", " ").title()
    elif order_col and order_col in columns:
        customer_name_field = quote_ident(order_col)
        item_label = order_col.replace("_", " ").title()
    else:
        customer_name_field = "'Item'"
        item_label = "Item"

    # Category
    if cat_col and cat_col in columns:
        category_field = quote_ident(cat_col)
        category_name = cat_col.replace("_", " ").title()
    else:
        category_field = "'General'"
        category_name = "Category"

    # Region
    if reg_col and reg_col in columns:
        region_field = quote_ident(reg_col)
        region_name = reg_col.replace("_", " ").title()
    else:
        region_field = "'Global'"
        region_name = "Region"

    # Date
    order_date_field = quote_ident(date_col) if date_col and date_col in columns else None

    final_mapping = {
        "dialect": dialect,
        "has_real_revenue": has_real_revenue,
        "revenue": revenue_expr,
        "gross_sales": gross_sales_expr,
        "revenue_source": revenue_source,
        "metric_name": metric_name,
        "has_real_category": bool(cat_col and cat_col in columns),
        "has_real_region": bool(reg_col and reg_col in columns and reg_col != cat_col),
        "has_real_date": bool(date_col and date_col in columns),
        "has_real_id": bool((order_col and order_col in columns) or (summary_orders_col and summary_orders_col in columns)),
        "raw_rev_col": authoritative_rev or gross_sales_col or payment_amount_col,
        "raw_cat_col": cat_col,
        "raw_reg_col": reg_col,
        "raw_date_col": date_col,
        "raw_id_col": order_col,
        "raw_name_col": cust_name_col,
        "aov_col": aov_col if aov_col and aov_col in columns else None,
        "profit": profit_expr,
        "profit_available": profit_available,
        "profit_source": profit_source,
        "profit_note": profit_note,
        "orders_aggregate": orders_aggregate,
        "order_id": order_id_field,
        "count_name": count_name,
        "customers_aggregate": customers_aggregate,
        "customer_id": customer_id_field,
        "customer_name": customer_name_field,
        "item_label": item_label,
        "category": category_field,
        "category_name": category_name,
        "region": region_field,
        "region_name": region_name,
        "order_date": order_date_field,
        "discounts_aggregate": discounts_aggregate,
        "tax_aggregate": tax_aggregate,
        "shipping_aggregate": shipping_aggregate,
        "quantity_aggregate": quantity_aggregate,
        "cost_aggregate": cost_aggregate,
        "avg_price_aggregate": avg_price_aggregate,
        "price_col": price_col,
        "qty_col": qty_col,
        "discount_col": discount_col,
        "tax_col": tax_col,
        "shipping_col": shipping_col,
        "cost_col": cost_col,
        "refund_col": refund_col,
        "payment_col": payment_col
    }

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
    has_rev = cols["has_real_revenue"]
    count_title = cols.get('count_name', 'Total Records')

    # The Revenue KPI title must always strictly be Revenue / Total Revenue
    # It must NEVER be replaced by 'Average Price', 'Total Quantity', 'Total Records', or arbitrary numeric fields
    primary_metric_title = f"Total {cols.get('metric_name', 'Revenue')}" if has_rev else "Total Revenue"
    avg_title = "Average Order Value"

    category_title = f"{cols.get('category_name', 'Category')} Breakdown"
    region_title = f"{cols.get('region_name', 'Regional')} Distribution"

    metric_labels = {
        "primary_metric_title": primary_metric_title,
        "revenue_title": primary_metric_title,
        "count_title": count_title,
        "average_title": avg_title,
        "category_title": category_title,
        "region_title": region_title
    }

    # 1. Fetch KPI metrics (Isolated Query)
    orders_expr = cols.get("orders_aggregate") or "COUNT(*)"
    customers_expr = cols.get("customers_aggregate") or "COUNT(*)"
    revenue_calc_expr = cols['revenue'] if has_rev else "0"
    rev_kpi_expr = f"COALESCE(SUM({cols['revenue']}), 0)" if has_rev else "0.0"

    gross_sales_kpi = f"COALESCE(SUM({cols['gross_sales']}), 0)" if (cols.get("gross_sales") and has_rev) else ("NULL" if not has_rev else rev_kpi_expr)
    discounts_kpi = f"COALESCE({cols['discounts_aggregate']}, 0)" if cols.get("discounts_aggregate") else "NULL"
    tax_kpi = f"COALESCE({cols['tax_aggregate']}, 0)" if cols.get("tax_aggregate") else "NULL"
    shipping_kpi = f"COALESCE({cols['shipping_aggregate']}, 0)" if cols.get("shipping_aggregate") else "NULL"
    quantity_kpi = f"COALESCE({cols['quantity_aggregate']}, 0)" if cols.get("quantity_aggregate") else "NULL"
    cost_kpi = f"COALESCE({cols['cost_aggregate']}, 0)" if cols.get("cost_aggregate") else "NULL"
    avg_price_kpi = f"COALESCE({cols['avg_price_aggregate']}, 0)" if cols.get("avg_price_aggregate") else "NULL"
    profit_kpi = f"COALESCE(SUM({cols['profit']}), 0)" if cols["profit_available"] and cols["profit"] is not None else "NULL"

    total_revenue = 0.0
    gross_sales = None
    total_discounts = None
    total_tax = None
    total_shipping = None
    total_quantity = None
    total_cost = None
    average_price = None
    total_profit = None
    total_orders = 0
    total_customers = 0

    try:
        kpi_query = f"""
        SELECT
            {rev_kpi_expr} AS total_revenue,
            {gross_sales_kpi} AS gross_sales,
            {discounts_kpi} AS total_discounts,
            {tax_kpi} AS total_tax,
            {shipping_kpi} AS total_shipping,
            {quantity_kpi} AS total_quantity,
            {cost_kpi} AS total_cost,
            {avg_price_kpi} AS average_price,
            {profit_kpi} AS total_profit,
            COALESCE({orders_expr}, 0) AS total_orders,
            COALESCE({customers_expr}, 0) AS total_customers
        FROM {quoted_table}
        """
        kpi_res = db.execute(text(kpi_query)).fetchone()
        if kpi_res:
            total_revenue = float(kpi_res[0]) if (kpi_res[0] is not None and has_rev) else 0.0
            gross_sales = float(kpi_res[1]) if (kpi_res[1] is not None and has_rev) else (total_revenue if has_rev else None)
            total_discounts = float(kpi_res[2]) if kpi_res[2] is not None else None
            total_tax = float(kpi_res[3]) if kpi_res[3] is not None else None
            total_shipping = float(kpi_res[4]) if kpi_res[4] is not None else None
            total_quantity = float(kpi_res[5]) if kpi_res[5] is not None else None
            total_cost = float(kpi_res[6]) if kpi_res[6] is not None else None
            average_price = float(kpi_res[7]) if kpi_res[7] is not None else None
            total_profit = float(kpi_res[8]) if kpi_res[8] is not None else None
            total_orders = int(kpi_res[9]) if kpi_res[9] is not None else 0
            total_customers = int(kpi_res[10]) if kpi_res[10] is not None else 0
    except Exception as e:
        # Fallback KPI calculation
        try:
            cnt_res = db.execute(text(f"SELECT COUNT(*) FROM {quoted_table}")).scalar()
            total_orders = int(cnt_res) if cnt_res is not None else 0
            total_customers = total_orders
        except Exception:
            pass

    if not has_rev:
        average_order_value = 0.0
    elif cols.get("aov_col"):
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

    if not has_rev:
        skipped_visualizations.append("Time-series revenue trend chart skipped: dataset does not contain valid revenue or price × quantity data.")
    elif not cols.get("has_real_date") or not cols.get("order_date"):
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

    if not has_rev:
        skipped_visualizations.append("Category revenue breakdown chart skipped: dataset does not contain valid revenue data.")
    elif not cols.get("has_real_category"):
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
    if not has_rev:
        skipped_visualizations.append("Regional revenue distribution chart skipped: dataset does not contain valid revenue data.")
    elif not cols.get("has_real_region"):
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
    if has_rev:
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

    profit_margin = round((total_profit / total_revenue) * 100, 2) if total_profit is not None and total_revenue > 0 else None

    dashboard_result = {
        "metrics": {
            "revenue": round(total_revenue, 2),
            "total_revenue": round(total_revenue, 2),
            "gross_sales": round(gross_sales, 2) if gross_sales is not None else None,
            "total_discounts": round(total_discounts, 2) if total_discounts is not None else None,
            "total_tax": round(total_tax, 2) if total_tax is not None else None,
            "total_shipping": round(total_shipping, 2) if total_shipping is not None else None,
            "total_quantity": round(total_quantity, 2) if total_quantity is not None else None,
            "total_cost": round(total_cost, 2) if total_cost is not None else None,
            "average_price": round(average_price, 2) if average_price is not None else None,
            "total_profit": round(total_profit, 2) if total_profit is not None else None,
            "profit_margin": profit_margin,
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


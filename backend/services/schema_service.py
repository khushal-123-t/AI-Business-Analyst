import re
from typing import Dict, Any, List, Optional
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from backend.database.connection import quote_ident, engine, clean_numeric_sql

NUMERIC_TYPE_KEYWORDS = ("INT", "FLOAT", "REAL", "DOUBLE", "DECIMAL", "NUMERIC", "BIGINT", "SMALLINT")
DATE_TYPE_KEYWORDS = ("DATE", "TIME", "TIMESTAMP")

NON_ID_WORDS = {
    "paid", "mid", "grid", "fluid", "acid", "solid", "valid", "rapid", "liquid", "void",
    "lipid", "hybrid", "pyramid", "lucid", "humid", "rigid", "tepid", "morbid", "candid",
    "vivid", "squalid", "frigid", "turbid", "timid", "rabid", "arid", "torrid", "putrid",
    "placid", "viscid", "splendid", "pallid", "livid", "stupid", "gelid", "fetid", "flaccid",
    "intrepid", "insipid", "maid", "raid", "braid", "squid", "kid", "lid"
}

ENTITY_STEMS = (
    "payment", "trans", "transaction", "order", "cust", "customer", "invoice", "user",
    "client", "account", "member", "emp", "employee", "vendor", "seller", "buyer",
    "product", "item", "session", "event", "receipt", "ticket", "visitor", "student",
    "patient", "doctor", "claim", "shipment", "delivery", "device", "lead", "deal",
    "contract", "case", "record", "row", "person", "org", "partner", "merchant",
    "sub", "subscription", "profile", "uniq", "unique", "post", "comment", "message",
    "channel", "asset", "entry", "batch", "lot", "vehicle"
)

MEASURE_SUFFIX_KEYWORDS = (
    "amount", "amt", "price", "revenue", "sales", "cost", "fee", "margin", "profit",
    "rate", "score", "percent", "percentage", "pct", "quantity", "qty", "units",
    "count", "sum", "total", "avg", "average", "balance", "salary", "spend", "spending",
    "value", "discount", "tax", "budget", "volume", "weight", "height", "width", "depth",
    "size", "distance", "duration", "hours", "minutes", "seconds"
)

def is_identifier_column(col_name: str) -> bool:
    """
    Dynamically determines whether a column represents an identifier (ID, key, code, hash)
    rather than a numeric metric/measure.
    Prioritizes identifiers regardless of whether values are numeric (e.g. 1001, 1002, 1003).
    Ensures monetary, quantity, and measurement columns (e.g. payment_amount, total_count)
    are never misclassified as identifiers.
    """
    if not col_name:
        return False
        
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', str(col_name).strip()).lower()
    norm = re.sub(r'[^a-z0-9]+', '_', s).strip('_')
    if not norm:
        return False

    tokens = norm.split('_')

    # Exact standard ID tokens
    if norm in ("id", "uuid", "guid", "code", "index", "idx", "key", "token", "hash", "pk", "fk", "zip", "zipcode", "postal_code", "postcode", "pin_code", "pincode", "serial_number", "phone_number", "account_number"):
        return True

    # Date/Time & Year columns are temporal dimensions, NEVER identifiers
    if norm in ("year", "yr", "month", "day", "date", "quarter", "qtr", "time", "hour", "minute", "second", "timestamp", "datetime", "created_at", "updated_at", "order_date", "transaction_date") or norm.endswith(("_year", "_yr", "_month", "_day", "_date", "_timestamp", "_datetime")):
        return False

    # Check if this column is explicitly a measure/quantity/count
    if norm.startswith(("number_of_", "num_of_", "count_of_")):
        return False
    if tokens[-1] in MEASURE_SUFFIX_KEYWORDS and tokens[-1] != "id":
        return False

    # Common ID suffixes: _id, _ids, _uuid, _guid, _code, _key, _pk, _fk, _token, _hash
    if tokens[-1] in ("id", "ids", "uuid", "guid", "code", "key", "pk", "fk", "token", "hash", "idx", "index"):
        return True

    # Common ID prefixes: id_, uuid_, guid_, code_, pk_, fk_
    if tokens[0] in ("id", "uuid", "guid", "code", "pk", "fk"):
        return True

    # Number/No suffixes when tied to an entity (e.g. order_number, invoice_no, card_number)
    if tokens[-1] in ("no", "number", "num") and len(tokens) > 1:
        if any(stem in norm for stem in ENTITY_STEMS) or tokens[0] in ("ref", "reference", "serial", "tracking", "card", "phone"):
            return True

    # Suffix 'id' without underscore (e.g. paymentid, orderid, customerid, invoiceid, transid)
    if norm.endswith("id") and len(norm) > 2:
        if any(norm.startswith(stem) for stem in ENTITY_STEMS) or norm not in NON_ID_WORDS:
            return True

    return False

class FinancialRole:
    IDENTIFIER = "IDENTIFIER"
    QUANTITY = "QUANTITY"
    UNIT_PRICE = "UNIT_PRICE"
    SELLING_PRICE = "SELLING_PRICE"
    COST_PRICE = "COST_PRICE"
    DISCOUNT_AMOUNT = "DISCOUNT_AMOUNT"
    DISCOUNT_PERCENT = "DISCOUNT_PERCENT"
    TAX_AMOUNT = "TAX_AMOUNT"
    TAX_PERCENT = "TAX_PERCENT"
    SHIPPING_FEE = "SHIPPING_FEE"
    OTHER_FEE = "OTHER_FEE"
    GROSS_REVENUE = "GROSS_REVENUE"
    NET_REVENUE = "NET_REVENUE"
    REFUND = "REFUND"
    RETURN = "RETURN"
    COGS = "COGS"
    PROFIT = "PROFIT"
    PAYMENT_AMOUNT = "PAYMENT_AMOUNT"
    OTHER = "OTHER"

def classify_column_role(col_name: str, ctype: str = "", sample_vals: list = None) -> str:
    """
    Intelligently classifies a column into its financial role.
    Distinguishes identifiers, quantities, prices, discounts, taxes, fees, refunds, and revenue.
    """
    if not col_name:
        return FinancialRole.OTHER

    # 1. Identifier detection has strict priority
    if is_identifier_column(col_name):
        return FinancialRole.IDENTIFIER

    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', str(col_name).strip()).lower()
    norm = re.sub(r'[^a-z0-9]+', '_', s).strip('_')

    # Date/Time & Year columns are temporal dimensions, NEVER revenue or identifiers
    if norm in ("year", "yr", "month", "day", "date", "quarter", "qtr", "time", "hour", "minute", "second", "timestamp", "datetime", "created_at", "updated_at", "order_date", "transaction_date") or norm.endswith(("_year", "_yr", "_month", "_day", "_date", "_timestamp", "_datetime")):
        return FinancialRole.OTHER

    # Unrelated numeric business metrics (HR, demographic, survey, education) are NEVER revenue
    if norm in ("age", "salary", "experience", "rating", "score", "employee_count", "department_code", "tenure", "gpa", "marks", "rank", "level", "weight", "height", "duration", "distance", "step", "steps", "count"):
        return FinancialRole.OTHER

    # 2. Rates, percentages, and ratios that are NOT monetary amounts
    if norm.endswith(("_rate", "_ratio", "_pct", "_percent", "_percentage")) or norm in ("rate", "ratio", "pct", "percent", "percentage"):
        if any(t in norm for t in ("tax", "gst", "vat")):
            return FinancialRole.TAX_PERCENT
        if any(d in norm for d in ("discount", "promo", "coupon", "markdown", "rebate")):
            return FinancialRole.DISCOUNT_PERCENT
        return FinancialRole.OTHER

    # 3. Non-transactional counts (ratings, reviews, impressions, views, clicks, users, items)
    if any(r in norm for r in ("rating", "review", "view", "click", "impression", "visit", "session", "follower", "subscriber", "vote", "star", "like", "column", "table", "product_count", "products_used")):
        return FinancialRole.OTHER

    # 4. Payment Amount
    if norm in ("payment_amount", "paid_amount", "transaction_amount", "transacted_amount") or (norm.endswith(("_amount", "_value")) and any(p in norm for p in ("payment", "paid", "transact"))):
        return FinancialRole.PAYMENT_AMOUNT

    # 5. Selling Price (discounted price, sale price, retail price, selling price)
    if norm in ("selling_price", "sale_price", "discounted_price", "retail_price", "final_price", "special_price") or norm.endswith(("_selling_price", "_sale_price", "_discounted_price")):
        return FinancialRole.SELLING_PRICE

    # 6. Unit Price / Catalog Price
    if norm in ("price", "unit_price", "item_price", "product_price", "unit_rate", "list_price", "marked_price", "mrp", "actual_price") or (norm.endswith(("_price", "_mrp")) and not norm.endswith(("_cost_price", "_purchase_price"))):
        return FinancialRole.UNIT_PRICE

    # 7. Refund & Return (monetary values only)
    if any(r in norm for r in ("refund", "refund_amount", "refund_value", "chargeback", "cancelled_amount", "canceled_amount")):
        return FinancialRole.REFUND
    if norm in ("returns", "return_amount", "returned_quantity", "credit_note") or (norm.startswith("return_") and norm.endswith(("_amount", "_value", "_qty", "_quantity", "_total"))):
        return FinancialRole.RETURN

    # 8. Discount (Amount vs Percent) - only if NOT a price
    if any(d in norm for d in ("discount", "promo_discount", "coupon_discount", "markdown", "rebate")):
        if any(p in norm for p in ("percent", "percentage", "rate", "pct")) or norm.endswith("_pct"):
            return FinancialRole.DISCOUNT_PERCENT
        if sample_vals and any("%" in str(v) for v in sample_vals if v is not None):
            return FinancialRole.DISCOUNT_PERCENT
        return FinancialRole.DISCOUNT_AMOUNT

    # 9. Tax / GST / VAT (Amount vs Percent)
    if any(t in norm for t in ("tax", "gst", "vat")):
        if any(p in norm for p in ("rate", "percent", "percentage", "pct")) or norm.endswith("_rate"):
            return FinancialRole.TAX_PERCENT
        if sample_vals and any("%" in str(v) for v in sample_vals if v is not None):
            return FinancialRole.TAX_PERCENT
        return FinancialRole.TAX_AMOUNT

    # 10. Shipping / Delivery
    if any(sh in norm for sh in ("shipping", "delivery")):
        return FinancialRole.SHIPPING_FEE

    # 11. Other Fees
    if any(f in norm for f in ("handling_fee", "handling_charge", "platform_fee", "service_fee", "transaction_fee", "processing_fee", "other_charges", "additional_charges")):
        return FinancialRole.OTHER_FEE

    # 12. Cost / COGS / Purchase Price
    if norm in ("cost_price", "purchase_price", "purchase_cost", "unit_cost", "cost_per_unit"):
        return FinancialRole.COST_PRICE
    if norm in ("cogs", "cost_of_goods_sold", "total_cost", "cost", "expense", "expenses") or norm.endswith(("_cogs", "_expense", "_expenses")):
        return FinancialRole.COGS

    # 13. Profit
    if any(pr in norm for pr in ("profit", "net_profit", "gross_profit", "profit_amount", "total_profit", "earnings")):
        return FinancialRole.PROFIT

    # 14. Quantity
    if norm in ("quantity", "qty", "units", "units_sold", "number_of_units", "item_count", "pieces", "pcs", "volume", "items_sold") or norm.endswith(("_quantity", "_qty", "_units_sold", "_pieces")):
        return FinancialRole.QUANTITY

    # 15. Gross Revenue / Gross Sales
    if norm in ("gross_sales", "sales_value", "gross_revenue", "total_sales", "subtotal", "gross_amount") or norm.endswith(("_gross_sales", "_gross_revenue")):
        return FinancialRole.GROSS_REVENUE

    # 16. Net Revenue / Authoritative Explicit Revenue
    if norm in ("net_revenue", "net_sales", "total_revenue", "revenue", "sales", "sales_amount", "total_amount", "order_total", "invoice_total", "grand_total", "line_total", "extended_price", "total_value", "final_amount", "net_amount") or norm.endswith(("_net_revenue", "_net_sales", "_total_amount", "_order_total", "_invoice_total", "_grand_total")):
        return FinancialRole.NET_REVENUE

    return FinancialRole.OTHER

def inspect_dataset_schema(db: Session, table_name: str) -> Dict[str, Any]:
    """
    Intelligently profiles an arbitrary database table to detect:
    - column names and types
    - financial role classification for each column
    - numeric columns (strictly excluding identifier columns)
    - categorical columns
    - date/datetime columns
    - ID / identifier columns (prioritized over numeric types)
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

    # Financial role classifications
    financial_roles = {}
    for col in columns:
        vals = [r.get(col) for r in sample_rows if r.get(col) is not None]
        financial_roles[col] = classify_column_role(col, col_type_map.get(col, ""), vals)

    # Classify columns dynamically
    numeric_columns = []
    date_columns = []
    categorical_columns = []
    id_columns = []
    nullable_columns = [c["name"] for c in col_objs if c.get("nullable", True)]

    # Date regex patterns for string-stored dates
    date_pattern = re.compile(r"^\d{4}[-/]\d{1,2}([-/]\d{1,2})?(\s+\d{1,2}:\d{2}(:\d{2})?)?$")

    for col in columns:
        ctype = col_type_map.get(col, "")
        role = financial_roles[col]

        # RULE 1 & RULE 2: Identifier detection takes strict priority over numeric detection
        # Numeric-looking ID columns (e.g. payment_id=1001, 1002, 1003) MUST be classified as identifiers
        if role == FinancialRole.IDENTIFIER:
            id_columns.append(col)
            continue

        # 1. Date/Time Detection
        if any(dk in ctype for dk in DATE_TYPE_KEYWORDS):
            date_columns.append(col)
            continue
        
        # Check sample rows for date-like strings
        if sample_rows:
            sample_vals = [str(r[col]).strip() for r in sample_rows if r.get(col) is not None]
            if sample_vals and all(date_pattern.match(v) for v in sample_vals if v):
                date_columns.append(col)
                continue

        # 2. Numeric Detection (Excludes all identifiers by definition)
        if any(nt in ctype for nt in NUMERIC_TYPE_KEYWORDS):
            numeric_columns.append(col)
            continue

        # Check sample rows for numeric values stored as strings
        if sample_rows:
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
        categorical_columns.append(col)

    # Detect profit and margin columns specifically if present
    PROFIT_KEYWORDS = ("profit", "net_profit", "gross_profit", "profit_amount", "total_profit", "earnings")
    MARGIN_KEYWORDS = ("profit_margin", "margin_percent", "margin_percentage", "margin_pct", "net_margin", "gross_margin", "margin")

    profit_col = next((c for c in columns if any(pk == c.lower() or c.lower().endswith(f"_{pk}") for pk in PROFIT_KEYWORDS)), None)
    margin_col = next((c for c in columns if any(mk == c.lower() or c.lower().endswith(f"_{mk}") for mk in MARGIN_KEYWORDS)), None)

    # Key financial column resolution
    REVENUE_HIERARCHY = (
        "net_revenue", "net_sales", "total_revenue", "sales_amount", "total_amount",
        "order_total", "invoice_total", "grand_total", "revenue", "sales", "line_total",
        "extended_price", "total_value", "final_amount", "net_amount"
    )
    authoritative_revenue_col = next(
        (c for pref in REVENUE_HIERARCHY for c in columns if financial_roles.get(c) == FinancialRole.NET_REVENUE and pref in c.lower()),
        next((c for c in columns if financial_roles.get(c) == FinancialRole.NET_REVENUE), None)
    )

    gross_sales_col = next(
        (c for c in columns if financial_roles.get(c) == FinancialRole.GROSS_REVENUE), None
    )

    selling_price_col = next(
        (c for c in columns if financial_roles.get(c) == FinancialRole.SELLING_PRICE), None
    )
    unit_price_col = next(
        (c for c in columns if financial_roles.get(c) == FinancialRole.UNIT_PRICE), None
    )
    price_col = selling_price_col or unit_price_col

    quantity_col = next(
        (c for c in columns if financial_roles.get(c) == FinancialRole.QUANTITY), None
    )

    discount_amount_col = next(
        (c for c in columns if financial_roles.get(c) == FinancialRole.DISCOUNT_AMOUNT), None
    )
    discount_percent_col = next(
        (c for c in columns if financial_roles.get(c) == FinancialRole.DISCOUNT_PERCENT), None
    )
    discount_col = discount_amount_col or discount_percent_col
    discount_type = "PERCENT" if discount_percent_col else ("AMOUNT" if discount_amount_col else None)

    tax_amount_col = next(
        (c for c in columns if financial_roles.get(c) == FinancialRole.TAX_AMOUNT), None
    )
    tax_percent_col = next(
        (c for c in columns if financial_roles.get(c) == FinancialRole.TAX_PERCENT), None
    )
    tax_col = tax_amount_col or tax_percent_col
    tax_type = "PERCENT" if tax_percent_col else ("AMOUNT" if tax_amount_col else None)

    shipping_col = next(
        (c for c in columns if financial_roles.get(c) == FinancialRole.SHIPPING_FEE), None
    )
    refund_col = next(
        (c for c in columns if financial_roles.get(c) in (FinancialRole.REFUND, FinancialRole.RETURN)), None
    )
    cost_col = next(
        (c for c in columns if financial_roles.get(c) in (FinancialRole.COGS, FinancialRole.COST_PRICE)), None
    )
    payment_amount_col = next(
        (c for c in columns if financial_roles.get(c) == FinancialRole.PAYMENT_AMOUNT), None
    )

    # Dynamic Selection of Primary Metric (without assuming sales/revenue)
    primary_metric = None
    if authoritative_revenue_col:
        primary_metric = authoritative_revenue_col
    elif payment_amount_col:
        primary_metric = payment_amount_col
    elif gross_sales_col:
        primary_metric = gross_sales_col
    elif price_col and quantity_col:
        # Both exist -> will be calculated in analysis_service
        primary_metric = price_col
    elif cost_col:
        primary_metric = cost_col
    elif numeric_columns:
        # Prefer actual financial / measure columns over arbitrary numbers
        NON_METRIC_ROLES = (FinancialRole.IDENTIFIER, FinancialRole.UNIT_PRICE, FinancialRole.TAX_PERCENT, FinancialRole.DISCOUNT_PERCENT)
        valid_candidates = [c for c in numeric_columns if financial_roles.get(c) not in NON_METRIC_ROLES]
        primary_metric = valid_candidates[0] if valid_candidates else numeric_columns[0]

    # Secondary metric
    secondary_metric = next((c for c in numeric_columns if c != primary_metric and financial_roles.get(c) != FinancialRole.IDENTIFIER), None)

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

    schema_dict = {
        "table_name": table_name,
        "dialect": dialect_name,
        "row_count": row_count,
        "columns": columns,
        "column_types": col_type_map,
        "financial_roles": financial_roles,
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
        "margin_col": margin_col,
        "authoritative_revenue_col": authoritative_revenue_col,
        "gross_sales_col": gross_sales_col,
        "price_col": price_col,
        "selling_price_col": selling_price_col,
        "unit_price_col": unit_price_col,
        "quantity_col": quantity_col,
        "discount_col": discount_col,
        "discount_type": discount_type,
        "tax_col": tax_col,
        "tax_type": tax_type,
        "shipping_col": shipping_col,
        "refund_col": refund_col,
        "cost_col": cost_col,
        "payment_amount_col": payment_amount_col
    }

    schema_dict["resolved_revenue"] = resolve_revenue_metric(
        columns=columns,
        financial_roles=financial_roles,
        dialect=dialect_name,
        schema=schema_dict
    )

    return schema_dict

def resolve_revenue_metric(
    db: Optional[Session] = None,
    table_name: Optional[str] = None,
    schema: Optional[Dict[str, Any]] = None,
    columns: Optional[List[str]] = None,
    financial_roles: Optional[Dict[str, str]] = None,
    dialect: str = "sqlite"
) -> Dict[str, Any]:
    """
    Single authoritative function to resolve the Revenue metric.
    Strictly ensures the Revenue KPI represents ONLY actual revenue.
    Never falls back to summing arbitrary numeric columns (e.g. Year, Date, IDs, Quantity alone, Price alone, Salary, Age).

    Resolution Hierarchy:
    1. Authoritative explicit revenue column (NET_REVENUE or PAYMENT_AMOUNT)
    2. Gross revenue / gross sales with deductions (GROSS_REVENUE)
    3. Price * Quantity with deductions (SELLING_PRICE / UNIT_PRICE AND QUANTITY)
    4. ELSE: value = 0, is_valid = False, source = 'No valid revenue source'
    """
    if schema is None and db is not None and table_name is not None:
        schema = inspect_dataset_schema(db, table_name)

    if schema is not None:
        if columns is None:
            columns = schema.get("columns", [])
        if financial_roles is None:
            financial_roles = schema.get("financial_roles", {})
        dialect = schema.get("dialect", dialect)

    if columns is None:
        columns = []
    if financial_roles is None:
        financial_roles = {}

    for c in columns:
        if c not in financial_roles:
            financial_roles[c] = classify_column_role(c)

    NUMERIC_TYPES = ("FLOAT", "REAL", "INT", "DOUBLE", "DECIMAL", "NUMERIC", "BIGINT", "SMALLINT")
    col_type_map = schema.get("column_types", {}) if schema else {}

    def col_expr(c: str) -> str:
        ctype = col_type_map.get(c, "").upper()
        quoted = quote_ident(c)
        if ctype and any(t in ctype for t in NUMERIC_TYPES):
            return quoted
        return clean_numeric_sql(quoted, dialect=dialect)

    # 1. Authoritative explicit revenue column
    authoritative_rev = None
    REVENUE_PREFERENCE = (
        "net_revenue", "net_sales", "total_revenue", "totalrevenue", "revenue",
        "sales", "total_sales", "sales_amount", "sales_value", "total_amount",
        "order_total", "invoice_total", "transaction_amount", "payment_amount",
        "grand_total", "subtotal", "line_total", "extended_price", "total_value",
        "final_amount", "net_amount"
    )
    for pref in REVENUE_PREFERENCE:
        for c in columns:
            r = financial_roles.get(c)
            if r in (FinancialRole.NET_REVENUE, FinancialRole.PAYMENT_AMOUNT) and (c.lower() == pref or pref in c.lower()) and not is_identifier_column(c):
                authoritative_rev = c
                break
        if authoritative_rev:
            break

    if not authoritative_rev:
        authoritative_rev = next(
            (c for c in columns if financial_roles.get(c) in (FinancialRole.NET_REVENUE, FinancialRole.PAYMENT_AMOUNT) and not is_identifier_column(c)),
            None
        )

    # 2. Gross Sales column
    gross_sales_col = next(
        (c for c in columns if financial_roles.get(c) == FinancialRole.GROSS_REVENUE and not is_identifier_column(c)),
        None
    )

    # 3. Price & Quantity columns
    selling_price_col = next(
        (c for c in columns if financial_roles.get(c) == FinancialRole.SELLING_PRICE and not is_identifier_column(c)),
        None
    )
    unit_price_col = next(
        (c for c in columns if financial_roles.get(c) == FinancialRole.UNIT_PRICE and not is_identifier_column(c)),
        None
    )
    price_col = selling_price_col or unit_price_col

    quantity_col = next(
        (c for c in columns if financial_roles.get(c) == FinancialRole.QUANTITY and not is_identifier_column(c)),
        None
    )

    # Deductions: Discount & Refund
    discount_amount_col = next(
        (c for c in columns if financial_roles.get(c) == FinancialRole.DISCOUNT_AMOUNT and not is_identifier_column(c)),
        None
    )
    discount_percent_col = next(
        (c for c in columns if financial_roles.get(c) == FinancialRole.DISCOUNT_PERCENT and not is_identifier_column(c)),
        None
    )
    discount_col = discount_amount_col or discount_percent_col
    discount_type = "PERCENT" if discount_percent_col else ("AMOUNT" if discount_amount_col else None)

    refund_col = next(
        (c for c in columns if financial_roles.get(c) in (FinancialRole.REFUND, FinancialRole.RETURN) and not is_identifier_column(c)),
        None
    )

    has_real_revenue = False
    is_valid = False
    revenue_expr = "0"
    gross_sales_expr = None
    revenue_source = "No valid revenue source"
    label = "Revenue"

    # Hierarchy 1: Authoritative explicit revenue column
    if authoritative_rev and authoritative_rev in columns and not is_identifier_column(authoritative_rev):
        has_real_revenue = True
        is_valid = True
        is_already_net = any(k in authoritative_rev.lower() for k in ("net", "total_revenue", "totalrevenue", "final", "settled", "grand_total"))
        if not is_already_net and (refund_col or discount_col):
            gross_sales_expr = col_expr(authoritative_rev)
            parts = [gross_sales_expr]
            if discount_col and discount_col in columns:
                if discount_type == "PERCENT":
                    parts.append(f"- COALESCE(({gross_sales_expr} * ({col_expr(discount_col)} / 100.0)), 0)")
                else:
                    parts.append(f"- COALESCE({col_expr(discount_col)}, 0)")
            if refund_col and refund_col in columns:
                parts.append(f"- COALESCE({col_expr(refund_col)}, 0)")
            revenue_expr = f"({' '.join(parts)})"
            revenue_source = "revenue_minus_deductions"
            label = "Net Revenue"
        else:
            revenue_expr = col_expr(authoritative_rev)
            gross_sales_expr = col_expr(gross_sales_col) if (gross_sales_col and gross_sales_col in columns) else revenue_expr
            revenue_source = "authoritative_revenue"
            label = authoritative_rev.replace("_", " ").title()

    # Hierarchy 2: Gross Sales with optional deductions
    elif gross_sales_col and gross_sales_col in columns and not is_identifier_column(gross_sales_col):
        has_real_revenue = True
        is_valid = True
        gross_sales_expr = col_expr(gross_sales_col)
        parts = [gross_sales_expr]
        if discount_col and discount_col in columns:
            if discount_type == "PERCENT":
                parts.append(f"- COALESCE(({gross_sales_expr} * ({col_expr(discount_col)} / 100.0)), 0)")
            else:
                parts.append(f"- COALESCE({col_expr(discount_col)}, 0)")
        if refund_col and refund_col in columns:
            parts.append(f"- COALESCE({col_expr(refund_col)}, 0)")
        revenue_expr = f"({' '.join(parts)})"
        revenue_source = "gross_sales_with_deductions"
        label = "Net Revenue"

    # Hierarchy 3: Price * Quantity with optional deductions
    elif price_col and quantity_col and price_col in columns and quantity_col in columns and not is_identifier_column(price_col) and not is_identifier_column(quantity_col):
        has_real_revenue = True
        is_valid = True
        gross_sales_expr = f"({col_expr(price_col)} * {col_expr(quantity_col)})"
        parts = [gross_sales_expr]
        if discount_col and discount_col in columns:
            if discount_type == "PERCENT":
                parts.append(f"- COALESCE(({gross_sales_expr} * ({col_expr(discount_col)} / 100.0)), 0)")
            else:
                parts.append(f"- COALESCE({col_expr(discount_col)}, 0)")
        if refund_col and refund_col in columns:
            parts.append(f"- COALESCE({col_expr(refund_col)}, 0)")
        revenue_expr = f"({' '.join(parts)})"
        revenue_source = "price_times_quantity"
        label = "Net Sales" if (discount_col or refund_col) else "Revenue"

    # Hierarchy 4: ABSOLUTELY NO FALLBACK
    # Price alone, Quantity alone, Year, Date, ID, Cost, Profit, Tax, Shipping, Salary, Age, etc. are NOT revenue
    else:
        has_real_revenue = False
        is_valid = False
        revenue_expr = "0"
        gross_sales_expr = None
        revenue_source = "No valid revenue source"
        label = "Revenue"

    value = 0.0
    if db is not None and table_name is not None and has_real_revenue and is_valid:
        try:
            q = f"SELECT COALESCE(SUM({revenue_expr}), 0) FROM {quote_ident(table_name)}"
            res = db.execute(text(q)).scalar()
            value = float(res) if res is not None else 0.0
        except Exception:
            value = 0.0
    else:
        value = 0.0

    return {
        "metric": "revenue",
        "label": label,
        "value": round(float(value), 2),
        "source": revenue_source,
        "is_valid": is_valid,
        "has_real_revenue": has_real_revenue,
        "revenue_expr": revenue_expr,
        "rev_kpi_expr": f"COALESCE(SUM({revenue_expr}), 0)" if has_real_revenue else "0.0",
        "gross_sales_expr": gross_sales_expr,
        "raw_rev_col": authoritative_rev or gross_sales_col,
        "price_col": price_col,
        "quantity_col": quantity_col,
        "discount_col": discount_col,
        "discount_type": discount_type,
        "refund_col": refund_col
    }

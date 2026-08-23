import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

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
            # Check if column is numeric or can be converted to numeric
            try:
                numeric_col = pd.to_numeric(df[col])
                if not pd.api.types.is_bool_dtype(numeric_col):
                    summary["numeric_summaries"][col] = {
                        "sum": float(numeric_col.sum()) if not pd.isna(numeric_col.sum()) else 0.0,
                        "mean": float(numeric_col.mean()) if not pd.isna(numeric_col.mean()) else 0.0,
                        "min": float(numeric_col.min()) if not pd.isna(numeric_col.min()) else 0.0,
                        "max": float(numeric_col.max()) if not pd.isna(numeric_col.max()) else 0.0
                    }
            except (ValueError, TypeError):
                continue

    return summary

def get_dashboard_data(db: Session) -> dict:
    """
    Retrieves all dashboard KPIs and chart data using optimized SQL queries and Pandas formatting.
    """
    # 1. Fetch KPI metrics
    kpi_query = """
    SELECT
        COALESCE(SUM(revenue), 0) AS total_revenue,
        COALESCE(SUM(profit), 0) AS total_profit,
        COUNT(DISTINCT order_id) AS total_orders,
        COUNT(DISTINCT customer_id) AS total_customers
    FROM sales
    """
    kpi_res = db.execute(text(kpi_query)).fetchone()
    
    total_revenue = float(kpi_res[0])
    total_profit = float(kpi_res[1])
    total_orders = int(kpi_res[2])
    total_customers = int(kpi_res[3])
    average_order_value = total_revenue / total_orders if total_orders > 0 else 0.0

    # 2. Fetch Revenue Trend (Monthly)
    trend_query = """
    SELECT strftime('%Y-%m', order_date) AS month, SUM(revenue) AS revenue
    FROM sales
    GROUP BY month
    ORDER BY month ASC
    """
    trend_df = pd.read_sql(trend_query, db.bind)
    revenue_trend = trend_df.to_dict(orient="records")

    # 3. Revenue by Category
    cat_query = """
    SELECT category, SUM(revenue) AS revenue
    FROM sales
    GROUP BY category
    ORDER BY revenue DESC
    """
    cat_df = pd.read_sql(cat_query, db.bind)
    revenue_by_category = cat_df.to_dict(orient="records")

    # 4. Revenue by Region
    reg_query = """
    SELECT region, SUM(revenue) AS revenue
    FROM sales
    GROUP BY region
    ORDER BY revenue DESC
    """
    reg_df = pd.read_sql(reg_query, db.bind)
    revenue_by_region = reg_df.to_dict(orient="records")

    # 5. Profit by Category
    prof_cat_query = """
    SELECT category, SUM(profit) AS profit
    FROM sales
    GROUP BY category
    ORDER BY profit DESC
    """
    prof_cat_df = pd.read_sql(prof_cat_query, db.bind)
    profit_by_category = prof_cat_df.to_dict(orient="records")

    # 6. Top 10 Customers
    cust_query = """
    SELECT customer_name, SUM(revenue) AS revenue, SUM(profit) AS profit
    FROM sales
    GROUP BY customer_name
    ORDER BY revenue DESC
    LIMIT 10
    """
    cust_df = pd.read_sql(cust_query, db.bind)
    top_customers = cust_df.to_dict(orient="records")

    # 7. Monthly Orders
    orders_query = """
    SELECT strftime('%Y-%m', order_date) AS month, COUNT(DISTINCT order_id) AS orders
    FROM sales
    GROUP BY month
    ORDER BY month ASC
    """
    orders_df = pd.read_sql(orders_query, db.bind)
    monthly_orders = orders_df.to_dict(orient="records")

    return {
        "metrics": {
            "total_revenue": round(total_revenue, 2),
            "total_profit": round(total_profit, 2),
            "total_orders": total_orders,
            "total_customers": total_customers,
            "average_order_value": round(average_order_value, 2)
        },
        "revenue_trend": revenue_trend,
        "revenue_by_category": revenue_by_category,
        "revenue_by_region": revenue_by_region,
        "profit_by_category": profit_by_category,
        "top_customers": top_customers,
        "monthly_orders": monthly_orders
    }

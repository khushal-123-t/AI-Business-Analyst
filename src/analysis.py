import pandas as pd
from sqlalchemy import create_engine


# -----------------------------
# Connect to database
# -----------------------------

engine = create_engine(
    "sqlite:///database/business.db"
)


# -----------------------------
# Load sales data
# -----------------------------

query = """
SELECT *
FROM sales
"""

df = pd.read_sql(query, engine)


# -----------------------------
# Basic Business Metrics
# -----------------------------

total_revenue = df["revenue"].sum()

total_profit = df["profit"].sum()

total_orders = df["order_id"].nunique()

total_customers = df["customer_id"].nunique()

average_order_value = (
    total_revenue / total_orders
)


# -----------------------------
# Display Results
# -----------------------------

print("\n========== BUSINESS SUMMARY ==========\n")

print(f"Total Revenue       : ₹{total_revenue:,.2f}")

print(f"Total Profit        : ₹{total_profit:,.2f}")

print(f"Total Orders        : {total_orders:,}")

print(f"Total Customers     : {total_customers:,}")

print(
    f"Average Order Value : ₹{average_order_value:,.2f}"
)


# -----------------------------
# Revenue by Category
# -----------------------------

category_sales = (
    df.groupby("category")["revenue"]
    .sum()
    .sort_values(ascending=False)
)

print("\n========== REVENUE BY CATEGORY ==========\n")

print(category_sales)


# -----------------------------
# Revenue by Region
# -----------------------------

region_sales = (
    df.groupby("region")["revenue"]
    .sum()
    .sort_values(ascending=False)
)

print("\n========== REVENUE BY REGION ==========\n")

print(region_sales)


# -----------------------------
# Top 10 Customers
# -----------------------------

top_customers = (
    df.groupby("customer_name")["revenue"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
)

print("\n========== TOP 10 CUSTOMERS ==========\n")

print(top_customers)
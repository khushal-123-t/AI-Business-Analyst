import unittest
import sys
import os
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database.connection import SessionLocal, engine
from backend.services.schema_service import inspect_dataset_schema
from backend.services.analysis_service import get_dashboard_data, clean_numeric_sql
from backend.services.llm_service import generate_sql, clean_generated_sql, get_db_dialect, sanitize_db_error_message
from backend.main import sanitize_dataframe_columns
from backend.utils.sql_validator import is_safe_sql

class TestDynamicSchemasAndIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        # Dataset A: date, product, region, sales, quantity
        df_a = pd.DataFrame([
            {"date": "2025-01-15", "product": "Laptop", "region": "North", "sales": 1200.0, "quantity": 2},
            {"date": "2025-01-20", "product": "Mouse", "region": "South", "sales": 50.0, "quantity": 5},
            {"date": "2025-02-10", "product": "Monitor", "region": "East", "sales": 600.0, "quantity": 3},
            {"date": "2025-02-15", "product": "Keyboard", "region": "West", "sales": 150.0, "quantity": 3}
        ])

        # Dataset B: employee_id, department, salary, joining_date
        df_b = pd.DataFrame([
            {"employee_id": 101, "department": "Engineering", "salary": 95000, "joining_date": "2023-03-01"},
            {"employee_id": 102, "department": "Sales", "salary": 75000, "joining_date": "2023-06-15"},
            {"employee_id": 103, "department": "Marketing", "salary": 68000, "joining_date": "2024-01-10"},
            {"employee_id": 104, "department": "Engineering", "salary": 110000, "joining_date": "2024-05-01"}
        ])

        # Dataset C: customer_name, city, age, spending_score
        df_c = pd.DataFrame([
            {"customer_name": "Alice Brown", "city": "New York", "age": 29, "spending_score": 88},
            {"customer_name": "Bob Green", "city": "Chicago", "age": 42, "spending_score": 65},
            {"customer_name": "Charlie White", "city": "Austin", "age": 35, "spending_score": 72},
            {"customer_name": "Diana Ross", "city": "Seattle", "age": 24, "spending_score": 94}
        ])

        # Dataset D: product_name, category, price, stock
        df_d = pd.DataFrame([
            {"product_name": "Desk Lamp", "category": "Home Decor", "price": 45.0, "stock": 120},
            {"product_name": "Ergo Chair", "category": "Office Furniture", "price": 280.0, "stock": 40},
            {"product_name": "Coffee Maker", "category": "Kitchen", "price": 95.0, "stock": 65},
            {"product_name": "Water Bottle", "category": "Accessories", "price": 20.0, "stock": 300}
        ])

        # Dataset E: date, website_visits, conversion_rate
        df_e = pd.DataFrame([
            {"date": "2025-01-01", "website_visits": 5400, "conversion_rate": 3.4},
            {"date": "2025-01-02", "website_visits": 6200, "conversion_rate": 3.8},
            {"date": "2025-02-01", "website_visits": 7100, "conversion_rate": 4.1},
            {"date": "2025-02-02", "website_visits": 6800, "conversion_rate": 3.9}
        ])

        with engine.begin() as conn:
            df_a.to_sql("test_dataset_a", conn, if_exists="replace", index=False)
            df_b.to_sql("test_dataset_b", conn, if_exists="replace", index=False)
            df_c.to_sql("test_dataset_c", conn, if_exists="replace", index=False)
            df_d.to_sql("test_dataset_d", conn, if_exists="replace", index=False)
            df_e.to_sql("test_dataset_e", conn, if_exists="replace", index=False)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        with engine.begin() as conn:
            for tbl in ["test_dataset_a", "test_dataset_b", "test_dataset_c", "test_dataset_d", "test_dataset_e"]:
                conn.execute(text(f"DROP TABLE IF EXISTS {tbl}"))

    def test_schema_profiling_dataset_a_retail(self):
        """Dataset A: date, product, region, sales, quantity"""
        schema = inspect_dataset_schema(self.db, "test_dataset_a")
        self.assertEqual(schema["primary_metric"], "sales")
        self.assertEqual(schema["primary_date"], "date")
        self.assertIn("product", schema["categorical_columns"])
        self.assertIn("region", schema["categorical_columns"])
        self.assertEqual(schema["row_count"], 4)

    def test_schema_profiling_dataset_b_hr(self):
        """Dataset B: employee_id, department, salary, joining_date"""
        schema = inspect_dataset_schema(self.db, "test_dataset_b")
        self.assertEqual(schema["primary_metric"], "salary")
        self.assertEqual(schema["primary_category"], "department")
        self.assertEqual(schema["primary_date"], "joining_date")
        self.assertIn("employee_id", schema["id_columns"])
        self.assertEqual(schema["row_count"], 4)

    def test_schema_profiling_dataset_c_customer(self):
        """Dataset C: customer_name, city, age, spending_score (NO date column)"""
        schema = inspect_dataset_schema(self.db, "test_dataset_c")
        self.assertIn(schema["primary_metric"], ["spending_score", "age"])
        self.assertIn(schema["primary_category"], ["city", "customer_name"])
        self.assertIsNone(schema["primary_date"])  # Correctly identifies no date column!
        self.assertEqual(schema["row_count"], 4)

    def test_schema_profiling_dataset_d_inventory(self):
        """Dataset D: product_name, category, price, stock (NO date column)"""
        schema = inspect_dataset_schema(self.db, "test_dataset_d")
        self.assertIn(schema["primary_metric"], ["price", "stock"])
        self.assertEqual(schema["primary_category"], "category")
        self.assertIsNone(schema["primary_date"])
        self.assertEqual(schema["row_count"], 4)

    def test_schema_profiling_dataset_e_marketing(self):
        """Dataset E: date, website_visits, conversion_rate (NO categorical column)"""
        schema = inspect_dataset_schema(self.db, "test_dataset_e")
        self.assertIn(schema["primary_metric"], ["website_visits", "conversion_rate"])
        self.assertEqual(schema["primary_date"], "date")
        self.assertEqual(len(schema["categorical_columns"]), 0)  # Correctly identifies no category!
        self.assertEqual(schema["row_count"], 4)

    def test_dashboard_generation_dataset_b_hr(self):
        """HR dataset has no revenue: total_revenue must be 0, not sum of salaries."""
        dash = get_dashboard_data(self.db, "test_dataset_b")
        self.assertIsNotNone(dash["metrics"])
        self.assertEqual(dash["metrics"]["total_revenue"], 0.0)
        self.assertEqual(dash["metrics"]["total_orders"], 4)         # 4 employees
        self.assertEqual(dash["metrics"]["average_order_value"], 0.0)
        self.assertTrue(any("revenue" in s.lower() for s in dash["skipped_visualizations"]))

    def test_dashboard_isolation_dataset_c_no_date(self):
        """Customer demographics (no date, no revenue) must have revenue=0 and gracefully skip charts without crashing."""
        dash = get_dashboard_data(self.db, "test_dataset_c")
        self.assertIsNotNone(dash["metrics"])
        self.assertEqual(dash["metrics"]["total_revenue"], 0.0)
        self.assertEqual(dash["revenue_trend"], []) # Skipped trend
        self.assertTrue(any("trend" in s.lower() or "revenue" in s.lower() for s in dash["skipped_visualizations"]))

    def test_dashboard_isolation_dataset_e_no_category(self):
        """Marketing traffic (no category, no revenue) must have revenue=0 and gracefully skip charts without crashing."""
        dash = get_dashboard_data(self.db, "test_dataset_e")
        self.assertIsNotNone(dash["metrics"])
        self.assertEqual(dash["metrics"]["total_revenue"], 0.0)
        self.assertEqual(dash["revenue_by_category"], []) # Skipped category
        self.assertTrue(any("category" in s.lower() or "revenue" in s.lower() for s in dash["skipped_visualizations"]))

    def test_security_sql_validator(self):
        """Verify blocked destructive SQL commands."""
        for blocked in ["DROP TABLE sales", "DELETE FROM sales", "UPDATE sales SET revenue = 0", "TRUNCATE TABLE sales", "ALTER TABLE sales DROP COLUMN date"]:
            is_safe, msg = is_safe_sql(blocked)
            self.assertFalse(is_safe, f"Expected unsafe for: {blocked}")

    def test_column_sanitization_reserved_keywords(self):
        """Verify reserved SQL keywords are safely renamed during CSV column sanitization."""
        df = pd.DataFrame(columns=["Order", "User", "Group", "Normal Col", "Category!"])
        cleaned = sanitize_dataframe_columns(df)
        cols = list(cleaned.columns)
        self.assertEqual(cols[0], "order_col")
        self.assertEqual(cols[1], "user_col")
        self.assertEqual(cols[2], "group_col")
        self.assertEqual(cols[3], "normal_col")
        self.assertEqual(cols[4], "category")

    def test_numeric_sql_dialects(self):
        """Verify clean_numeric_sql generates PostgreSQL and SQLite compatible SQL."""
        pg_sql = clean_numeric_sql("amount", dialect="postgresql")
        self.assertIn("REGEXP_REPLACE", pg_sql)
        self.assertIn("NUMERIC", pg_sql)

        sqlite_sql = clean_numeric_sql("amount", dialect="sqlite")
        self.assertIn("REPLACE", sqlite_sql)
        self.assertIn("REAL", sqlite_sql)

if __name__ == "__main__":
    unittest.main()

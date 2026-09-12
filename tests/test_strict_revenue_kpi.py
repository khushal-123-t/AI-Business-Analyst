import unittest
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.services.schema_service import (
    resolve_revenue_metric,
    classify_column_role,
    is_identifier_column,
    FinancialRole,
    inspect_dataset_schema
)
from backend.services.analysis_service import get_dashboard_data, invalidate_dashboard_cache

class TestStrictRevenueKPI(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        invalidate_dashboard_cache()

    def tearDown(self):
        self.session.close()

    def _create_table(self, table_name: str, data: dict):
        df = pd.DataFrame(data)
        df.to_sql(table_name, self.engine, if_exists="replace", index=False)
        invalidate_dashboard_cache(table_name)
        return table_name

    def test_01_year_only(self):
        """TEST 1: Year only: Year = [2022, 2023, 2024] -> Expected: Revenue = 0"""
        tbl = self._create_table("t1_year_only", {"Year": [2022, 2023, 2024, 2025]})
        res = resolve_revenue_metric(self.session, tbl)
        self.assertFalse(res["is_valid"])
        self.assertFalse(res["has_real_revenue"])
        self.assertEqual(res["value"], 0.0)

        dash = get_dashboard_data(self.session, tbl)
        self.assertEqual(dash["metrics"]["total_revenue"], 0.0)
        self.assertEqual(dash["metrics"]["revenue"], 0.0)
        self.assertEqual(dash["metrics"]["metric_labels"]["primary_metric_title"], "Total Revenue")

    def test_02_year_employee_id_salary(self):
        """TEST 2: Year + employee_id + salary -> Expected: Revenue = 0"""
        tbl = self._create_table("t2_hr", {
            "year": [2022, 2023, 2024],
            "employee_id": [101, 102, 103],
            "salary": [50000, 60000, 75000]
        })
        res = resolve_revenue_metric(self.session, tbl)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["value"], 0.0)

        dash = get_dashboard_data(self.session, tbl)
        self.assertEqual(dash["metrics"]["total_revenue"], 0.0)

    def test_03_quantity_only(self):
        """TEST 3: Quantity only -> Expected: Revenue = 0"""
        tbl = self._create_table("t3_qty_only", {
            "quantity": [10, 20, 30, 40]
        })
        res = resolve_revenue_metric(self.session, tbl)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["value"], 0.0)

        dash = get_dashboard_data(self.session, tbl)
        self.assertEqual(dash["metrics"]["total_revenue"], 0.0)
        self.assertEqual(dash["metrics"]["total_quantity"], 100.0)

    def test_04_price_only(self):
        """TEST 4: Price only -> Expected: Revenue = 0"""
        tbl = self._create_table("t4_price_only", {
            "price": [100.0, 200.0, 300.0]
        })
        res = resolve_revenue_metric(self.session, tbl)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["value"], 0.0)

        dash = get_dashboard_data(self.session, tbl)
        self.assertEqual(dash["metrics"]["total_revenue"], 0.0)
        self.assertEqual(dash["metrics"]["average_price"], 200.0)

    def test_05_price_plus_quantity(self):
        """TEST 5: Price + Quantity -> Expected: Revenue = Price × Quantity"""
        tbl = self._create_table("t5_pq", {
            "price": [10.0, 20.0, 30.0],
            "quantity": [2, 3, 4]
        })
        # 10*2 + 20*3 + 30*4 = 20 + 60 + 120 = 200.0
        res = resolve_revenue_metric(self.session, tbl)
        self.assertTrue(res["is_valid"])
        self.assertTrue(res["has_real_revenue"])
        self.assertEqual(res["value"], 200.0)

        dash = get_dashboard_data(self.session, tbl)
        self.assertEqual(dash["metrics"]["total_revenue"], 200.0)

    def test_06_revenue_column(self):
        """TEST 6: Revenue column -> Expected: Revenue = SUM(valid revenue column)"""
        tbl = self._create_table("t6_rev", {
            "revenue": [500.0, 1500.0, 2500.0]
        })
        res = resolve_revenue_metric(self.session, tbl)
        self.assertTrue(res["is_valid"])
        self.assertEqual(res["value"], 4500.0)

        dash = get_dashboard_data(self.session, tbl)
        self.assertEqual(dash["metrics"]["total_revenue"], 4500.0)

    def test_07_revenue_plus_year(self):
        """TEST 7: Revenue + Year -> Expected: Revenue = SUM(revenue) NOT SUM(year)"""
        tbl = self._create_table("t7_rev_yr", {
            "year": [2021, 2022, 2023],
            "revenue": [100.0, 200.0, 300.0]
        })
        # Year sum would be 6066, revenue is 600.0
        res = resolve_revenue_metric(self.session, tbl)
        self.assertTrue(res["is_valid"])
        self.assertEqual(res["value"], 600.0)

        dash = get_dashboard_data(self.session, tbl)
        self.assertEqual(dash["metrics"]["total_revenue"], 600.0)
        self.assertNotEqual(dash["metrics"]["total_revenue"], 6066.0)

    def test_08_order_id_plus_price(self):
        """TEST 8: Order ID + Price -> Expected: Revenue = 0"""
        tbl = self._create_table("t8_order_price", {
            "order_id": [1001, 1002, 1003],
            "price": [50.0, 75.0, 100.0]
        })
        res = resolve_revenue_metric(self.session, tbl)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["value"], 0.0)

        dash = get_dashboard_data(self.session, tbl)
        self.assertEqual(dash["metrics"]["total_revenue"], 0.0)

    def test_09_order_id_price_quantity(self):
        """TEST 9: Order ID + Price + Quantity -> Expected: Revenue = Price × Quantity"""
        tbl = self._create_table("t9_order_pq", {
            "order_id": [1001, 1002, 1003],
            "price": [15.0, 20.0, 25.0],
            "quantity": [2, 1, 4]
        })
        # 15*2 + 20*1 + 25*4 = 30 + 20 + 100 = 150.0
        res = resolve_revenue_metric(self.session, tbl)
        self.assertTrue(res["is_valid"])
        self.assertEqual(res["value"], 150.0)

        dash = get_dashboard_data(self.session, tbl)
        self.assertEqual(dash["metrics"]["total_revenue"], 150.0)
        self.assertEqual(dash["metrics"]["total_orders"], 3)

    def test_10_payment_id_plus_unrelated_numeric_fields(self):
        """TEST 10: Payment ID + unrelated numeric fields -> Expected: Revenue = 0 unless a valid payment/revenue amount exists."""
        tbl = self._create_table("t10_pay_unrelated", {
            "payment_id": [9001, 9002, 9003],
            "user_rating": [4.5, 4.8, 3.9],
            "session_count": [12, 15, 8]
        })
        res = resolve_revenue_metric(self.session, tbl)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["value"], 0.0)

        dash = get_dashboard_data(self.session, tbl)
        self.assertEqual(dash["metrics"]["total_revenue"], 0.0)

    def test_11_customer_id_age_year(self):
        """TEST 11: Customer ID + Age + Year -> Expected: Revenue = 0"""
        tbl = self._create_table("t11_demographics", {
            "customer_id": [501, 502, 503],
            "age": [28, 34, 45],
            "year": [2022, 2023, 2024]
        })
        res = resolve_revenue_metric(self.session, tbl)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["value"], 0.0)

        dash = get_dashboard_data(self.session, tbl)
        self.assertEqual(dash["metrics"]["total_revenue"], 0.0)

    def test_12_date_year_quantity(self):
        """TEST 12: Date + Year + Quantity -> Expected: Revenue = 0"""
        tbl = self._create_table("t12_warehouse_volume", {
            "order_date": ["2023-01-01", "2023-02-01", "2023-03-01"],
            "year": [2023, 2023, 2023],
            "quantity": [50, 60, 70]
        })
        res = resolve_revenue_metric(self.session, tbl)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["value"], 0.0)

        dash = get_dashboard_data(self.session, tbl)
        self.assertEqual(dash["metrics"]["total_revenue"], 0.0)
        self.assertEqual(dash["metrics"]["total_quantity"], 180.0)

    def test_13_salary_age_experience_year(self):
        """TEST 13: Salary + Age + Experience + Year -> Expected: Revenue = 0"""
        tbl = self._create_table("t13_employee_stats", {
            "salary": [80000, 95000, 110000],
            "age": [29, 35, 42],
            "experience": [4, 8, 15],
            "year": [2021, 2022, 2023]
        })
        res = resolve_revenue_metric(self.session, tbl)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["value"], 0.0)

        dash = get_dashboard_data(self.session, tbl)
        self.assertEqual(dash["metrics"]["total_revenue"], 0.0)

    def test_14_gross_sales_plus_discount(self):
        """TEST 14: Gross Sales + Discount -> Expected: Revenue = gross sales minus applicable discount"""
        tbl = self._create_table("t14_gross_discount", {
            "gross_sales": [1000.0, 2000.0, 3000.0],
            "discount_amount": [100.0, 250.0, 300.0]
        })
        # 6000 - 650 = 5350.0
        res = resolve_revenue_metric(self.session, tbl)
        self.assertTrue(res["is_valid"])
        self.assertEqual(res["value"], 5350.0)

        dash = get_dashboard_data(self.session, tbl)
        self.assertEqual(dash["metrics"]["total_revenue"], 5350.0)
        self.assertEqual(dash["metrics"]["gross_sales"], 6000.0)
        self.assertEqual(dash["metrics"]["total_discounts"], 650.0)

if __name__ == "__main__":
    unittest.main()

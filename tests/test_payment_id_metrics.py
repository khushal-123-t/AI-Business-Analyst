import unittest
import sys
import os
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database.connection import SessionLocal, engine
from backend.services.schema_service import inspect_dataset_schema, is_identifier_column
from backend.services.analysis_service import (
    get_dashboard_data,
    resolve_columns,
    analyze_result_set,
    format_identifier_count_title
)
from backend.services.llm_service import generate_sql, clean_generated_sql

class TestPaymentIdAndIdentifierMetrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        # Dataset 1: Numeric IDs (1001, 1002, 1003) with monetary amount column
        df_payments_with_amount = pd.DataFrame([
            {"payment_id": 1001, "payment_amount": 250.50, "payment_date": "2025-01-10", "payment_status": "COMPLETED"},
            {"payment_id": 1002, "payment_amount": 120.00, "payment_date": "2025-01-15", "payment_status": "COMPLETED"},
            {"payment_id": 1003, "payment_amount": 430.75, "payment_date": "2025-02-01", "payment_status": "PENDING"},
        ])

        # Dataset 2: Numeric IDs only (1001, 1002, 1003) WITHOUT any amount column
        df_payments_only_id = pd.DataFrame([
            {"payment_id": 1001, "customer_name": "Alice", "payment_method": "Credit Card"},
            {"payment_id": 1002, "customer_name": "Bob", "payment_method": "PayPal"},
            {"payment_id": 1003, "customer_name": "Charlie", "payment_method": "Bank Transfer"},
        ])

        # Dataset 3: "Payment ID" (spaced title case) with "Amount"
        df_payment_id_title = pd.DataFrame([
            {"Payment ID": 5001, "Amount": 99.99, "Category": "Electronics"},
            {"Payment ID": 5002, "Amount": 149.50, "Category": "Books"},
            {"Payment ID": 5003, "Amount": 20.00, "Category": "Apparel"},
        ])

        # Dataset 4: "paymentid" (lowercase concatenated) with "transacted_amount"
        df_paymentid_concat = pd.DataFrame([
            {"paymentid": 901, "transacted_amount": 300.0, "vendor": "Stripe"},
            {"paymentid": 902, "transacted_amount": 150.0, "vendor": "Square"},
        ])

        with engine.begin() as conn:
            df_payments_with_amount.to_sql("test_payments_amount", conn, if_exists="replace", index=False)
            df_payments_only_id.to_sql("test_payments_only_id", conn, if_exists="replace", index=False)
            df_payment_id_title.to_sql("test_payment_id_title", conn, if_exists="replace", index=False)
            df_paymentid_concat.to_sql("test_paymentid_concat", conn, if_exists="replace", index=False)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        with engine.begin() as conn:
            for tbl in ["test_payments_amount", "test_payments_only_id", "test_payment_id_title", "test_paymentid_concat"]:
                conn.execute(text(f"DROP TABLE IF EXISTS {tbl}"))

    def test_dynamic_identifier_detection(self):
        """Rule 1 & 2: Dynamic detection of various identifier formats vs monetary/quantity measures"""
        # Identifiers (must be True)
        self.assertTrue(is_identifier_column("payment_id"))
        self.assertTrue(is_identifier_column("Payment ID"))
        self.assertTrue(is_identifier_column("paymentid"))
        self.assertTrue(is_identifier_column("PaymentId"))
        self.assertTrue(is_identifier_column("PAYMENT_ID"))
        self.assertTrue(is_identifier_column("transaction_id"))
        self.assertTrue(is_identifier_column("trans_id"))
        self.assertTrue(is_identifier_column("order_id"))
        self.assertTrue(is_identifier_column("customer_id"))
        self.assertTrue(is_identifier_column("invoice_id"))
        self.assertTrue(is_identifier_column("invoice_no"))
        self.assertTrue(is_identifier_column("order_number"))
        self.assertTrue(is_identifier_column("uuid"))
        self.assertTrue(is_identifier_column("id"))
        self.assertTrue(is_identifier_column("id_payment"))

        # Measures and metrics (must be False)
        self.assertFalse(is_identifier_column("payment_amount"))
        self.assertFalse(is_identifier_column("paid_amount"))
        self.assertFalse(is_identifier_column("amount"))
        self.assertFalse(is_identifier_column("revenue"))
        self.assertFalse(is_identifier_column("total_revenue"))
        self.assertFalse(is_identifier_column("price"))
        self.assertFalse(is_identifier_column("quantity"))
        self.assertFalse(is_identifier_column("units"))
        self.assertFalse(is_identifier_column("salary"))
        self.assertFalse(is_identifier_column("spending_score"))
        self.assertFalse(is_identifier_column("payment_count"))
        self.assertFalse(is_identifier_column("number_of_payments"))
        self.assertFalse(is_identifier_column("total_payments"))

    def test_format_identifier_count_title(self):
        """Dashboard count labels must display 'Total Payments' instead of 'Total Payment ID' or 'Payment Id'"""
        self.assertEqual(format_identifier_count_title("payment_id"), "Total Payments")
        self.assertEqual(format_identifier_count_title("Payment ID"), "Total Payments")
        self.assertEqual(format_identifier_count_title("paymentid"), "Total Payments")
        self.assertEqual(format_identifier_count_title("PaymentId"), "Total Payments")
        self.assertEqual(format_identifier_count_title("order_id"), "Total Orders")
        self.assertEqual(format_identifier_count_title("transaction_id"), "Total Transactions")
        self.assertEqual(format_identifier_count_title("invoice_id"), "Total Invoices")
        self.assertEqual(format_identifier_count_title("customer_id"), "Total Customers")

    def test_schema_profiling_excludes_numeric_ids_from_numeric_columns(self):
        """Rule 1 & 2: Numeric-looking ID columns (1001, 1002, 1003) must be in id_columns, not numeric_columns"""
        schema = inspect_dataset_schema(self.db, "test_payments_amount")
        self.assertIn("payment_id", schema["id_columns"])
        self.assertNotIn("payment_id", schema["numeric_columns"])
        self.assertIn("payment_amount", schema["numeric_columns"])
        self.assertEqual(schema["primary_metric"], "payment_amount")

        schema_no_amount = inspect_dataset_schema(self.db, "test_payments_only_id")
        self.assertIn("payment_id", schema_no_amount["id_columns"])
        self.assertNotIn("payment_id", schema_no_amount["numeric_columns"])
        self.assertIsNone(schema_no_amount["primary_metric"])

    def test_analyze_result_set_excludes_ids_from_sum_and_mean(self):
        """Rule 3: analyze_result_set must exclude identifier columns from SUM/AVG calculation"""
        rows = [
            {"payment_id": 1001, "payment_amount": 250.50},
            {"payment_id": 1002, "payment_amount": 120.00},
            {"payment_id": 1003, "payment_amount": 430.75}
        ]
        columns = ["payment_id", "payment_amount"]
        summary = analyze_result_set(columns, rows)
        
        # payment_id must NOT be in numeric_summaries (never SUM-ed or averaged)
        self.assertNotIn("payment_id", summary["numeric_summaries"])
        # payment_amount MUST be in numeric_summaries with correct SUM
        self.assertIn("payment_amount", summary["numeric_summaries"])
        self.assertAlmostEqual(summary["numeric_summaries"]["payment_amount"]["sum"], 801.25)

    def test_dashboard_metrics_with_payment_amount(self):
        """
        For payment_id, payment_amount:
        - total payments count uses COUNT(payment_id) = 3
        - total revenue/amount uses SUM(payment_amount) = 801.25
        - average payment amount = 801.25 / 3 = 267.08
        - dashboard metric label says 'Total Payments', not 'Total Payment ID'
        """
        data = get_dashboard_data(self.db, table_name="test_payments_amount")
        metrics = data["metrics"]
        labels = metrics["metric_labels"]

        self.assertEqual(metrics["total_orders"], 3)
        self.assertAlmostEqual(metrics["total_revenue"], 801.25)
        self.assertAlmostEqual(metrics["average_order_value"], 267.08, places=2)

        # Labels verification
        self.assertEqual(labels["count_title"], "Total Payments")
        self.assertNotEqual(labels["count_title"], "Total Payment ID")
        self.assertNotEqual(labels["count_title"], "Payment Id")
        self.assertEqual(labels["primary_metric_title"], "Total Payment Amount")

    def test_dashboard_metrics_with_only_payment_ids_never_sums(self):
        """
        When dataset has ONLY payment_id (numeric 1001, 1002, 1003) and no monetary amount:
        - payment_id must NEVER be SUM-ed (summing 1001+1002+1003 = 3006 is WRONG)
        - total_orders must be COUNT = 3
        - total_revenue must be 0.0 (NOT 3006.0)
        - label says 'Total Payments'
        """
        data = get_dashboard_data(self.db, table_name="test_payments_only_id")
        metrics = data["metrics"]
        labels = metrics["metric_labels"]

        # MUST NOT BE 3006 (which would be 1001 + 1002 + 1003)
        self.assertNotEqual(metrics["total_revenue"], 3006.0)
        self.assertEqual(metrics["total_revenue"], 0.0)
        self.assertEqual(metrics["total_orders"], 3)
        self.assertEqual(labels["count_title"], "Total Payments")
        self.assertNotIn("Total Payment ID", labels["count_title"])

    def test_spaced_and_concatenated_payment_id_columns(self):
        """Verify 'Payment ID' and 'paymentid' are recognized and properly formatted"""
        cols_title = resolve_columns(self.db, "test_payment_id_title")
        self.assertEqual(cols_title["count_name"], "Total Payments")
        self.assertTrue(cols_title["has_real_revenue"])
        self.assertEqual(cols_title["raw_rev_col"], "Amount")

        cols_concat = resolve_columns(self.db, "test_paymentid_concat")
        self.assertEqual(cols_concat["count_name"], "Total Payments")
        self.assertTrue(cols_concat["has_real_revenue"])
        self.assertEqual(cols_concat["raw_rev_col"], "transacted_amount")

    def test_llm_sql_generation_prevents_sum_of_identifier(self):
        """Verify that generate_sql catches and converts disallowed SUM(payment_id) to COUNT(payment_id)"""
        from unittest.mock import patch

        cols = [
            {"name": "payment_id", "type": "INTEGER"},
            {"name": "payment_amount", "type": "DECIMAL(10,2)"},
            {"name": "payment_date", "type": "DATE"}
        ]

        # Simulate LLM erroneously outputting SUM(payment_id)
        with patch("backend.services.llm_service.call_llm") as mock_llm:
            mock_llm.side_effect = [
                "SELECT SUM(payment_id) FROM test_payments_amount;",
                "SELECT COUNT(payment_id) FROM test_payments_amount;"
            ]

            sql = generate_sql(
                question="What is the total number of payments?",
                table_name="test_payments_amount",
                columns=cols
            )

            self.assertIn("COUNT(payment_id)", sql)
            self.assertNotIn("SUM(payment_id)", sql)

        # Simulate LLM exhausting retries with SUM(payment_id), fallback should convert to COUNT(payment_id)
        with patch("backend.services.llm_service.call_llm") as mock_llm:
            mock_llm.return_value = "SELECT SUM(payment_id) FROM test_payments_amount;"

            sql = generate_sql(
                question="Total payments",
                table_name="test_payments_amount",
                columns=cols,
                max_retries=0
            )

            self.assertIn("COUNT(payment_id)", sql)
            self.assertNotIn("SUM(payment_id)", sql)

if __name__ == "__main__":
    unittest.main()


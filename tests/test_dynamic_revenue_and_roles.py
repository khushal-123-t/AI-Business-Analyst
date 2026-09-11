import unittest
import sys
import os
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database.connection import SessionLocal, engine
from backend.services.schema_service import (
    inspect_dataset_schema,
    classify_column_role,
    FinancialRole,
    is_identifier_column
)
from backend.services.analysis_service import (
    get_dashboard_data,
    resolve_columns,
    invalidate_dashboard_cache
)

class TestDynamicRevenueAndRoles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        # 1. Price + Quantity
        # 10 * 2 + 20 * 3 = 20 + 60 = 80
        df1 = pd.DataFrame([
            {"product_name": "A", "price": 10.0, "quantity": 2},
            {"product_name": "B", "price": 20.0, "quantity": 3},
        ])

        # 2. Price + Quantity + Discount Amount
        # (10 * 2 - 2) + (20 * 3 - 5) = 18 + 55 = 73
        df2 = pd.DataFrame([
            {"product_name": "A", "price": 10.0, "quantity": 2, "discount_amount": 2.0},
            {"product_name": "B", "price": 20.0, "quantity": 3, "discount_amount": 5.0},
        ])

        # 3. Price + Quantity + Discount Percent
        # (10 * 2 * 0.9) + (20 * 3 * 0.8) = 18 + 48 = 66
        df3 = pd.DataFrame([
            {"product_name": "A", "price": 10.0, "quantity": 2, "discount_percent": 10.0},
            {"product_name": "B", "price": 20.0, "quantity": 3, "discount_percent": 20.0},
        ])

        # 4. Price + Quantity + Tax (tax kept separate)
        # Revenue = 10 * 2 + 20 * 3 = 80. Tax = 4 + 6 = 10
        df4 = pd.DataFrame([
            {"product_name": "A", "price": 10.0, "quantity": 2, "tax_amount": 4.0},
            {"product_name": "B", "price": 20.0, "quantity": 3, "tax_amount": 6.0},
        ])

        # 5. Price + Quantity + Shipping Fee (shipping kept separate)
        # Revenue = 10 * 2 + 20 * 3 = 80. Shipping = 5 + 7 = 12
        df5 = pd.DataFrame([
            {"product_name": "A", "price": 10.0, "quantity": 2, "shipping_fee": 5.0},
            {"product_name": "B", "price": 20.0, "quantity": 3, "shipping_fee": 7.0},
        ])

        # 6. Price + Quantity + Refund
        # (10 * 2 - 5) + (20 * 3 - 10) = 15 + 50 = 65
        df6 = pd.DataFrame([
            {"product_name": "A", "price": 10.0, "quantity": 2, "refund_amount": 5.0},
            {"product_name": "B", "price": 20.0, "quantity": 3, "refund_amount": 10.0},
        ])

        # 7. Price + Quantity + Cost (cost separate, profit calculated)
        # Revenue = 80. Cost = 6*2 + 12*3 = 12 + 36 = 48. Profit = 80 - 48 = 32
        df7 = pd.DataFrame([
            {"product_name": "A", "unit_price": 10.0, "quantity": 2, "unit_cost": 6.0},
            {"product_name": "B", "unit_price": 20.0, "quantity": 3, "unit_cost": 12.0},
        ])

        # 8. Explicit Revenue
        # Revenue = 150 + 250 = 400
        df8 = pd.DataFrame([
            {"product_name": "A", "revenue": 150.0},
            {"product_name": "B", "revenue": 250.0},
        ])

        # 9. Explicit Net Revenue
        # Revenue = 140 + 230 = 370
        df9 = pd.DataFrame([
            {"product_name": "A", "gross_sales": 160.0, "net_revenue": 140.0},
            {"product_name": "B", "gross_sales": 250.0, "net_revenue": 230.0},
        ])

        # 10. Payment ID + Payment Amount
        # Revenue = 100.5 + 200.5 = 301.0, Payment ID = 2 orders/payments
        df10 = pd.DataFrame([
            {"payment_id": 9001, "payment_amount": 100.50},
            {"payment_id": 9002, "payment_amount": 200.50},
        ])

        # 11. Order ID + Price + Quantity
        # Revenue = 100 * 1 + 50 * 2 = 200.0, Total Orders = 2
        df11 = pd.DataFrame([
            {"order_id": 501, "price": 100.0, "quantity": 1},
            {"order_id": 502, "price": 50.0, "quantity": 2},
        ])

        # 12. Numeric Identifiers
        # Identifiers must NOT be summed
        df12 = pd.DataFrame([
            {"payment_id": 88888, "customer_id": 77777, "amount": 150.0},
            {"payment_id": 88889, "customer_id": 77778, "amount": 250.0},
        ])

        # 13. Currency-formatted Price ($ and commas)
        # $100.50 * 2 + $50.00 * 3 = 201.0 + 150.0 = 351.0
        df13 = pd.DataFrame([
            {"product_name": "A", "price": "$100.50", "quantity": 2},
            {"product_name": "B", "price": " $50.00 ", "quantity": 3},
        ])

        # 14. Price Without Quantity
        # Has NO real revenue, primary metric is Average Price
        df14 = pd.DataFrame([
            {"product_name": "Widget A", "unit_price": 40.0},
            {"product_name": "Widget B", "unit_price": 60.0},
        ])

        # 15. Quantity Without Price
        # Has NO real revenue, primary metric is Total Quantity
        df15 = pd.DataFrame([
            {"item": "Box A", "quantity": 15},
            {"item": "Box B", "quantity": 25},
        ])

        # 16. Revenue + Tax
        # Revenue = 300 + 400 = 700. Tax = 30 + 40 = 70 (kept separate)
        df16 = pd.DataFrame([
            {"category": "Tech", "revenue": 300.0, "tax": 30.0},
            {"category": "Books", "revenue": 400.0, "tax": 40.0},
        ])

        # 17. Revenue + Refund
        # Revenue = (300 - 20) + (400 - 50) = 280 + 350 = 630
        df17 = pd.DataFrame([
            {"category": "Tech", "revenue": 300.0, "refund": 20.0},
            {"category": "Books", "revenue": 400.0, "refund": 50.0},
        ])

        # 18. Price + Quantity + Explicit Total Amount
        # Explicit total_amount takes precedence over price * quantity (300 + 700 = 1000)
        df18 = pd.DataFrame([
            {"item": "X", "unit_price": 10.0, "quantity": 2, "total_amount": 300.0},
            {"item": "Y", "unit_price": 20.0, "quantity": 3, "total_amount": 700.0},
        ])

        with engine.begin() as conn:
            df1.to_sql("scen1_price_qty", conn, if_exists="replace", index=False)
            df2.to_sql("scen2_price_qty_disc_amt", conn, if_exists="replace", index=False)
            df3.to_sql("scen3_price_qty_disc_pct", conn, if_exists="replace", index=False)
            df4.to_sql("scen4_price_qty_tax", conn, if_exists="replace", index=False)
            df5.to_sql("scen5_price_qty_ship", conn, if_exists="replace", index=False)
            df6.to_sql("scen6_price_qty_refund", conn, if_exists="replace", index=False)
            df7.to_sql("scen7_price_qty_cost", conn, if_exists="replace", index=False)
            df8.to_sql("scen8_explicit_rev", conn, if_exists="replace", index=False)
            df9.to_sql("scen9_explicit_net_rev", conn, if_exists="replace", index=False)
            df10.to_sql("scen10_payment_id_amt", conn, if_exists="replace", index=False)
            df11.to_sql("scen11_order_id_price_qty", conn, if_exists="replace", index=False)
            df12.to_sql("scen12_numeric_ids", conn, if_exists="replace", index=False)
            df13.to_sql("scen13_currency_price", conn, if_exists="replace", index=False)
            df14.to_sql("scen14_price_no_qty", conn, if_exists="replace", index=False)
            df15.to_sql("scen15_qty_no_price", conn, if_exists="replace", index=False)
            df16.to_sql("scen16_rev_tax", conn, if_exists="replace", index=False)
            df17.to_sql("scen17_rev_refund", conn, if_exists="replace", index=False)
            df18.to_sql("scen18_price_qty_total_amt", conn, if_exists="replace", index=False)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        table_names = [
            f"scen{i}_{name}" for i, name in [
                (1, "price_qty"), (2, "price_qty_disc_amt"), (3, "price_qty_disc_pct"),
                (4, "price_qty_tax"), (5, "price_qty_ship"), (6, "price_qty_refund"),
                (7, "price_qty_cost"), (8, "explicit_rev"), (9, "explicit_net_rev"),
                (10, "payment_id_amt"), (11, "order_id_price_qty"), (12, "numeric_ids"),
                (13, "currency_price"), (14, "price_no_qty"), (15, "qty_no_price"),
                (16, "rev_tax"), (17, "rev_refund"), (18, "price_qty_total_amt")
            ]
        ]
        with engine.begin() as conn:
            for t in table_names:
                conn.execute(text(f"DROP TABLE IF EXISTS {t}"))

    def setUp(self):
        invalidate_dashboard_cache()

    # --- Role Classification Tests ---
    def test_role_classification(self):
        self.assertEqual(classify_column_role("payment_id"), FinancialRole.IDENTIFIER)
        self.assertEqual(classify_column_role("order_id"), FinancialRole.IDENTIFIER)
        self.assertEqual(classify_column_role("customer_id"), FinancialRole.IDENTIFIER)
        self.assertEqual(classify_column_role("quantity"), FinancialRole.QUANTITY)
        self.assertEqual(classify_column_role("units_sold"), FinancialRole.QUANTITY)
        self.assertEqual(classify_column_role("unit_price"), FinancialRole.UNIT_PRICE)
        self.assertEqual(classify_column_role("discount_amount"), FinancialRole.DISCOUNT_AMOUNT)
        self.assertEqual(classify_column_role("discount_percentage"), FinancialRole.DISCOUNT_PERCENT)
        self.assertEqual(classify_column_role("tax_amount"), FinancialRole.TAX_AMOUNT)
        self.assertEqual(classify_column_role("shipping_fee"), FinancialRole.SHIPPING_FEE)
        self.assertEqual(classify_column_role("refund_amount"), FinancialRole.REFUND)
        self.assertEqual(classify_column_role("cogs"), FinancialRole.COGS)
        self.assertEqual(classify_column_role("net_revenue"), FinancialRole.NET_REVENUE)
        self.assertEqual(classify_column_role("gross_sales"), FinancialRole.GROSS_REVENUE)
        self.assertEqual(classify_column_role("payment_amount"), FinancialRole.PAYMENT_AMOUNT)

    # --- 18 Revenue Scenarios Tests ---
    def test_scenario_01_price_and_quantity(self):
        # 10*2 + 20*3 = 80
        data = get_dashboard_data(self.db, "scen1_price_qty")
        self.assertEqual(data["metrics"]["total_revenue"], 80.0)
        self.assertEqual(data["metrics"]["metric_labels"]["primary_metric_title"], "Total Revenue")

    def test_scenario_02_price_quantity_discount_amount(self):
        # (10*2 - 2) + (20*3 - 5) = 73
        data = get_dashboard_data(self.db, "scen2_price_qty_disc_amt")
        self.assertEqual(data["metrics"]["total_revenue"], 73.0)
        self.assertEqual(data["metrics"]["gross_sales"], 80.0)
        self.assertEqual(data["metrics"]["total_discounts"], 7.0)

    def test_scenario_03_price_quantity_discount_percent(self):
        # 10*2*0.9 + 20*3*0.8 = 18 + 48 = 66
        data = get_dashboard_data(self.db, "scen3_price_qty_disc_pct")
        self.assertEqual(data["metrics"]["total_revenue"], 66.0)
        self.assertEqual(data["metrics"]["gross_sales"], 80.0)
        self.assertEqual(data["metrics"]["total_discounts"], 14.0)

    def test_scenario_04_price_quantity_tax(self):
        # Revenue = 80, Tax = 10 (separate, not added into revenue)
        data = get_dashboard_data(self.db, "scen4_price_qty_tax")
        self.assertEqual(data["metrics"]["total_revenue"], 80.0)
        self.assertEqual(data["metrics"]["total_tax"], 10.0)

    def test_scenario_05_price_quantity_shipping(self):
        # Revenue = 80, Shipping = 12 (separate, not added into revenue)
        data = get_dashboard_data(self.db, "scen5_price_qty_ship")
        self.assertEqual(data["metrics"]["total_revenue"], 80.0)
        self.assertEqual(data["metrics"]["total_shipping"], 12.0)

    def test_scenario_06_price_quantity_refund(self):
        # (10*2 - 5) + (20*3 - 10) = 65
        data = get_dashboard_data(self.db, "scen6_price_qty_refund")
        self.assertEqual(data["metrics"]["total_revenue"], 65.0)
        self.assertEqual(data["metrics"]["gross_sales"], 80.0)

    def test_scenario_07_price_quantity_cost(self):
        # Revenue = 80, Cost = 48, Profit = 32
        data = get_dashboard_data(self.db, "scen7_price_qty_cost")
        self.assertEqual(data["metrics"]["total_revenue"], 80.0)
        self.assertEqual(data["metrics"]["total_cost"], 48.0)
        self.assertEqual(data["metrics"]["total_profit"], 32.0)
        self.assertEqual(data["metrics"]["profit_margin"], 40.0)

    def test_scenario_08_explicit_revenue(self):
        # Revenue = 150 + 250 = 400
        data = get_dashboard_data(self.db, "scen8_explicit_rev")
        self.assertEqual(data["metrics"]["total_revenue"], 400.0)

    def test_scenario_09_explicit_net_revenue(self):
        # Net revenue = 140 + 230 = 370
        data = get_dashboard_data(self.db, "scen9_explicit_net_rev")
        self.assertEqual(data["metrics"]["total_revenue"], 370.0)

    def test_scenario_10_payment_id_and_payment_amount(self):
        # Revenue = 301.0, Total Orders/Payments = 2
        data = get_dashboard_data(self.db, "scen10_payment_id_amt")
        self.assertEqual(data["metrics"]["total_revenue"], 301.0)
        self.assertEqual(data["metrics"]["total_orders"], 2)
        self.assertEqual(data["metrics"]["metric_labels"]["count_title"], "Total Payments")

    def test_scenario_11_order_id_price_quantity(self):
        # Revenue = 100*1 + 50*2 = 200.0, Orders = 2
        data = get_dashboard_data(self.db, "scen11_order_id_price_qty")
        self.assertEqual(data["metrics"]["total_revenue"], 200.0)
        self.assertEqual(data["metrics"]["total_orders"], 2)
        self.assertEqual(data["metrics"]["metric_labels"]["count_title"], "Total Orders")

    def test_scenario_12_numeric_identifiers_never_summed(self):
        # Amount = 150 + 250 = 400, NOT payment_id (88888 + 88889)
        data = get_dashboard_data(self.db, "scen12_numeric_ids")
        self.assertEqual(data["metrics"]["total_revenue"], 400.0)
        self.assertEqual(data["metrics"]["total_orders"], 2)
        cols = resolve_columns(self.db, "scen12_numeric_ids")
        self.assertNotIn("payment_id", cols["revenue"])
        self.assertNotIn("customer_id", cols["revenue"])

    def test_scenario_13_currency_formatted_price(self):
        # $100.50 * 2 + $50.00 * 3 = 351.0
        data = get_dashboard_data(self.db, "scen13_currency_price")
        self.assertEqual(data["metrics"]["total_revenue"], 351.0)

    def test_scenario_14_price_without_quantity(self):
        # Price alone is NOT revenue. Primary metric is Average Price.
        data = get_dashboard_data(self.db, "scen14_price_no_qty")
        self.assertEqual(data["metrics"]["total_revenue"], 0.0)
        self.assertEqual(data["metrics"]["average_price"], 50.0)
        self.assertEqual(data["metrics"]["metric_labels"]["primary_metric_title"], "Average Price")

    def test_scenario_15_quantity_without_price(self):
        # Quantity alone is NOT revenue. Primary metric is Total Quantity.
        data = get_dashboard_data(self.db, "scen15_qty_no_price")
        self.assertEqual(data["metrics"]["total_revenue"], 0.0)
        self.assertEqual(data["metrics"]["total_quantity"], 40.0)
        self.assertEqual(data["metrics"]["metric_labels"]["primary_metric_title"], "Total Quantity")

    def test_scenario_16_revenue_and_tax(self):
        # Revenue = 700. Tax = 70 (kept separate, not added to revenue)
        data = get_dashboard_data(self.db, "scen16_rev_tax")
        self.assertEqual(data["metrics"]["total_revenue"], 700.0)
        self.assertEqual(data["metrics"]["total_tax"], 70.0)

    def test_scenario_17_revenue_and_refund(self):
        # Revenue = (300 - 20) + (400 - 50) = 630
        data = get_dashboard_data(self.db, "scen17_rev_refund")
        self.assertEqual(data["metrics"]["total_revenue"], 630.0)

    def test_scenario_18_price_quantity_and_explicit_total_amount(self):
        # Authoritative total_amount takes precedence: 300 + 700 = 1000.0
        data = get_dashboard_data(self.db, "scen18_price_qty_total_amt")
        self.assertEqual(data["metrics"]["total_revenue"], 1000.0)

if __name__ == "__main__":
    unittest.main()

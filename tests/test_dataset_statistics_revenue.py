import sys
import unittest
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

from backend.database.connection import SessionLocal
from backend.services.analysis_service import resolve_columns, get_dashboard_data, invalidate_dashboard_cache
from backend.main import clean_dataframe_numeric_columns
import pandas as pd

class TestDatasetStatisticsRevenue(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        invalidate_dashboard_cache()

    def tearDown(self):
        self.db.close()

    def test_dataset_15_statistics_metrics(self):
        """Verify that Dataset statistics (table dataset_client_4_5d7455351831) fetches accurate revenue and metrics."""
        table_name = 'dataset_client_4_5d7455351831'
        cols = resolve_columns(self.db, table_name)
        self.assertTrue(cols["profit_available"])
        self.assertEqual(cols["profit_source"], "column")

        dashboard = get_dashboard_data(self.db, table_name=table_name)
        m = dashboard["metrics"]
        
        print("\n[TEST] Dataset Statistics Metrics:")
        print(f"  Revenue: {m['total_revenue']}")
        print(f"  Profit: {m['total_profit']}")
        print(f"  Orders: {m['total_orders']}")
        print(f"  Customers: {m['total_customers']}")
        print(f"  AOV: {m['average_order_value']}")

        # Revenue was $177,134,263.74
        self.assertAlmostEqual(m['total_revenue'], 177134263.74, places=2)
        # Profit was $76,146,395.76
        self.assertAlmostEqual(m['total_profit'], 76146395.76, places=2)
        # Orders was 138,116
        self.assertEqual(m['total_orders'], 138116)
        # Customers was 24,911
        self.assertEqual(m['total_customers'], 24911)
        # AOV was 1,282.50
        self.assertAlmostEqual(m['average_order_value'], 1282.50, places=2)

    def test_dataset_9_amazon_numeric_cleaning(self):
        """Verify that Amazon table with ₹ and prices but NO quantity has Revenue=0 (Price alone is not revenue) and computes average_price."""
        table_name = 'dataset_client_4_9e9265977413'
        dashboard = get_dashboard_data(self.db, table_name=table_name)
        m = dashboard["metrics"]

        print("\n[TEST] Amazon Metrics:")
        print(f"  Revenue: {m['total_revenue']}")
        print(f"  Average Price: {m['average_price']}")
        print(f"  Profit: {m['total_profit']}")
        print(f"  Orders: {m['total_orders']}")

        # Under strict revenue logic, price alone without quantity is NOT revenue -> Revenue = 0.0
        self.assertEqual(m['total_revenue'], 0.0)
        self.assertAlmostEqual(m['average_price'], 3125.99, places=2)
        # Profit must be None since no profit column exists
        self.assertIsNone(m['total_profit'])
        self.assertFalse(m['profit_available'])

    def test_clean_dataframe_numeric_columns_unit(self):
        """Unit test for clean_dataframe_numeric_columns with various currencies and formats."""
        raw_df = pd.DataFrame({
            "title": ["Item A", "Item B", "Item C"],
            "price_usd": ["$1,250.50", "$300.00", "$49.99"],
            "price_inr": ["₹1,099", "₹199", "1399"],
            "price_eur": ["€ 1.200,50" if False else "€1200.50", "€350.00", "€25.00"],
            "margin_pct": ["15%", "25.5%", "18%"],
            "date_range": ["2021-01-01 to 2025-12-31", "2021-01-01 to 2025-12-31", "2021-01-01 to 2025-12-31"]
        })

        cleaned = clean_dataframe_numeric_columns(raw_df)

        import numpy as np
        self.assertTrue(np.issubdtype(cleaned["price_usd"].dtype, np.number))
        self.assertAlmostEqual(cleaned["price_usd"].sum(), 1600.49, places=2)

        self.assertTrue(np.issubdtype(cleaned["price_inr"].dtype, np.number))
        self.assertAlmostEqual(cleaned["price_inr"].sum(), 2697.0, places=2)

        self.assertTrue(np.issubdtype(cleaned["margin_pct"].dtype, np.number))
        self.assertAlmostEqual(cleaned["margin_pct"].iloc[0], 15.0)

        # Date range should remain string
        self.assertTrue("str" in str(cleaned["date_range"].dtype) or cleaned["date_range"].dtype == "object")

if __name__ == "__main__":
    unittest.main()

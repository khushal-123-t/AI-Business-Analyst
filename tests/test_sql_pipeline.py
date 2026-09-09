import sys
import unittest
import os

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

from fastapi.testclient import TestClient
from backend.main import app
from backend.services.llm_service import generate_sql, generate_insights, clean_generated_sql
from backend.services.sql_service import execute_query
from backend.database.connection import SessionLocal
from backend.utils.auth import create_access_token

class TestSQLPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Client 4 token
        cls.token = create_access_token(data={"sub": "khushalsharma1260@gmail.com", "role": "CLIENT"})
        cls.headers = {"Authorization": f"Bearer {cls.token}"}
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_trends_amazon_sales_dataset(self):
        """Test 'What trends do you see in my data?' on Amazon sales dataset."""
        print("\n--- TEST 01: 'What trends do you see in my data?' on Amazon sales dataset ---")
        # Dataset 10 is 'Amazon sales dataset' (table: dataset_client_4_f6017eece021)
        response = self.client.post(
            "/api/ask?dataset_id=10",
            headers=self.headers,
            json={"question": "What trends do you see in my data?", "session_id": "test_session_trends"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        print("Success:", data.get("success"))
        print("Generated SQL:", data.get("sql"))
        print("Summary:", data.get("summary")[:120] if data.get("summary") else None)
        print("Columns:", data.get("columns"))
        print("Row count:", len(data.get("rows", [])))
        print("Error:", data.get("error"))

        self.assertTrue(data.get("success"), f"Query failed with error: {data.get('error')}")
        self.assertIsNotNone(data.get("sql"))
        self.assertTrue(len(data.get("sql")) > 0)
        self.assertTrue(data["sql"].upper().startswith(("SELECT", "WITH")))
        self.assertTrue(len(data.get("rows", [])) > 0)
        self.assertIsNotNone(data.get("summary"))
        self.assertNotIn("Sorry, I could not generate a valid SQL query", data.get("summary"))

    def test_02_total_sales_amazon_sales_dataset(self):
        """Test 'What is the total sales?' on Amazon sales dataset."""
        print("\n--- TEST 02: 'What is the total sales?' ---")
        response = self.client.post(
            "/api/ask?dataset_id=10",
            headers=self.headers,
            json={"question": "What is the total sales?", "session_id": "test_session_sales"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        print("Generated SQL:", data.get("sql"))
        print("Summary:", data.get("summary")[:100] if data.get("summary") else None)
        self.assertTrue(data.get("success"))
        self.assertTrue(len(data.get("rows", [])) > 0)

    def test_03_highest_sales_product(self):
        """Test 'Which product has the highest sales?' on Amazon sales dataset."""
        print("\n--- TEST 03: 'Which product has the highest sales?' ---")
        response = self.client.post(
            "/api/ask?dataset_id=10",
            headers=self.headers,
            json={"question": "Which product has the highest sales?", "session_id": "test_session_product"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        print("Generated SQL:", data.get("sql"))
        self.assertTrue(data.get("success"))
        self.assertTrue(len(data.get("rows", [])) > 0)

    def test_04_sales_by_category(self):
        """Test 'Show sales by category.' on Amazon sales dataset."""
        print("\n--- TEST 04: 'Show sales by category.' ---")
        response = self.client.post(
            "/api/ask?dataset_id=10",
            headers=self.headers,
            json={"question": "Show sales by category.", "session_id": "test_session_cat"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        print("Generated SQL:", data.get("sql"))
        self.assertTrue(data.get("success"))
        self.assertTrue(len(data.get("rows", [])) > 0)

    def test_05_profit_integrity_no_margin(self):
        """Test 'What is my profit?' on a dataset without profit column - must NOT assume 18%."""
        print("\n--- TEST 05: 'What is my profit?' without profit column ---")
        response = self.client.post(
            "/api/ask?dataset_id=10",
            headers=self.headers,
            json={"question": "What is my profit?", "session_id": "test_session_profit"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        print("Summary:", data.get("summary"))
        print("Key findings:", data.get("key_findings"))
        self.assertTrue(data.get("success"))
        # Must clearly state profit cannot be calculated / unavailable
        self.assertIn("profit", data.get("summary", "").lower())
        # Must not generate SQL assuming 0.18
        self.assertEqual(data.get("sql"), "")

    def test_06_profit_with_explicit_margin(self):
        """Test 'What is my estimated profit with a 20% margin?'."""
        print("\n--- TEST 06: 'What is my estimated profit with a 20% margin?' ---")
        response = self.client.post(
            "/api/ask?dataset_id=10",
            headers=self.headers,
            json={"question": "What is my estimated profit with a 20% margin?", "session_id": "test_session_exp_profit"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        print("Generated SQL:", data.get("sql"))
        self.assertTrue(data.get("success"))
        self.assertTrue(len(data.get("rows", [])) > 0)
        self.assertIn("0.2", data.get("sql"))

    def test_07_different_dataset_statistics(self):
        """Test query on Dataset 15 ('Dataset statistics')."""
        print("\n--- TEST 07: Query on Dataset 15 ('Dataset statistics') ---")
        response = self.client.post(
            "/api/ask?dataset_id=15",
            headers=self.headers,
            json={"question": "What is the total revenue and profit?", "session_id": "test_session_ds15"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        print("Generated SQL:", data.get("sql"))
        print("Summary:", data.get("summary")[:100] if data.get("summary") else None)
        self.assertTrue(data.get("success"))
        self.assertTrue(len(data.get("rows", [])) > 0)

if __name__ == "__main__":
    unittest.main()

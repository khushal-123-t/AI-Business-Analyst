import sys
import unittest
import time
import io

sys.path.insert(0, '.')

from fastapi.testclient import TestClient
from backend.main import app
from backend.database.connection import SessionLocal
from backend.models.orm_models import Dataset
from backend.utils.auth import create_access_token
from tests.test_upload_benchmark import generate_benchmark_csv
from sqlalchemy import text

class TestAPIUploadPerformance(unittest.TestCase):
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

    def test_upload_15mb_dataset_performance(self):
        """Test uploading a 15 MB dataset via HTTP POST /client/datasets."""
        print("\n--- Testing API Upload: 15 MB CSV via POST /client/datasets ---")
        csv_bytes = generate_benchmark_csv(size_mb=15.0)
        
        t0 = time.perf_counter()
        files = {"file": ("test_perf_15mb.csv", io.BytesIO(csv_bytes), "text/csv")}
        data = {"name": "Performance Test 15MB Dataset"}
        
        response = self.client.post(
            "/client/datasets",
            headers=self.headers,
            data=data,
            files=files
        )
        t_total = time.perf_counter() - t0
        print(f"HTTP Status: {response.status_code}")
        print(f"Total HTTP Round-trip: {t_total:.3f}s")
        
        self.assertEqual(response.status_code, 200)
        ds = response.json()
        print("Dataset returned:", ds)
        self.assertIn("id", ds)
        self.assertEqual(ds["name"], "Performance Test 15MB Dataset")
        self.assertGreater(ds["row_count"], 100000)
        
        # Clean up created table
        table_name = ds["table_name"]
        with self.db.bind.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS `{table_name}`"))
        self.db.query(Dataset).filter(Dataset.id == ds["id"]).delete()
        self.db.commit()
        print(f"[OK] 15 MB dataset uploaded and registered in {t_total:.3f}s!")

if __name__ == "__main__":
    unittest.main()

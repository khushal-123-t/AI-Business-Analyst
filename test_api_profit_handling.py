import os
import sys

# Add parent directory to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from fastapi.testclient import TestClient
from backend.main import app
from backend.models.orm_models import User
from backend.utils.auth import create_access_token

client = TestClient(app)

def test_api_profit():
    print("=== TESTING API PROFIT INTEGRITY ===")

    # Create admin token for test
    token = create_access_token({"sub": "admin@example.com", "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Admin querying global sales table (which HAS profit column)
    res_a = client.post("/api/ask", json={"question": "What is our total profit?"}, headers=headers)
    assert res_a.status_code == 200
    data_a = res_a.json()
    print("Test A data:", data_a)

    # 2. Client 3 querying netflix dataset (id=5) which has NO profit or margin columns
    token_client3 = create_access_token({"sub": "omega@example.com", "role": "CLIENT"})
    headers_c3 = {"Authorization": f"Bearer {token_client3}"}
    res_c = client.post("/api/ask?dataset_id=5", json={"question": "What is our total profit?"}, headers=headers_c3)
    assert res_c.status_code == 200
    data_c = res_c.json()
    print("Test C (Dataset without Profit):", data_c)
    assert data_c["success"] == True
    assert "Profit data cannot be calculated from the available dataset" in data_c["summary"]
    assert "Default profit margins (such as 18%) are strictly disabled" in data_c["key_findings"][1]
    print("[OK] Test C passed: Intercepted profit query and cleanly rejected default margin")

    print("\n=== API PROFIT INTEGRITY VERIFIED! ===")

if __name__ == "__main__":
    test_api_profit()

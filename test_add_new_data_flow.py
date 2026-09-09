import os
import sys
import io
import json
import pandas as pd
from fastapi.testclient import TestClient

# Add parent directory to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.main import app
from backend.utils.auth import create_access_token
from backend.database.connection import engine
from sqlalchemy import text

client = TestClient(app)

def test_add_new_data_flow():
    print("=== TESTING COMPLETE ADD NEW DATA FLOW ===")

    # Client 1 auth token
    token_c1 = create_access_token({"sub": "client1@example.com", "role": "CLIENT"})
    headers_c1 = {"Authorization": f"Bearer {token_c1}"}

    # Client 2 auth token (for tenant isolation check)
    token_c2 = create_access_token({"sub": "client2@example.com", "role": "CLIENT"})
    headers_c2 = {"Authorization": f"Bearer {token_c2}"}

    # Clean up any leftover test datasets from previous runs
    existing = client.get("/client/datasets", headers=headers_c1).json()
    for d in existing:
        if d["name"].startswith("Test ") or d["name"].startswith("New Employees") or d["name"].startswith("Inventory Excel") or d["name"].startswith("User Sessions"):
            client.delete(f"/client/datasets/{d['id']}", headers=headers_c1)

    # ----------------------------------------------------
    # TEST A: Upload an existing/standard CSV file
    # ----------------------------------------------------
    print("\n--- TEST A: Upload standard CSV file ---")
    csv_data = "order_id,product,category,revenue\n1,Widget A,Hardware,150.0\n2,Widget B,Hardware,250.0\n"
    res_a = client.post(
        "/client/datasets",
        data={"name": "Test CSV Dataset"},
        files={"file": ("test_sales.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")},
        headers=headers_c1
    )
    assert res_a.status_code == 200, f"Upload failed: {res_a.text}"
    ds_a = res_a.json()
    assert ds_a["name"] == "Test CSV Dataset"
    assert ds_a["row_count"] == 2
    assert ds_a["col_count"] == 4
    print("[OK] Test A passed: Standard CSV uploaded successfully (ID:", ds_a["id"], ")")

    # ----------------------------------------------------
    # TEST B: Newly created/downloaded CSV file
    # ----------------------------------------------------
    print("\n--- TEST B: Newly created CSV file ---")
    new_csv = "emp_id,emp_name,department,salary\n101,John Doe,Engineering,85000\n102,Jane Smith,Marketing,78000\n103,Bob Lee,Design,72000\n"
    res_b = client.post(
        "/client/datasets",
        data={"name": "New Employees Data"},
        files={"file": ("new_downloaded_employees.csv", io.BytesIO(new_csv.encode("utf-8")), "text/csv")},
        headers=headers_c1
    )
    assert res_b.status_code == 200, f"Upload failed: {res_b.text}"
    ds_b = res_b.json()
    assert ds_b["name"] == "New Employees Data"
    assert ds_b["row_count"] == 3
    print("[OK] Test B passed: Newly created CSV uploaded immediately (ID:", ds_b["id"], ")")

    # ----------------------------------------------------
    # TEST C: Upload XLSX file
    # ----------------------------------------------------
    print("\n--- TEST C: Upload Excel (XLSX) file ---")
    excel_buffer = io.BytesIO()
    df_excel = pd.DataFrame({
        "item_code": ["ITM01", "ITM02"],
        "stock": [45, 120],
        "warehouse": ["North", "South"]
    })
    df_excel.to_excel(excel_buffer, index=False, engine="openpyxl")
    excel_buffer.seek(0)
    res_c = client.post(
        "/client/datasets",
        data={"name": "Inventory Excel"},
        files={"file": ("inventory.xlsx", excel_buffer, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=headers_c1
    )
    assert res_c.status_code == 200, f"Upload failed: {res_c.text}"
    ds_c = res_c.json()
    assert ds_c["row_count"] == 2
    assert ds_c["col_count"] == 3
    print("[OK] Test C passed: Excel XLSX uploaded successfully (ID:", ds_c["id"], ")")

    # ----------------------------------------------------
    # TEST D: Upload JSON file
    # ----------------------------------------------------
    print("\n--- TEST D: Upload JSON file ---")
    json_data = json.dumps([
        {"user_id": "U1", "action": "login", "duration_sec": 120},
        {"user_id": "U2", "action": "search", "duration_sec": 45},
        {"user_id": "U3", "action": "checkout", "duration_sec": 300}
    ])
    res_d = client.post(
        "/client/datasets",
        data={"name": "User Sessions JSON"},
        files={"file": ("sessions.json", io.BytesIO(json_data.encode("utf-8")), "application/json")},
        headers=headers_c1
    )
    assert res_d.status_code == 200, f"Upload failed: {res_d.text}"
    ds_d = res_d.json()
    assert ds_d["row_count"] == 3
    assert ds_d["col_count"] == 3
    print("[OK] Test D passed: JSON dataset uploaded successfully (ID:", ds_d["id"], ")")

    # ----------------------------------------------------
    # TEST E: Upload consecutive files with duplicate names
    # ----------------------------------------------------
    print("\n--- TEST E: Duplicate dataset name handling ---")
    res_e = client.post(
        "/client/datasets",
        data={"name": "Test CSV Dataset"},  # Same name as Test A
        files={"file": ("test_sales.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")},
        headers=headers_c1
    )
    assert res_e.status_code == 200
    ds_e = res_e.json()
    assert ds_e["name"] == "Test CSV Dataset (1)"
    assert ds_e["id"] != ds_a["id"]
    print("[OK] Test E passed: Duplicate name safely auto-versioned as:", ds_e["name"])

    # ----------------------------------------------------
    # TEST F: Empty file validation
    # ----------------------------------------------------
    print("\n--- TEST F: Empty file validation ---")
    res_f = client.post(
        "/client/datasets",
        data={"name": "Empty Dataset"},
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
        headers=headers_c1
    )
    assert res_f.status_code == 400
    print("[OK] Test F passed: Empty file cleanly rejected with 400:", res_f.json()["detail"])

    # ----------------------------------------------------
    # TEST G: Unsupported file format validation
    # ----------------------------------------------------
    print("\n--- TEST G: Unsupported file format validation ---")
    res_g = client.post(
        "/client/datasets",
        data={"name": "Bad File"},
        files={"file": ("script.exe", io.BytesIO(b"binary data"), "application/octet-stream")},
        headers=headers_c1
    )
    assert res_g.status_code == 400
    print("[OK] Test G passed: Unsupported file cleanly rejected with 400:", res_g.json()["detail"])

    # ----------------------------------------------------
    # TEST H: Fetch dataset list & verify immediate presence & no-cache headers
    # ----------------------------------------------------
    print("\n--- TEST H: Dataset list retrieval and freshness ---")
    list_res = client.get("/client/datasets", headers=headers_c1)
    assert list_res.status_code == 200
    assert "no-cache" in list_res.headers.get("Cache-Control", "")
    client1_datasets = list_res.json()
    client1_ids = [d["id"] for d in client1_datasets]
    assert ds_a["id"] in client1_ids
    assert ds_b["id"] in client1_ids
    assert ds_c["id"] in client1_ids
    assert ds_d["id"] in client1_ids
    assert ds_e["id"] in client1_ids
    print("[OK] Test H passed: All newly uploaded datasets present in dataset list with no-cache headers")

    # ----------------------------------------------------
    # TEST I: Tenant Data Isolation
    # ----------------------------------------------------
    print("\n--- TEST I: Tenant data isolation ---")
    list_res_c2 = client.get("/client/datasets", headers=headers_c2)
    assert list_res_c2.status_code == 200
    client2_datasets = list_res_c2.json()
    client2_ids = [d["id"] for d in client2_datasets]
    for uploaded_id in [ds_a["id"], ds_b["id"], ds_c["id"], ds_d["id"], ds_e["id"]]:
        assert uploaded_id not in client2_ids, f"Data isolation breach: Dataset {uploaded_id} visible to Client 2!"
    print("[OK] Test I passed: Client 1 datasets are strictly isolated and invisible to Client 2")

    # ----------------------------------------------------
    # TEST J: Analytical Dashboard & KPI Availability
    # ----------------------------------------------------
    print("\n--- TEST J: Analytical queries on newly uploaded dataset ---")
    dash_res = client.get(f"/client/dashboard?dataset_id={ds_a['id']}", headers=headers_c1)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["metrics"]["total_revenue"] == 400.0  # 150 + 250
    assert dash_data["metrics"]["total_orders"] == 2
    print("[OK] Test J passed: Newly uploaded dataset immediately powers dashboard KPIs (Revenue: $400.0)")

    # Cleanup test datasets and tables
    for d in [ds_a, ds_b, ds_c, ds_d, ds_e]:
        client.delete(f"/client/datasets/{d['id']}", headers=headers_c1)

    print("\n=== ALL ADD NEW DATA FLOW TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    test_add_new_data_flow()

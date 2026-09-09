import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text

# Add parent directory to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.services.analysis_service import resolve_columns, get_dashboard_data
from backend.services.llm_service import extract_explicit_margin, generate_sql
from backend.database.connection import engine

def test_cases():
    print("=== STARTING PROFIT LOGIC VERIFICATION ===")
    
    with engine.connect() as conn:
        # ----------------------------------------------------
        # CASE A: Dataset with actual 'profit' column
        # ----------------------------------------------------
        print("\n--- CASE A: Dataset with actual profit column ---")
        conn.execute(text("DROP TABLE IF EXISTS test_case_a"))
        conn.execute(text("""
            CREATE TABLE test_case_a (
                order_id INT, customer_name TEXT, category TEXT, region TEXT, order_date TEXT,
                revenue FLOAT, profit FLOAT
            )
        """))
        conn.execute(text("""
            INSERT INTO test_case_a VALUES
            (1, 'Alice', 'Tech', 'North', '2026-01-01', 1000.0, 350.0),
            (2, 'Bob', 'Tech', 'South', '2026-01-02', 2000.0, 500.0),
            (3, 'Charlie', 'Office', 'East', '2026-01-03', 500.0, 100.0)
        """))
        conn.commit()

        mapping_a = resolve_columns(conn, "test_case_a")
        assert mapping_a["profit_available"] == True, "Case A profit should be available"
        assert mapping_a["profit_source"] == "column", f"Case A source should be column, got {mapping_a['profit_source']}"
        assert mapping_a["profit"] == "`profit`", f"Case A mapped column should be `profit`, got {mapping_a['profit']}"

        dash_a = get_dashboard_data(conn, "test_case_a")
        assert dash_a["metrics"]["total_profit"] == 950.0, f"Expected 950.0, got {dash_a['metrics']['total_profit']}"
        assert dash_a["metrics"]["profit_available"] == True
        assert len(dash_a["profit_by_category"]) > 0
        print("[OK] Case A passed: Uses actual profit values directly (total_profit = 950.0)")

        # ----------------------------------------------------
        # CASE B: Dataset with 'profit_margin' column
        # ----------------------------------------------------
        print("\n--- CASE B: Dataset with margin column ---")
        conn.execute(text("DROP TABLE IF EXISTS test_case_b"))
        conn.execute(text("""
            CREATE TABLE test_case_b (
                order_id INT, customer_name TEXT, category TEXT, region TEXT, order_date TEXT,
                revenue FLOAT, profit_margin FLOAT
            )
        """))
        conn.execute(text("""
            INSERT INTO test_case_b VALUES
            (1, 'Alice', 'Tech', 'North', '2026-01-01', 1000.0, 0.25),
            (2, 'Bob', 'Tech', 'South', '2026-01-02', 2000.0, 20.0),
            (3, 'Charlie', 'Office', 'East', '2026-01-03', 500.0, 10.0)
        """))
        conn.commit()

        mapping_b = resolve_columns(conn, "test_case_b")
        assert mapping_b["profit_available"] == True, "Case B profit should be available"
        assert mapping_b["profit_source"] == "margin_column", f"Case B source should be margin_column, got {mapping_b['profit_source']}"
        
        dash_b = get_dashboard_data(conn, "test_case_b")
        # 1000*0.25=250, 2000*(20/100)=400, 500*(10/100)=50 -> Total = 700.0
        assert dash_b["metrics"]["total_profit"] == 700.0, f"Expected 700.0, got {dash_b['metrics']['total_profit']}"
        assert dash_b["metrics"]["profit_available"] == True
        print("[OK] Case B passed: Accurately calculates profit from margin column (total_profit = 700.0)")

        # ----------------------------------------------------
        # CASE C: Dataset with NEITHER profit NOR margin
        # ----------------------------------------------------
        print("\n--- CASE C: Dataset with neither profit nor margin ---")
        conn.execute(text("DROP TABLE IF EXISTS test_case_c"))
        conn.execute(text("""
            CREATE TABLE test_case_c (
                order_id INT, customer_name TEXT, category TEXT, region TEXT, order_date TEXT,
                revenue FLOAT
            )
        """))
        conn.execute(text("""
            INSERT INTO test_case_c VALUES
            (1, 'Alice', 'Tech', 'North', '2026-01-01', 1000.0),
            (2, 'Bob', 'Tech', 'South', '2026-01-02', 2000.0)
        """))
        conn.commit()

        mapping_c = resolve_columns(conn, "test_case_c")
        assert mapping_c["profit_available"] == False, "Case C profit MUST NOT be available"
        assert mapping_c["profit"] is None, "Case C profit column mapping MUST be None"
        
        dash_c = get_dashboard_data(conn, "test_case_c")
        assert dash_c["metrics"]["total_profit"] is None, f"Expected None, got {dash_c['metrics']['total_profit']}"
        assert dash_c["metrics"]["profit_available"] == False
        assert dash_c["profit_by_category"] == []
        print("[OK] Case C passed: Profit is strictly None/unavailable, no 18% assumption made")

        # ----------------------------------------------------
        # CASE D: User explicitly provides a margin in prompt
        # ----------------------------------------------------
        print("\n--- CASE D: Explicit user-provided margin ---")
        prompt_1 = "Assume a 15% profit margin, what is our profit?"
        margin_1 = extract_explicit_margin(prompt_1)
        assert margin_1 == 15.0, f"Expected 15.0, got {margin_1}"

        prompt_2 = "Calculate profit with 22.5% margin"
        margin_2 = extract_explicit_margin(prompt_2)
        assert margin_2 == 22.5, f"Expected 22.5, got {margin_2}"

        prompt_3 = "Show me the top products by sales"
        margin_3 = extract_explicit_margin(prompt_3)
        assert margin_3 is None, f"Expected None, got {margin_3}"

        mapping_d = resolve_columns(conn, "test_case_c", user_margin=15.0)
        assert mapping_d["profit_available"] == True
        assert mapping_d["profit_source"] == "user_margin"
        dash_d = get_dashboard_data(conn, "test_case_c", user_margin=15.0)
        # Revenue = 3000.0 * 0.15 = 450.0
        assert dash_d["metrics"]["total_profit"] == 450.0, f"Expected 450.0, got {dash_d['metrics']['total_profit']}"
        print("[OK] Case D passed: Explicit margin extracted and estimated profit calculated (450.0)")

        # ----------------------------------------------------
        # CASE E: Dataset with revenue and cost but no profit column
        # ----------------------------------------------------
        print("\n--- CASE E: Dataset with revenue and cost, no profit column ---")
        conn.execute(text("DROP TABLE IF EXISTS test_case_e"))
        conn.execute(text("""
            CREATE TABLE test_case_e (
                order_id INT, customer_name TEXT, category TEXT, region TEXT, order_date TEXT,
                revenue FLOAT, cost FLOAT
            )
        """))
        conn.execute(text("""
            INSERT INTO test_case_e VALUES
            (1, 'Alice', 'Tech', 'North', '2026-01-01', 1000.0, 700.0),
            (2, 'Bob', 'Tech', 'South', '2026-01-02', 2000.0, 1300.0)
        """))
        conn.commit()

        mapping_e = resolve_columns(conn, "test_case_e")
        assert mapping_e["profit_available"] == False, "Case E profit MUST NOT be assumed when no profit/margin column exists"
        assert mapping_e["profit"] is None, "Case E mapped profit MUST be None"

        dash_e = get_dashboard_data(conn, "test_case_e")
        assert dash_e["metrics"]["total_profit"] is None, f"Expected None, got {dash_e['metrics']['total_profit']}"
        assert dash_e["metrics"]["profit_available"] == False
        print("[OK] Case E passed: Does NOT assume profit margin or default 18% when only cost and revenue exist")

        # Cleanup test tables
        conn.execute(text("DROP TABLE IF EXISTS test_case_a"))
        conn.execute(text("DROP TABLE IF EXISTS test_case_b"))
        conn.execute(text("DROP TABLE IF EXISTS test_case_c"))
        conn.execute(text("DROP TABLE IF EXISTS test_case_e"))
        conn.commit()

    print("\n=== ALL PROFIT CASES SUCCESSFULLY VERIFIED! ===")

if __name__ == "__main__":
    test_cases()

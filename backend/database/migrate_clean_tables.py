import sys
import os
import sqlite3
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

from backend.main import clean_dataframe_numeric_columns
from backend.services.analysis_service import invalidate_dashboard_cache, get_dashboard_data
from backend.database.connection import SessionLocal, engine

db = SessionLocal()

print("--- Starting Database Clean Migration for Existing Datasets ---")
datasets = db.execute(sqlite3.connect('database/business.db').cursor().execute("SELECT id, client_id, name, table_name, row_count FROM datasets").fetchall) if False else None

conn = sqlite3.connect('database/business.db')
datasets = conn.execute("SELECT id, client_id, name, table_name, row_count FROM datasets").fetchall()

for d in datasets:
    ds_id, client_id, name, table_name, row_count = d
    print(f"\nProcessing Dataset {ds_id}: '{name}' (Table: {table_name}, Rows: {row_count})")
    try:
        df = pd.read_sql(f"SELECT * FROM `{table_name}`", engine)
        original_dtypes = df.dtypes.to_dict()
        df_cleaned = clean_dataframe_numeric_columns(df)
        
        changed_cols = []
        for col in df.columns:
            if str(original_dtypes[col]) != str(df_cleaned[col].dtype):
                changed_cols.append(f"{col} ({original_dtypes[col]} -> {df_cleaned[col].dtype})")
        
        if changed_cols:
            print(f"  Cleaning columns: {', '.join(changed_cols)}")
            df_cleaned.to_sql(table_name, engine, if_exists="replace", index=False, chunksize=2000, method="multi")
            print(f"  Successfully updated table `{table_name}` with cleaned numeric data.")
        else:
            print("  No text-formatted numeric columns required conversion.")
    except Exception as e:
        print(f"  Error processing `{table_name}`: {e}")

# Invalidate cache
invalidate_dashboard_cache()
print("\nAll dashboard caches successfully cleared.")

# Pre-warm & verify key datasets
print("\n--- Verifying Dashboard Metrics After Migration ---")
for check_ds_id in [15, 9, 11, 7]:
    ds_meta = next((d for d in datasets if d[0] == check_ds_id), None)
    if ds_meta:
        t_name = ds_meta[3]
        metrics = get_dashboard_data(db, table_name=t_name)["metrics"]
        print(f"Dataset {check_ds_id} ('{ds_meta[2]}', Table: {t_name}):")
        print(f"  Revenue: {metrics['total_revenue']:,}")
        print(f"  Profit: {metrics['total_profit']}")
        print(f"  Orders: {metrics['total_orders']:,}")
        print(f"  Customers: {metrics['total_customers']:,}")
        print(f"  AOV: {metrics['average_order_value']:,}")
        print(f"  Profit Available: {metrics['profit_available']} ({metrics['profit_source']})")

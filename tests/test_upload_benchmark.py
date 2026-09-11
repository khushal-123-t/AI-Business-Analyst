import time
import os
import sys
import io
import pandas as pd
import numpy as np
import sqlite3

sys.path.insert(0, '.')

from backend.main import (
    parse_uploaded_file_to_df,
    sanitize_dataframe_columns,
    clean_dataframe_numeric_columns,
    engine
)
from backend.config import settings
from sqlalchemy import text

sys.stdout.reconfigure(encoding='utf-8')

def generate_benchmark_csv(size_mb: float = 1.0) -> bytes:
    """Generates a realistic business dataset CSV in memory of roughly size_mb megabytes."""
    target_bytes = int(size_mb * 1024 * 1024)
    num_rows = max(100, int(target_bytes / 120))
    
    np.random.seed(42)
    categories = ['Electronics', 'Home & Kitchen', 'Apparel', 'Books', 'Health', 'Automotive', 'Toys', 'Beauty']
    regions = ['North America', 'Europe', 'Asia Pacific', 'Latin America', 'Middle East']
    dates = pd.date_range('2022-01-01', '2024-12-31', freq='h')
    
    df = pd.DataFrame({
        'order_id': [f"ORD-{i:07d}" for i in range(1, num_rows + 1)],
        'order_date': np.random.choice(dates.strftime('%Y-%m-%d'), size=num_rows),
        'customer_id': [f"CUST-{np.random.randint(1000, 99999):05d}" for _ in range(num_rows)],
        'customer_name': [f"Customer {np.random.randint(1, 10000)}" for _ in range(num_rows)],
        'category': np.random.choice(categories, size=num_rows),
        'region': np.random.choice(regions, size=num_rows),
        'unit_price': [f"${x:,.2f}" for x in np.random.uniform(10.0, 500.0, size=num_rows)],
        'quantity': np.random.randint(1, 15, size=num_rows),
        'revenue': [f"${x:,.2f}" for x in np.random.uniform(50.0, 5000.0, size=num_rows)],
        'profit': [f"${x:,.2f}" for x in np.random.uniform(5.0, 1500.0, size=num_rows)],
        'discount_rate': [f"{x:.1f}%" for x in np.random.uniform(0.0, 30.0, size=num_rows)]
    })
    
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    csv_bytes = buf.getvalue().encode('utf-8')
    return csv_bytes

def benchmark_optimized_pipeline(csv_bytes: bytes, label: str):
    print(f"\n============================================================")
    print(f"BENCHMARK: {label} ({len(csv_bytes)/(1024*1024):.2f} MB)")
    print(f"============================================================")
    
    timings = {}
    total_start = time.perf_counter()
    
    # 1. Upload receiving
    t0 = time.perf_counter()
    contents = csv_bytes
    timings['1. Upload receiving'] = time.perf_counter() - t0
    
    # 2. File read / memory
    t0 = time.perf_counter()
    bio = io.BytesIO(contents)
    timings['2. File memory stream'] = time.perf_counter() - t0
    
    # 3. CSV parsing
    t0 = time.perf_counter()
    df = parse_uploaded_file_to_df('benchmark.csv', contents)
    timings['3. CSV parsing (C-engine)'] = time.perf_counter() - t0
    row_count = len(df)
    col_count = len(df.columns)
    
    # 4. Data validation
    t0 = time.perf_counter()
    is_valid = row_count > 0 and col_count > 0
    timings['4. Data validation'] = time.perf_counter() - t0
    
    # 5. Data cleaning
    t0 = time.perf_counter()
    df = sanitize_dataframe_columns(df)
    df = clean_dataframe_numeric_columns(df)
    timings['5. Data cleaning (vectorized)'] = time.perf_counter() - t0
    
    # 6. Table creation & preparation
    t0 = time.perf_counter()
    table_name = f"bench_tbl_{int(time.time()*1000)}"
    timings['6. Table preparation'] = time.perf_counter() - t0
    
    # 7. Database insertion
    t0 = time.perf_counter()
    chunk_size = getattr(settings, 'CSV_CHUNK_SIZE', 10000)
    with engine.begin() as conn:
        conn.execute(text("PRAGMA synchronous = NORMAL"))
        conn.execute(text("PRAGMA journal_mode = WAL"))
        df.to_sql(table_name, conn, if_exists="replace", index=False, chunksize=chunk_size)
    timings['7. Database insertion (WAL)'] = time.perf_counter() - t0
    
    # 8. Schema detection
    t0 = time.perf_counter()
    with engine.connect() as conn:
        res = conn.execute(text(f"PRAGMA table_info(`{table_name}`)"))
        cols = res.fetchall()
    timings['8. Schema detection'] = time.perf_counter() - t0
    
    # 9 & 10. Profiling & AI calls
    timings['9. Data profiling (deferred)'] = 0.0
    timings['10. AI/LLM calls (separated)'] = 0.0
    
    # Cleanup table
    with engine.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS `{table_name}`"))
        
    total_time = time.perf_counter() - total_start
    timings['TOTAL TIME'] = total_time
    
    for stage, sec in timings.items():
        pct = (sec / total_time) * 100 if stage != 'TOTAL TIME' else 100
        bar = "#" * int(pct / 5)
        print(f"{stage:<40}: {sec:6.3f}s ({pct:5.1f}%) {bar}")
    print(f"Summary: {row_count:,} rows, {col_count} columns imported in {total_time:.3f}s")
    return total_time

if __name__ == "__main__":
    for size in [1.0, 5.0, 15.0]:
        data = generate_benchmark_csv(size_mb=size)
        benchmark_optimized_pipeline(data, label=f"{int(size)} MB CSV")

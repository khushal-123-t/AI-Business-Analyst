import pandas as pd
from sqlalchemy import create_engine
import os

# Load CSV
df = pd.read_csv("sales_data.csv")

# Create database folder
os.makedirs("database", exist_ok=True)

# SQLite database
engine = create_engine(
    "sqlite:///database/business.db"
)

# Save data to database
df.to_sql(
    "sales",
    engine,
    if_exists="replace",
    index=False
)

print("Database created successfully!")
print("Table: sales")
print(f"Rows inserted: {len(df)}")
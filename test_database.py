import pandas as pd
from sqlalchemy import create_engine

engine = create_engine(
    "sqlite:///database/business.db"
)

query = """
SELECT
    category,
    SUM(revenue) AS total_revenue
FROM sales
GROUP BY category
ORDER BY total_revenue DESC;
"""

df = pd.read_sql(query, engine)

print(df)
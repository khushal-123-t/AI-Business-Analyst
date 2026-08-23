import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

np.random.seed(42)
random.seed(42)

# -----------------------------
# Configuration
# -----------------------------

num_orders = 5000

products = {
    "Laptop": ("Electronics", 65000),
    "Phone": ("Electronics", 30000),
    "Headphones": ("Electronics", 3000),
    "Keyboard": ("Electronics", 2500),
    "Chair": ("Furniture", 7000),
    "Desk": ("Furniture", 12000),
    "Shoes": ("Fashion", 4000),
    "T-Shirt": ("Fashion", 1200),
    "Jeans": ("Fashion", 2500),
    "Coffee": ("Grocery", 500),
    "Rice": ("Grocery", 1000),
    "Oil": ("Grocery", 1500)
}

regions = ["North", "South", "East", "West"]

customers = [
    f"CUST{str(i).zfill(4)}"
    for i in range(1, 501)
]

customer_names = {
    customer: f"Customer {customer[-4:]}"
    for customer in customers
}

# -----------------------------
# Generate orders
# -----------------------------

start_date = datetime(2025, 1, 1)

data = []

for order_id in range(1, num_orders + 1):

    order_date = start_date + timedelta(
        days=random.randint(0, 364)
    )

    customer_id = random.choice(customers)

    product = random.choice(list(products.keys()))

    category, unit_price = products[product]

    quantity = random.randint(1, 5)

    discount = round(
        random.uniform(0, 0.20),
        2
    )

    revenue = quantity * unit_price * (1 - discount)

    profit_margin = random.uniform(0.08, 0.30)

    profit = revenue * profit_margin

    region = random.choice(regions)

    data.append([
        order_id,
        order_date.date(),
        customer_id,
        customer_names[customer_id],
        product,
        category,
        region,
        quantity,
        unit_price,
        round(revenue, 2),
        discount,
        round(profit, 2)
    ])

# -----------------------------
# Create DataFrame
# -----------------------------

columns = [
    "order_id",
    "order_date",
    "customer_id",
    "customer_name",
    "product",
    "category",
    "region",
    "quantity",
    "unit_price",
    "revenue",
    "discount",
    "profit"
]

df = pd.DataFrame(data, columns=columns)

# -----------------------------
# Save CSV
# -----------------------------

df.to_csv("sales_data.csv", index=False)

print("Dataset created successfully!")
print(f"Rows: {len(df)}")
print(df.head())
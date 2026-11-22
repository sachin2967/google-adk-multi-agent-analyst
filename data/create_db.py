"""Populates a realistic relational e-commerce database for analytical querying."""

import sqlite3
from pathlib import Path

import numpy as np


def create_sample_database(db_path: Path):
    """Generates a multi-table relational schema with realistic e-commerce data."""
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Table 1: Customers
    cur.execute("""
    CREATE TABLE customers (
        customer_id TEXT PRIMARY KEY,
        customer_city TEXT NOT NULL,
        customer_state TEXT NOT NULL,
        signup_date DATE NOT NULL
    )
    """)

    # Table 2: Products
    cur.execute("""
    CREATE TABLE products (
        product_id TEXT PRIMARY KEY,
        category TEXT NOT NULL,
        unit_cost REAL NOT NULL,
        retail_price REAL NOT NULL
    )
    """)

    # Table 3: Orders
    cur.execute("""
    CREATE TABLE orders (
        order_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        order_status TEXT NOT NULL,
        order_date DATE NOT NULL,
        delivered_date DATE,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    )
    """)

    # Table 4: Order Items
    cur.execute("""
    CREATE TABLE order_items (
        order_id TEXT NOT NULL,
        item_id INTEGER NOT NULL,
        product_id TEXT NOT NULL,
        seller_id TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        freight_value REAL NOT NULL,
        PRIMARY KEY (order_id, item_id),
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    )
    """)

    # Table 5: Reviews
    cur.execute("""
    CREATE TABLE reviews (
        review_id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        review_score INTEGER NOT NULL,
        review_text TEXT,
        review_date DATE NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
    )
    """)

    np.random.seed(42)

    # Populate Customers (500 customers across Indian metro hubs)
    cities = [
        ("Bengaluru", "KA"),
        ("Mumbai", "MH"),
        ("Delhi", "DL"),
        ("Hyderabad", "TG"),
        ("Pune", "MH"),
        ("Chennai", "TN"),
    ]
    customers_data = []
    for i in range(1, 501):
        c_id = f"CUST_{i:04d}"
        city, state = cities[np.random.choice(len(cities))]
        signup = f"2025-{np.random.randint(1, 12):02d}-{np.random.randint(1, 28):02d}"
        customers_data.append((c_id, city, state, signup))
    cur.executemany("INSERT INTO customers VALUES (?, ?, ?, ?)", customers_data)

    # Populate Products (50 products across categories)
    categories = [
        "Electronics",
        "Fashion",
        "Home & Kitchen",
        "Beauty & Personal",
        "Books & Stationery",
    ]
    products_data = []
    for i in range(1, 51):
        p_id = f"PROD_{i:03d}"
        cat = categories[np.random.choice(len(categories))]
        cost = round(float(np.random.uniform(150, 4000)), 2)
        price = round(cost * float(np.random.uniform(1.2, 1.8)), 2)
        products_data.append((p_id, cat, cost, price))
    cur.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", products_data)

    # Populate Orders & Items (1,200 orders across 2025)
    orders_data = []
    items_data = []
    reviews_data = []
    statuses = [
        "delivered",
        "delivered",
        "delivered",
        "delivered",
        "shipped",
        "canceled",
    ]

    for i in range(1, 1201):
        o_id = f"ORD_{i:05d}"
        cust_id = f"CUST_{np.random.randint(1, 501):04d}"
        status = np.random.choice(statuses, p=[0.75, 0.08, 0.05, 0.05, 0.04, 0.03])
        m = np.random.randint(1, 13)
        d = np.random.randint(1, 25)
        order_date = f"2025-{m:02d}-{d:02d}"
        deliv_date = (
            f"2025-{m:02d}-{d + np.random.randint(2, 6):02d}"
            if status == "delivered"
            else None
        )
        orders_data.append((o_id, cust_id, status, order_date, deliv_date))

        # 1 to 3 items per order
        # Convert NumPy scalars before SQLite binding. Some NumPy releases adapt
        # np.int64 as a BLOB, silently corrupting COUNT/SUM and AVG queries.
        num_items = int(np.random.choice([1, 2, 3], p=[0.7, 0.2, 0.1]))
        for item_idx in range(1, num_items + 1):
            prod = products_data[np.random.choice(len(products_data))]
            prod_id = prod[0]
            price = prod[3]
            qty = int(np.random.choice([1, 2], p=[0.85, 0.15]))
            freight = round(float(np.random.uniform(40, 150)), 2)
            seller_id = f"SELLER_{np.random.randint(1, 40):03d}"
            items_data.append((o_id, item_idx, prod_id, seller_id, qty, price, freight))

        # Reviews for delivered orders
        if status == "delivered" and np.random.rand() > 0.15:
            r_id = f"REV_{i:05d}"
            score = int(
                np.random.choice([1, 2, 3, 4, 5], p=[0.08, 0.07, 0.12, 0.28, 0.45])
            )
            comments = {
                1: "Damaged item received, delivery delayed by 4 days.",
                2: "Poor packaging and late arrival.",
                3: "Average product quality, as expected.",
                4: "Fast delivery, product matches description.",
                5: "Excellent quality! Will definitely order again.",
            }
            reviews_data.append((r_id, o_id, score, comments[score], deliv_date))

    cur.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", orders_data)
    cur.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, ?, ?, ?)", items_data)
    cur.executemany("INSERT INTO reviews VALUES (?, ?, ?, ?, ?)", reviews_data)

    conn.commit()
    conn.close()
    print(f"Database successfully created at: {db_path}")


if __name__ == "__main__":
    db_file = Path(__file__).resolve().parent / "ecommerce.db"
    create_sample_database(db_file)

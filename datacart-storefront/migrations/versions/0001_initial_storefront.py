"""Create and seed the initial DataCart storefront schema.

Revision ID: 0001
Revises:
Create Date: 2026-07-27
"""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
import random

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "ecommerce"


def _seed_rows() -> tuple[list[dict], ...]:
    rng = random.Random(42)

    # Keep the workshop fixture compact; ordering is part of the deterministic seed.
    # fmt: off
    first_names = [
        "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry",
        "Iris", "Jack", "Karen", "Leo", "Mia", "Noah", "Olivia", "Paul",
        "Quinn", "Ruby", "Sam", "Tara", "Uma", "Victor", "Wendy", "Xander",
        "Yara", "Zach", "Amber", "Blake", "Cora", "Derek", "Elena", "Felix",
        "Gina", "Hugo", "Isla", "Jake", "Kira", "Liam", "Maya", "Nate",
        "Opal", "Pete", "Rosa", "Sean", "Tina", "Uri", "Vera", "Wade",
        "Xena", "Yuri",
    ]
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
        "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
        "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    ]
    customers = []
    for index in range(100):
        first = first_names[index % len(first_names)]
        last = last_names[index % len(last_names)]
        customers.append(
            {
                "id": index + 1,
                "name": f"{first} {last}",
                "email": f"{first.lower()}.{last.lower()}.{index}@example.com",
            }
        )

    categories = {
        "Electronics": [
            "Laptop", "Headphones", "Phone Case", "USB Cable", "Webcam",
            "Keyboard", "Mouse", "Monitor", "Tablet", "Speaker",
        ],
        "Clothing": [
            "T-Shirt", "Jeans", "Sneakers", "Jacket", "Hat", "Scarf", "Socks",
            "Belt", "Hoodie", "Shorts",
        ],
        "Books": [
            "Python Guide", "SQL Mastery", "Data Engineering", "ML Handbook",
            "Cloud Atlas", "Clean Code", "System Design", "Algorithms",
            "DevOps Handbook", "AI Ethics",
        ],
        "Home": [
            "Desk Lamp", "Coffee Mug", "Plant Pot", "Cushion", "Candle",
            "Picture Frame", "Clock", "Vase", "Blanket", "Coaster",
        ],
        "Sports": [
            "Yoga Mat", "Water Bottle", "Resistance Band", "Jump Rope",
            "Dumbbell", "Tennis Ball", "Running Socks", "Gym Bag", "Towel",
            "Foam Roller",
        ],
    }
    # fmt: on
    products = []
    for category, items in categories.items():
        for item in items:
            products.append(
                {
                    "id": len(products) + 1,
                    "name": item,
                    "price": Decimal(str(round(rng.uniform(5.99, 299.99), 2))),
                    "category": category,
                }
            )

    raw_orders = [
        (1, 1, 1, 1, "1299.99", "USD", "2024-03-01 10:05:00", "delivered"),
        (2, 1, 2, 1, "89.99", "USD", "2024-03-05 14:22:00", "delivered"),
        (3, 2, 4, 1, "129.99", "USD", "2024-03-08 09:00:00", "shipped"),
        (4, 3, 3, 1, "449.99", "EUR", "2024-03-10 11:30:00", "confirmed"),
        (5, 4, 5, 2, "119.98", "EUR", "2024-03-12 16:45:00", "delivered"),
        (6, 5, 2, 1, "89.99", "GBP", "2024-03-15 08:10:00", "shipped"),
        (7, 6, 6, 3, "119.97", "AED", "2024-03-16 12:00:00", "pending"),
        (8, 7, 1, 1, "1299.99", "JPY", "2024-03-18 07:30:00", "confirmed"),
        (9, 8, 13, 2, "109.98", "EUR", "2024-03-19 15:15:00", "delivered"),
        (10, 9, 10, 1, "99.99", "EUR", "2024-03-20 10:00:00", "shipped"),
        (11, 10, 7, 1, "24.99", "INR", "2024-03-21 13:30:00", "delivered"),
        (12, 11, 8, 1, "49.99", "BRL", "2024-03-22 09:45:00", "confirmed"),
        (13, 12, 9, 2, "69.98", "CNY", "2024-03-23 18:20:00", "pending"),
        (14, 1, 11, 1, "29.99", "USD", "2024-03-24 11:05:00", "shipped"),
        (15, 2, 12, 2, "39.98", "USD", "2024-03-25 14:00:00", "delivered"),
        (16, 3, 15, 1, "29.99", "EUR", "2024-03-26 16:30:00", "pending"),
        (17, 4, 14, 1, "69.99", "EUR", "2024-03-27 08:00:00", "confirmed"),
        (18, 5, 4, 1, "129.99", "GBP", "2024-03-28 12:45:00", "shipped"),
        (19, 6, 3, 1, "449.99", "AED", "2024-03-29 10:10:00", "confirmed"),
        (20, 7, 5, 1, "59.99", "JPY", "2024-03-30 07:50:00", "pending"),
        (21, 8, 1, 1, "1299.99", "EUR", "2024-03-31 15:00:00", "confirmed"),
        (22, 9, 2, 2, "179.98", "EUR", "2024-04-01 09:30:00", "shipped"),
    ]
    orders = [
        {
            "id": order_id,
            "customer_id": customer_id,
            "product_id": product_id,
            "quantity": quantity,
            "total": Decimal(total),
            "currency": currency,
            "order_date": datetime.fromisoformat(order_date),
            "status": status,
        }
        for (
            order_id,
            customer_id,
            product_id,
            quantity,
            total,
            currency,
            order_date,
            status,
        ) in raw_orders
    ]

    warehouses = ["US-East", "US-West", "EU-Central"]
    inventory = []
    for product_id in range(1, 51):
        inventory.append(
            {
                "id": product_id,
                "product_id": product_id,
                "quantity": rng.randint(0, 200),
                "warehouse": warehouses[product_id % len(warehouses)],
                "reorder_level": rng.choice([5, 10, 15, 20]),
            }
        )

    order_items = []
    for order in orders:
        product_ids = rng.sample(range(1, 51), rng.randint(1, 4))
        if order["product_id"] not in product_ids:
            product_ids[0] = order["product_id"]
        remaining_total = float(order["total"])
        for item_index, product_id in enumerate(product_ids):
            quantity = rng.randint(1, 3)
            if item_index == len(product_ids) - 1:
                unit_price = round(max(remaining_total / quantity, 1.00), 2)
            else:
                unit_price = round(rng.uniform(9.99, 199.99), 2)
                remaining_total -= round(unit_price * quantity, 2)
            order_items.append(
                {
                    "id": len(order_items) + 1,
                    "order_id": order["id"],
                    "product_id": product_id,
                    "quantity": quantity,
                    "unit_price": Decimal(str(unit_price)),
                    "line_total": Decimal(str(round(unit_price * quantity, 2))),
                }
            )

    assert (
        len(customers),
        len(products),
        len(inventory),
        len(orders),
        len(order_items),
    ) == (100, 50, 50, 22, 52)
    return customers, products, inventory, orders, order_items


def upgrade() -> None:
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')

    customers_table = op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        schema=SCHEMA,
    )
    products_table = op.create_table(
        "products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("category", sa.String(length=50)),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    inventory_table = op.create_table(
        "inventory",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column(
            "quantity", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "warehouse",
            sa.String(length=50),
            server_default=sa.text("'US-East'"),
            nullable=False,
        ),
        sa.Column(
            "reorder_level", sa.Integer(), server_default=sa.text("10"), nullable=False
        ),
        sa.Column("last_restocked", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["product_id"], [f"{SCHEMA}.products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "warehouse"),
        schema=SCHEMA,
    )
    orders_table = op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column(
            "quantity", sa.Integer(), server_default=sa.text("1"), nullable=False
        ),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default=sa.text("'USD'"),
            nullable=False,
        ),
        sa.Column(
            "order_date", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')",
            name="ck_orders_status",
        ),
        sa.ForeignKeyConstraint(["customer_id"], [f"{SCHEMA}.customers.id"]),
        sa.ForeignKeyConstraint(["product_id"], [f"{SCHEMA}.products.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    order_items_table = op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column(
            "quantity", sa.Integer(), server_default=sa.text("1"), nullable=False
        ),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(
            ["order_id"], [f"{SCHEMA}.orders.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["product_id"], [f"{SCHEMA}.products.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    customers, products, inventory, orders, order_items = _seed_rows()
    op.bulk_insert(customers_table, customers)
    op.bulk_insert(products_table, products)
    op.bulk_insert(orders_table, orders)
    op.bulk_insert(inventory_table, inventory)
    op.bulk_insert(order_items_table, order_items)

    for table_name in ("customers", "products", "inventory", "orders", "order_items"):
        op.execute(
            f"""
            SELECT setval(
                pg_get_serial_sequence('{SCHEMA}.{table_name}', 'id'),
                (SELECT MAX(id) FROM {SCHEMA}.{table_name}),
                true
            )
            """
        )


def downgrade() -> None:
    op.drop_table("order_items", schema=SCHEMA)
    op.drop_table("inventory", schema=SCHEMA)
    op.drop_table("orders", schema=SCHEMA)
    op.drop_table("products", schema=SCHEMA)
    op.drop_table("customers", schema=SCHEMA)

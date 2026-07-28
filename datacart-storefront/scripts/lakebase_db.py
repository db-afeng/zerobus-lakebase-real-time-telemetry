"""Run Alembic or seed DataCart against a Lakebase branch."""

from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal
import os
from pathlib import Path
import random
import subprocess
import sys

from databricks.sdk import WorkspaceClient

ROOT = Path(__file__).resolve().parents[1]
GROUP_ROLE = "lakebase-app-schema-owner"
DATABASE = "databricks_postgres"
SCHEMA = "ecommerce"
CORE_TABLES = ("customers", "products", "inventory", "orders", "order_items")


def _branch_environment(
    profile: str, project: str, branch: str, role: str
) -> dict[str, str]:
    w = WorkspaceClient(profile=profile)
    parent = f"projects/{project}/branches/{branch}"
    endpoints = list(w.postgres.list_endpoints(parent=parent))
    endpoint = next(
        (
            candidate
            for candidate in endpoints
            if candidate.status
            and candidate.status.hosts
            and candidate.status.hosts.host
            and str(candidate.status.endpoint_type).endswith("READ_WRITE")
        ),
        None,
    )
    if endpoint is None:
        raise RuntimeError(f"No ready read-write endpoint found for {parent}")

    env = os.environ.copy()
    env.pop("PGPASSWORD", None)
    env.update(
        DATABRICKS_PROFILE=profile,
        ENDPOINT_NAME=endpoint.name,
        PGHOST=endpoint.status.hosts.host,
        PGPORT="5432",
        PGDATABASE=DATABASE,
        PGSSLMODE="require",
        PGUSER=role,
        LAKEBASE_PG_ROLE=role,
        DB_SCHEMA=SCHEMA,
    )
    return env


def _connect(env: dict[str, str]):
    os.environ.update(env)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from server.db import OAuthConnection

    return OAuthConnection.connect(
        dbname=DATABASE,
        user=env["LAKEBASE_PG_ROLE"],
        host=env["PGHOST"],
        port=int(env["PGPORT"]),
        sslmode=env["PGSSLMODE"],
        connect_timeout=15,
    )


def _verify_ownership(env: dict[str, str]) -> None:
    expected_objects = {
        "alembic_version",
        *CORE_TABLES,
        *(f"{table}_id_seq" for table in CORE_TABLES),
    }
    with _connect(env) as conn, conn.cursor() as cur:
        cur.execute("SELECT current_user")
        current_user = cur.fetchone()[0]
        if current_user != env["LAKEBASE_PG_ROLE"]:
            raise RuntimeError(
                f"Connected as {current_user!r}, expected {env['LAKEBASE_PG_ROLE']!r}"
            )

        cur.execute(
            """
            SELECT pg_get_userbyid(nspowner)
            FROM pg_namespace
            WHERE nspname = %s
            """,
            (SCHEMA,),
        )
        schema_row = cur.fetchone()
        if schema_row is None or schema_row[0] != env["LAKEBASE_PG_ROLE"]:
            actual = None if schema_row is None else schema_row[0]
            raise RuntimeError(f"{SCHEMA} schema owner is {actual!r}")

        cur.execute(
            """
            SELECT c.relname, pg_get_userbyid(c.relowner)
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s
              AND c.relname = ANY(%s)
            """,
            (SCHEMA, list(expected_objects)),
        )
        owners = dict(cur.fetchall())

    missing = expected_objects - owners.keys()
    wrong = {
        name: owner
        for name, owner in owners.items()
        if owner != env["LAKEBASE_PG_ROLE"]
    }
    if missing or wrong:
        raise RuntimeError(f"Ownership verification failed: missing={missing}, wrong={wrong}")
    print(f"Verified {SCHEMA} and {len(owners)} objects owned by {current_user}.")


def _seed_rows() -> tuple[list[dict], ...]:
    rng = random.Random(42)
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
    customers = [
        {
            "id": index + 1,
            "name": (
                f"{first_names[index % len(first_names)]} "
                f"{last_names[index % len(last_names)]}"
            ),
            "email": (
                f"{first_names[index % len(first_names)].lower()}."
                f"{last_names[index % len(last_names)].lower()}.{index}@example.com"
            ),
        }
        for index in range(100)
    ]

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
    inventory = [
        {
            "id": product_id,
            "product_id": product_id,
            "quantity": rng.randint(0, 200),
            "warehouse": warehouses[product_id % len(warehouses)],
            "reorder_level": rng.choice([5, 10, 15, 20]),
        }
        for product_id in range(1, 51)
    ]

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

    expected = (100, 50, 50, 22, 52)
    actual = tuple(
        len(rows)
        for rows in (customers, products, inventory, orders, order_items)
    )
    assert actual == expected
    return customers, products, inventory, orders, order_items


def _seed(env: dict[str, str]) -> None:
    customers, products, inventory, orders, order_items = _seed_rows()
    inserts = (
        (
            "customers",
            customers,
            """
            INSERT INTO ecommerce.customers (id, name, email)
            VALUES (%(id)s, %(name)s, %(email)s)
            ON CONFLICT (id) DO NOTHING
            """,
        ),
        (
            "products",
            products,
            """
            INSERT INTO ecommerce.products (id, name, price, category)
            VALUES (%(id)s, %(name)s, %(price)s, %(category)s)
            ON CONFLICT (id) DO NOTHING
            """,
        ),
        (
            "orders",
            orders,
            """
            INSERT INTO ecommerce.orders
                (id, customer_id, product_id, quantity, total, currency, order_date, status)
            VALUES
                (%(id)s, %(customer_id)s, %(product_id)s, %(quantity)s,
                 %(total)s, %(currency)s, %(order_date)s, %(status)s)
            ON CONFLICT (id) DO NOTHING
            """,
        ),
        (
            "inventory",
            inventory,
            """
            INSERT INTO ecommerce.inventory
                (id, product_id, quantity, warehouse, reorder_level)
            VALUES
                (%(id)s, %(product_id)s, %(quantity)s, %(warehouse)s, %(reorder_level)s)
            ON CONFLICT (id) DO NOTHING
            """,
        ),
        (
            "order_items",
            order_items,
            """
            INSERT INTO ecommerce.order_items
                (id, order_id, product_id, quantity, unit_price, line_total)
            VALUES
                (%(id)s, %(order_id)s, %(product_id)s, %(quantity)s,
                 %(unit_price)s, %(line_total)s)
            ON CONFLICT (id) DO NOTHING
            """,
        ),
    )

    with _connect(env) as conn, conn.cursor() as cur:
        for _, rows, statement in inserts:
            cur.executemany(statement, rows)
        for table in CORE_TABLES:
            cur.execute(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{SCHEMA}.{table}', 'id'),
                    (SELECT MAX(id) FROM {SCHEMA}.{table}),
                    true
                )
                """
            )
        for table, rows, _ in inserts:
            cur.execute(
                f"SELECT count(*) FROM {SCHEMA}.{table} WHERE id = ANY(%s)",
                ([row["id"] for row in rows],),
            )
            count = cur.fetchone()[0]
            if count != len(rows):
                raise RuntimeError(
                    f"{table}: found {count} fixture IDs, expected {len(rows)}"
                )
            print(f"{table}: {count} fixture rows present")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("migrate", "seed", "verify"))
    parser.add_argument("--profile", required=True)
    parser.add_argument(
        "--project", default="zerobus-lakebase-workshop-alex-feng"
    )
    parser.add_argument("--branch", default="production")
    parser.add_argument("--role", default=GROUP_ROLE)
    return parser


def main() -> None:
    args = _parser().parse_args()
    env = _branch_environment(args.profile, args.project, args.branch, args.role)
    if args.command == "migrate":
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=ROOT,
            env=env,
            check=True,
        )
        _verify_ownership(env)
    elif args.command == "seed":
        _seed(env)
    else:
        _verify_ownership(env)


if __name__ == "__main__":
    main()

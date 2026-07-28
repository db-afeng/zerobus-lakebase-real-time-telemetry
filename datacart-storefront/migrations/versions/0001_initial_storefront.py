"""Create the initial DataCart storefront schema.

Revision ID: 0001
Revises:
Create Date: 2026-07-27
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "ecommerce"


def upgrade() -> None:
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        schema=SCHEMA,
    )
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("category", sa.String(length=50)),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_table(
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
    op.create_table(
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
    op.create_table(
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


def downgrade() -> None:
    op.drop_table("order_items", schema=SCHEMA)
    op.drop_table("inventory", schema=SCHEMA)
    op.drop_table("orders", schema=SCHEMA)
    op.drop_table("products", schema=SCHEMA)
    op.drop_table("customers", schema=SCHEMA)

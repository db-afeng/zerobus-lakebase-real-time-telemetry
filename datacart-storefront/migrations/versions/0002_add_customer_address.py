"""Add an optional default address to customers.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-27
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "ecommerce"


def upgrade() -> None:
    op.add_column("customers", sa.Column("address", sa.Text(), nullable=True), schema=SCHEMA)


def downgrade() -> None:
    op.drop_column("customers", "address", schema=SCHEMA)

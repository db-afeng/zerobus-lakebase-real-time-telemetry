"""Enforce normalized customer email uniqueness.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-27
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX uq_customers_email_normalized
        ON ecommerce.customers (lower(trim(email)));
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX ecommerce.uq_customers_email_normalized")

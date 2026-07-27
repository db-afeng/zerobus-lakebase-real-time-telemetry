from __future__ import annotations

import os
import re
import time
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool, text

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None
DB_SCHEMA = os.environ.get("DB_SCHEMA", "ecommerce")
_LOCK_NAME = "datacart-storefront-alembic"
_CORE_TABLES = ("customers", "products", "inventory", "orders", "order_items")

if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", DB_SCHEMA):
    raise ValueError(f"Invalid DB_SCHEMA identifier: {DB_SCHEMA!r}")


def _connect_with_retry():
    """Wake an autoscaled endpoint and return an OAuth-authenticated connection."""
    from server.db import (
        OAuthConnection,
        database,
        host,
        port,
        sslmode,
        username,
    )

    for attempt in range(1, 4):
        try:
            return OAuthConnection.connect(
                dbname=database,
                user=username,
                host=host,
                port=port,
                sslmode=sslmode,
                connect_timeout=15,
            )
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=DB_SCHEMA,
    )
    context.execute(f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}"')
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(
        "postgresql+psycopg://",
        creator=_connect_with_retry,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}"'))
        connection.commit()

        version_exists = connection.scalar(
            text("SELECT to_regclass(:name) IS NOT NULL"),
            {"name": f"{DB_SCHEMA}.alembic_version"},
        )
        legacy_table_count = connection.scalar(
            text(
                """
                SELECT count(*)
                FROM information_schema.tables
                WHERE table_schema = :schema
                  AND table_name IN (
                    'customers', 'products', 'inventory', 'orders', 'order_items'
                  )
                """
            ),
            {"schema": DB_SCHEMA},
        )
        connection.commit()
        if legacy_table_count and not version_exists:
            tables = ", ".join(_CORE_TABLES)
            raise RuntimeError(
                f"Found legacy tables in schema {DB_SCHEMA!r} ({tables}) without "
                "Alembic state. Fresh deployments are supported; recreate the "
                "Lakebase project or transfer object ownership before adopting it."
            )

        connection.execute(
            text("SELECT pg_advisory_lock(hashtext(:name))"), {"name": _LOCK_NAME}
        )
        connection.commit()
        try:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                version_table_schema=DB_SCHEMA,
                transaction_per_migration=True,
            )
            with context.begin_transaction():
                context.run_migrations()
        finally:
            if connection.in_transaction():
                connection.rollback()
            connection.execute(
                text("SELECT pg_advisory_unlock(hashtext(:name))"),
                {"name": _LOCK_NAME},
            )
            connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

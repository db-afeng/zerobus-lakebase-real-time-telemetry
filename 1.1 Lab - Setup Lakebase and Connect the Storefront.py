# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 1.1: Verify the Storefront and Prepare Zerobus
# MAGIC
# MAGIC The DataCart Storefront now applies its Lakebase schema automatically when the app starts.
# MAGIC Alembic creates and versions the `ecommerce` schema, its five core tables, and the workshop's
# MAGIC sample data before FastAPI begins serving traffic. No manual PostgreSQL setup or grants are
# MAGIC required.
# MAGIC
# MAGIC This lab verifies that the deployed app is available, then prepares the Unity Catalog
# MAGIC `clickstream_bronze` Delta table used by Lab 3.1. Unity Catalog objects remain outside
# MAGIC Alembic because they are not PostgreSQL objects.
# MAGIC
# MAGIC ## Learning Objectives
# MAGIC 1. Verify that the bundle-deployed storefront is available
# MAGIC 2. Create the clickstream bronze Delta table in Unity Catalog
# MAGIC 3. Grant the storefront service principal permission to ingest through Zerobus
# MAGIC
# MAGIC > **Setup expectation:** The Lakebase Autoscaling project and DataCart Storefront app are
# MAGIC > deployed by the bundle before this lab. See `WORKSHOP_SETUP.md` if they are missing.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Architecture
# MAGIC
# MAGIC ```
# MAGIC Lakebase Autoscaling (created by bundle)
# MAGIC └── production
# MAGIC     └── ecommerce (created and versioned by app startup / Alembic)
# MAGIC         ├── customers
# MAGIC         ├── products
# MAGIC         ├── inventory
# MAGIC         ├── orders
# MAGIC         └── order_items
# MAGIC
# MAGIC Unity Catalog: <your-catalog>.ecommerce
# MAGIC └── clickstream_bronze (created below for Zerobus)
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Verify the Storefront Deployment
# MAGIC
# MAGIC The app resource binding creates a PostgreSQL login for the app service principal and injects
# MAGIC the Lakebase connection settings. At startup, the app runs `alembic upgrade head` using that
# MAGIC identity, so the migrated tables are owned by the identity that reads and writes them.

# COMMAND ----------

from databricks.sdk import WorkspaceClient  # type: ignore[import-not-found]

w = WorkspaceClient()
APP_NAME = f"storefront-{w.current_user.me().id}"
app_info = w.apps.get(APP_NAME)
SP_CLIENT_ID = app_info.service_principal_client_id

print(f"App:    {APP_NAME}")
print(f"App SP: {SP_CLIENT_ID}")
print(f"URL:    {app_info.url}")
print("\nOpen the URL and confirm the product catalog loads.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Provision the Clickstream Bronze Table
# MAGIC
# MAGIC Lab 3.1 pushes storefront views, clicks, and add-to-cart events into this table through
# MAGIC Zerobus. Zerobus does not create its target table, so create the empty Delta table first.
# MAGIC
# MAGIC `event_ts` intentionally lands as raw ISO-8601 text. The downstream silver layer casts it to
# MAGIC `TIMESTAMP`.

# COMMAND ----------

# Set the Unity Catalog used by Labs 2.1, 3.1, and 4.1.
UC_CATALOG = "<add-your-catalog-name-here>"
UC_SCHEMA = "ecommerce"
BRONZE_TABLE = f"{UC_CATALOG}.{UC_SCHEMA}.clickstream_bronze"

if UC_CATALOG.startswith("<"):
    raise ValueError(
        "Set UC_CATALOG to your Unity Catalog name before running this cell."
    )

spark_session = globals().get("spark")
if spark_session is None:
    raise RuntimeError("This cell must run on Databricks notebook compute with Spark.")

spark_session.sql(f"CREATE SCHEMA IF NOT EXISTS {UC_CATALOG}.{UC_SCHEMA}")
spark_session.sql(f"""
    CREATE TABLE IF NOT EXISTS {BRONZE_TABLE} (
        event_type  STRING,
        product_id  INT,
        event_ts    STRING
    )
    USING DELTA
    COMMENT 'Raw storefront clickstream — Zerobus ingest target (Lab 3.1). Append-only, at-least-once. event_ts is raw ISO-8601 text; silver casts to TIMESTAMP.'
""")
print(f"Bronze clickstream table ready: {BRONZE_TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Grant Zerobus Write Access
# MAGIC
# MAGIC Zerobus authenticates as the storefront service principal. Unity Catalog requires explicit
# MAGIC catalog, schema, and table privileges for ingestion.

# COMMAND ----------

# Re-resolve the app so this cell is safe to run independently after Step 1.
APP_NAME = f"storefront-{w.current_user.me().id}"
SP_CLIENT_ID = w.apps.get(APP_NAME).service_principal_client_id

spark_session.sql(f"GRANT USE CATALOG ON CATALOG {UC_CATALOG} TO `{SP_CLIENT_ID}`")
spark_session.sql(
    f"GRANT USE SCHEMA ON SCHEMA {UC_CATALOG}.{UC_SCHEMA} TO `{SP_CLIENT_ID}`"
)
spark_session.sql(f"GRANT MODIFY, SELECT ON TABLE {BRONZE_TABLE} TO `{SP_CLIENT_ID}`")

print(f"Granted Zerobus access on {BRONZE_TABLE}")
print(f"to storefront SP {SP_CLIENT_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Done
# MAGIC
# MAGIC The storefront database was already initialized by Alembic during app startup. The Unity
# MAGIC Catalog bronze target is now ready for Lab 3.1's Zerobus producer.

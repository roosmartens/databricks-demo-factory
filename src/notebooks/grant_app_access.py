# Databricks notebook source
# MAGIC %md
# MAGIC # Grant the web app read access to the gold table
# MAGIC
# MAGIC The Databricks App runs as its own service principal. This lets it read the demo schema and nothing else.

# COMMAND ----------

import re

dbutils.widgets.text("catalog", "workspace", "Unity Catalog")
dbutils.widgets.text("schema", "demo_factory", "Schema")
dbutils.widgets.text("app_principal", "", "App service principal (client ID)")

catalog = dbutils.widgets.get("catalog").strip()
schema = dbutils.widgets.get("schema").strip()
principal = dbutils.widgets.get("app_principal").strip()

identifier = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
uuid = re.compile(r"^[0-9a-fA-F-]{36}$")
if not identifier.fullmatch(catalog) or not identifier.fullmatch(schema):
    raise ValueError("Catalog and schema must be simple Unity Catalog identifiers.")
if not uuid.fullmatch(principal):
    raise ValueError("app_principal must be the app service principal's client ID (a UUID).")

# COMMAND ----------

spark.sql(f"GRANT USE CATALOG ON CATALOG `{catalog}` TO `{principal}`")
spark.sql(f"GRANT USE SCHEMA, SELECT ON SCHEMA `{catalog}`.`{schema}` TO `{principal}`")
display(spark.sql(f"SHOW GRANTS `{principal}` ON SCHEMA `{catalog}`.`{schema}`"))

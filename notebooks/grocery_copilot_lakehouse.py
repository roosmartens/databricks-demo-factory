# Databricks notebook source
# MAGIC %md
# MAGIC # Grocery inventory copilot: sources → Gold → model → knowledge index
# MAGIC
# MAGIC One notebook for the whole demo, in the order the story is told:
# MAGIC
# MAGIC 1. **Bronze**: the four sources exactly as delivered: Postgres point of sale and promo calendar, MySQL store inventory, and the supplier-portal CSV export. In production these land through Lakeflow Connect (Postgres, MySQL) and Auto Loader (portal export); here they come from `app/demos/grocery/engine.py`, so the app's offline mode shows the same numbers.
# MAGIC 2. **Silver**: keys conformed onto one core entity, the **store-product** (store_code × sku), with bad rows quarantined instead of dropped.
# MAGIC 3. **Model**: the demand forecaster is backtested, tracked in MLflow and registered in Unity Catalog as `grocery_demand_forecast@champion`.
# MAGIC 4. **Gold**: `gold_store_product_risk` (one row per store-product: stockout probability, waste, actions) and `gold_store_product_projection` (7-day projection), which the app reads.
# MAGIC 5. **Knowledge**: supplier documents chunked into `supplier_knowledge_chunks` and synced to a Vector Search index for the copilot.
# MAGIC
# MAGIC Run it from the repo's Git folder so `app/` can be imported. All data is synthetic.

# COMMAND ----------

# MAGIC %pip install -q "mlflow>=3.1" "databricks-vectorsearch>=0.40"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import json
import os
import re
import sys

import mlflow
import pandas as pd
from mlflow.models import infer_signature
from mlflow.tracking import MlflowClient
from pyspark.sql import functions as F

sys.path.append(os.path.abspath(".."))  # repo root, so `import app` works from notebooks/
from app.demos.grocery import engine as grocery
from app.demos.grocery.copilot import load_passages

dbutils.widgets.text("catalog", "main", "Unity Catalog")
dbutils.widgets.text("schema", "grocery_copilot", "Schema")
dbutils.widgets.text("vector_endpoint", "", "Vector Search endpoint (optional)")
catalog = dbutils.widgets.get("catalog").strip()
schema = dbutils.widgets.get("schema").strip()
vector_endpoint = dbutils.widgets.get("vector_endpoint").strip()

identifier = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
if not identifier.fullmatch(catalog) or not identifier.fullmatch(schema):
    raise ValueError("Catalog and schema must be simple Unity Catalog identifiers.")
ns = f"{catalog}.{schema}"
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {ns}")


def save(frame: pd.DataFrame, name: str, comment: str):
    (spark.createDataFrame(frame).write.format("delta").mode("overwrite")
     .option("overwriteSchema", "true").saveAsTable(f"{ns}.{name}"))
    spark.sql(f"COMMENT ON TABLE {ns}.{name} IS '{comment}'")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1 · Bronze: sources as delivered
# MAGIC
# MAGIC Keep raw keys and quirks (lower-case store codes, returns booked as negative sales). Bronze is the audit trail; nothing is fixed here.

# COMMAND ----------

sources = grocery.make_sources()
bronze = {
    "postgres.pos.sales_daily": ("bronze_pos_sales_daily", "Postgres POS daily sales, as extracted"),
    "postgres.commercial.promo_calendar": ("bronze_promo_calendar", "Postgres promotion calendar"),
    "mysql.wms.store_inventory": ("bronze_store_inventory", "MySQL store stock snapshot 05:30"),
    "saas.supplier_portal.confirmed_deliveries": ("bronze_supplier_deliveries",
                                                  "Supplier portal CSV export: confirmed deliveries"),
}
for key, (table, comment) in bronze.items():
    save(sources[key], table, comment)
    print(f"{ns}.{table}: {len(sources[key])} rows")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2 · Silver: one store-product, quality enforced
# MAGIC
# MAGIC `grocery.unify` maps POS `store_id`/`sku`, MySQL `store_code`/`ean` and portal `gtin` onto store_code × sku. In a Lakeflow Declarative Pipeline the same rules become expectations (`expect_or_drop` into a quarantine table), so the data quality numbers show up in the pipeline UI and in lineage.

# COMMAND ----------

silver = grocery.unify(sources)
save(silver["sales"], "silver_sales", "Daily sales per store-product; quarantined rows removed")
save(silver["inventory"], "silver_inventory", "Stock per store-product, keys standardized")
save(silver["deliveries"], "silver_deliveries", "Confirmed deliveries per store-product")
save(silver["promos"], "silver_promotions", "Planned promotions per product and day")
print(json.dumps(silver["quality"], indent=2))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3 · Model: backtest, track, register
# MAGIC
# MAGIC The forecaster is deliberately explainable (recent level × weekday shape × promo uplift). It is wrapped as an MLflow pyfunc so it can be served, monitored and replaced by a stronger model without the app changing. The backtest compares it with how planners forecast today: same weekday last week.

# COMMAND ----------


class ForecastModel(mlflow.pyfunc.PythonModel):
    def __init__(self, fitted):
        self.fitted = fitted

    def predict(self, context, model_input: pd.DataFrame):
        frame = model_input.assign(date=pd.to_datetime(model_input["date"]))
        return self.fitted.predict(frame)


current_user = spark.sql("SELECT current_user()").first()[0]
mlflow.set_registry_uri("databricks-uc")
mlflow.set_experiment(f"/Users/{current_user}/grocery-demand-forecast")
model_name = f"{ns}.grocery_demand_forecast"

with mlflow.start_run(run_name="grocery-demand-forecast") as run:
    backtest = grocery.backtest(silver["sales"])
    mlflow.log_metrics(backtest)
    mlflow.log_params({"model": "SeasonalPromoForecaster", "level_days": 28,
                       "source_table": f"{ns}.silver_sales"})
    fitted = grocery.SeasonalPromoForecaster().fit(silver["sales"])
    example = silver["sales"][["store_code", "sku", "date", "promo"]].head(5).assign(
        date=lambda f: f["date"].dt.strftime("%Y-%m-%d"))
    info = mlflow.pyfunc.log_model(
        name="model", python_model=ForecastModel(fitted), input_example=example,
        signature=infer_signature(example, fitted.predict(example.assign(
            date=pd.to_datetime(example["date"])))),
        registered_model_name=model_name, code_paths=["../app"])

MlflowClient().set_registered_model_alias(model_name, "champion", info.registered_model_version)
print(f"Backtest WAPE {backtest['model_wape']:.1f}% vs {backtest['current_wape']:.1f}% today")
print(f"Registered {model_name} v{info.registered_model_version} as @champion")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4 · Gold: risk and projection per store-product
# MAGIC
# MAGIC These two tables are what the app, Genie and dashboards read. Actions are stored as JSON so the copilot can explain exactly what the rules proposed.

# COMMAND ----------

snapshot = grocery.build_snapshot(silver)
risk = pd.DataFrame(snapshot["items"]).assign(
    actions_json=lambda f: f["actions"].map(json.dumps)).drop(columns=["actions"])
risk["model_version"] = str(info.registered_model_version)
save(risk, "gold_store_product_risk",
     "Stockout probability, waste and recommended actions per store-product, next 7 days")
save(pd.DataFrame(snapshot["daily"]), "gold_store_product_projection",
     "Daily forecast, confirmed deliveries and projected stock per store-product")
save(pd.DataFrame([{"as_of": snapshot["as_of"], "run_id": run.info.run_id,
                    "quality_json": json.dumps(snapshot["quality"]),
                    "backtest_json": json.dumps(snapshot["backtest"])}]),
     "gold_copilot_run", "One row per scoring run: data quality and backtest summary")

for column, comment in {
    "stockout_probability": "Chance the shelf runs empty within 7 days, given forecast uncertainty",
    "waste_units": "Units on hand that will not sell before the oldest batch expires",
    "value_at_risk_eur": "Expected lost sales (at price) plus waste (at cost), in euro",
}.items():
    spark.sql(f"ALTER TABLE {ns}.gold_store_product_risk ALTER COLUMN {column} COMMENT '{comment}'")

display(spark.table(f"{ns}.gold_store_product_risk")
        .select("store_name", "product_name", "status", "stockout_probability", "stockout_date",
                "waste_units", "value_at_risk_eur")
        .orderBy(F.desc("value_at_risk_eur")))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5 · Knowledge: supplier documents for the copilot
# MAGIC
# MAGIC One chunk per document section, with Change Data Feed on so a Delta Sync Vector Search index stays current when buyers add new grower updates. Set the `vector_endpoint` widget to create the index; the app then uses it through `COPILOT_VECTOR_INDEX`.

# COMMAND ----------

chunks = pd.DataFrame([{"chunk_id": f"{p['doc']}#{i}", "doc": p["doc"], "title": p["title"],
                        "section": p["section"], "text": p["text"]}
                       for i, p in enumerate(load_passages())])
save(chunks, "supplier_knowledge_chunks", "Supplier knowledge, one row per document section")
spark.sql(f"ALTER TABLE {ns}.supplier_knowledge_chunks "
          "SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
print(f"{len(chunks)} chunks")

if vector_endpoint:
    from databricks.vector_search.client import VectorSearchClient

    index_name = f"{ns}.supplier_knowledge_index"
    client = VectorSearchClient()
    existing = [i["name"] for i in client.list_indexes(vector_endpoint).get("vector_indexes", [])]
    if index_name in existing:
        client.get_index(vector_endpoint, index_name).sync()
    else:
        client.create_delta_sync_index(
            endpoint_name=vector_endpoint, index_name=index_name,
            source_table_name=f"{ns}.supplier_knowledge_chunks", pipeline_type="TRIGGERED",
            primary_key="chunk_id", embedding_source_column="text",
            embedding_model_endpoint_name="databricks-gte-large-en")
    print(f"Vector Search index: {index_name}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Governance, in one cell
# MAGIC
# MAGIC Examples of what the CDO will ask for. Group names are placeholders.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Store managers see only their own store; category managers see everything.
# MAGIC -- CREATE FUNCTION main.grocery_copilot.own_store(store_code STRING)
# MAGIC --   RETURN is_account_group_member('category_managers')
# MAGIC --       OR is_account_group_member(concat('store_', lower(replace(store_code, '-', '_'))));
# MAGIC -- ALTER TABLE main.grocery_copilot.gold_store_product_risk
# MAGIC --   SET ROW FILTER main.grocery_copilot.own_store ON (store_code);
# MAGIC -- GRANT SELECT ON TABLE main.grocery_copilot.gold_store_product_risk TO `store_managers`;
# MAGIC SELECT status, count(*) AS store_products, round(sum(value_at_risk_eur)) AS eur_at_risk
# MAGIC FROM main.grocery_copilot.gold_store_product_risk
# MAGIC GROUP BY status ORDER BY eur_at_risk DESC

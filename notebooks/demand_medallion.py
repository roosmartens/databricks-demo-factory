# Databricks notebook source
# MAGIC %md
# MAGIC # Demand data: Bronze → Silver → Gold
# MAGIC
# MAGIC This notebook is a runnable, synthetic end-to-end example. Replace the Bronze sample generator with the case's ingestion step when its source data is known. The Silver and Gold tables retain daily, market, and category detail for downstream analysis.

# COMMAND ----------

from pyspark.sql import functions as F
import re

dbutils.widgets.text("catalog", "main", "Unity Catalog")
dbutils.widgets.text("schema", "demo_factory", "Schema")
dbutils.widgets.text("periods", "100", "Number of days")

catalog = dbutils.widgets.get("catalog").strip()
schema = dbutils.widgets.get("schema").strip()
periods = int(dbutils.widgets.get("periods"))

identifier = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
if not identifier.fullmatch(catalog) or not identifier.fullmatch(schema):
    raise ValueError("Catalog and schema must be simple Unity Catalog identifiers.")
if not 1 <= periods <= 366:
    raise ValueError("periods must be between 1 and 366.")

bronze_table = f"{catalog}.{schema}.bronze_demand"
silver_table = f"{catalog}.{schema}.silver_demand"
gold_table = f"{catalog}.{schema}.gold_daily_demand"

# COMMAND ----------
# MAGIC %md
# MAGIC ## Bronze — raw synthetic demand
# MAGIC
# MAGIC In a customer implementation, this is where the source ingestion writes its unmodified records.

# COMMAND ----------

regions = spark.createDataFrame(
    [(0, "Netherlands"), (1, "Germany"), (2, "France")],
    "region_index INT, region STRING",
)
categories = spark.createDataFrame(
    [(0, "Fresh food"), (1, "Beverages"), (2, "Household")],
    "category_index INT, category STRING",
)
days = (
    spark.range(periods)
    .withColumnRenamed("id", "day_index")
    .withColumn(
        "date",
        F.date_sub(
            F.to_date(F.lit("2026-09-30")),
            (F.lit(periods - 1) - F.col("day_index")).cast("int"),
        ),
    )
)

bronze = (
    days.crossJoin(regions)
    .crossJoin(categories)
    .withColumn(
        "base",
        F.lit(175.0) + F.col("region_index") * 45 + F.col("category_index") * 30,
    )
    .withColumn(
        "promotion",
        (F.col("day_index") % 23 < 4).cast("int"),
    )
    .withColumn(
        "seasonal",
        35
        * F.sin(
            2 * F.lit(3.141592653589793) * F.col("day_index") / 7
            + F.col("category_index")
        ),
    )
    .withColumn(
        "actual_noise",
        F.pmod(
            F.xxhash64("day_index", "region_index", "category_index"),
            F.lit(43),
        )
        - 21,
    )
    .withColumn(
        "baseline_noise",
        F.pmod(
            F.xxhash64("category_index", "region_index", "day_index"),
            F.lit(77),
        )
        - 38,
    )
    .withColumn(
        "improved_noise",
        F.pmod(
            F.xxhash64("region_index", "category_index", "day_index"),
            F.lit(33),
        )
        - 16,
    )
    .select(
        "date",
        "region",
        "category",
        F.round(
            F.greatest(
                F.lit(10.0),
                F.col("base")
                + F.col("seasonal")
                + F.col("promotion") * 55
                + F.col("actual_noise"),
            ),
            1,
        ).alias("actual"),
        F.round(
            F.greatest(F.lit(10.0), F.col("base") + F.col("baseline_noise")),
            1,
        ).alias("baseline"),
        F.round(
            F.greatest(
                F.lit(10.0),
                F.col("base")
                + F.col("seasonal")
                + F.col("promotion") * 55
                + F.col("actual_noise")
                + F.col("improved_noise"),
            ),
            1,
        ).alias("improved"),
        "promotion",
    )
)

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
bronze.write.format("delta").mode("overwrite").saveAsTable(bronze_table)
display(spark.table(bronze_table).limit(10))

# COMMAND ----------
# MAGIC %md
# MAGIC ## Silver — typed, validated, and standardized

# COMMAND ----------

silver_source = spark.read.table(bronze_table)
required_columns = {"date", "region", "category", "actual", "baseline", "improved", "promotion"}
missing_columns = required_columns.difference(silver_source.columns)
if missing_columns:
    raise ValueError(f"Bronze input is missing required columns: {sorted(missing_columns)}")

normalized = silver_source.select(
    F.to_date("date").alias("demand_date"),
    F.trim(F.col("region").cast("string")).alias("region"),
    F.trim(F.col("category").cast("string")).alias("category"),
    F.col("actual").cast("double").alias("actual_units"),
    F.col("baseline").cast("double").alias("baseline_units"),
    F.col("improved").cast("double").alias("improved_units"),
    F.col("promotion").cast("int").alias("promotion"),
)
valid_record = (
    F.col("demand_date").isNotNull()
    & F.col("region").isNotNull()
    & (F.length("region") > 0)
    & F.col("category").isNotNull()
    & (F.length("category") > 0)
    & F.col("actual_units").isNotNull()
    & (F.col("actual_units") >= 0)
    & F.col("baseline_units").isNotNull()
    & (F.col("baseline_units") >= 0)
    & F.col("improved_units").isNotNull()
    & (F.col("improved_units") >= 0)
    & F.col("promotion").isin(0, 1)
)
valid_record = F.coalesce(valid_record, F.lit(False))
invalid_count = normalized.filter(~valid_record).count()
print(f"Rows excluded by Silver validation: {invalid_count}")

silver = normalized.filter(valid_record)
if silver.isEmpty():
    raise ValueError("Silver validation produced no usable demand rows.")

silver = (
    silver.withColumn("baseline_abs_error", F.abs(F.col("actual_units") - F.col("baseline_units")))
    .withColumn("improved_abs_error", F.abs(F.col("actual_units") - F.col("improved_units")))
    .withColumn("absolute_actual_units", F.abs("actual_units"))
)
silver.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    silver_table
)
display(spark.table(silver_table).limit(10))

# COMMAND ----------
# MAGIC %md
# MAGIC ## Gold — daily demand and forecast metrics
# MAGIC
# MAGIC Keep market and category in the grain so the app and analysts can filter without losing detail.

# COMMAND ----------

gold = (
    spark.read.table(silver_table)
    .groupBy("demand_date", "region", "category")
    .agg(
        F.sum("actual_units").alias("actual_units"),
        F.sum("baseline_units").alias("baseline_units"),
        F.sum("improved_units").alias("improved_units"),
        F.sum("baseline_abs_error").alias("baseline_abs_error"),
        F.sum("improved_abs_error").alias("improved_abs_error"),
        F.sum("absolute_actual_units").alias("absolute_actual_units"),
        F.sum("promotion").alias("promotion_days"),
    )
)
gold.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    gold_table
)

print(f"Bronze table: {bronze_table}")
print(f"Silver table: {silver_table}")
print(f"Gold table:   {gold_table}")
display(spark.table(gold_table).orderBy(F.desc("demand_date")).limit(20))

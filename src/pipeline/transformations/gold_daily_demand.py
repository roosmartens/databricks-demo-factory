from pyspark import pipelines as dp
from pyspark.sql import functions as F


@dp.materialized_view(
    name="gold_daily_demand",
    comment="Daily demand and forecast error by market and category, ready for the planning app. Keeps market and category so users can filter.",
    table_properties={"quality": "gold"},
)
def gold_daily_demand():
    return (
        spark.read.table("silver_demand")
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

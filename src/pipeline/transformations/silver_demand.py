from pyspark import pipelines as dp
from pyspark.sql import functions as F


@dp.table(
    name="silver_demand",
    comment="Typed, validated and standardized demand. Invalid records are dropped and counted in the pipeline quality metrics.",
    table_properties={"quality": "silver"},
)
@dp.expect_all_or_drop(
    {
        "valid_date": "demand_date IS NOT NULL",
        "valid_region": "region IS NOT NULL AND length(region) > 0",
        "valid_category": "category IS NOT NULL AND length(category) > 0",
        "non_negative_actual": "actual_units IS NOT NULL AND actual_units >= 0",
        "non_negative_forecasts": "baseline_units >= 0 AND improved_units >= 0",
        "valid_promotion_flag": "promotion IN (0, 1)",
    }
)
def silver_demand():
    return (
        spark.readStream.table("bronze_demand")
        .select(
            F.to_date("date").alias("demand_date"),
            F.trim(F.col("region")).alias("region"),
            F.trim(F.col("category")).alias("category"),
            F.col("actual").cast("double").alias("actual_units"),
            F.col("baseline").cast("double").alias("baseline_units"),
            F.col("improved").cast("double").alias("improved_units"),
            F.col("promotion").cast("int").alias("promotion"),
        )
        .withColumn("baseline_abs_error", F.abs(F.col("actual_units") - F.col("baseline_units")))
        .withColumn("improved_abs_error", F.abs(F.col("actual_units") - F.col("improved_units")))
        .withColumn("absolute_actual_units", F.abs(F.col("actual_units")))
    )

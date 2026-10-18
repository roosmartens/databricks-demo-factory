from pyspark import pipelines as dp
from pyspark.sql import functions as F


@dp.table(
    name="bronze_demand",
    comment="Raw synthetic demand files from the landing volume, ingested as-is with lineage columns.",
    table_properties={"quality": "bronze"},
)
def bronze_demand():
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaHints", "actual DOUBLE, baseline DOUBLE, improved DOUBLE, promotion INT")
        .load(spark.conf.get("landing_path"))
        .select(
            "*",
            F.col("_metadata.file_path").alias("source_file"),
            F.current_timestamp().alias("ingested_at"),
        )
    )

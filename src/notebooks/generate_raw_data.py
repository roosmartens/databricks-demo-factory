# Databricks notebook source
# MAGIC %md
# MAGIC # Generate raw synthetic demand files
# MAGIC
# MAGIC Writes one JSON-lines file per day into a Unity Catalog volume, standing in for a source system that drops files daily.
# MAGIC
# MAGIC * Files are named by date and never overwritten, so re-running is safe and Auto Loader only ingests new days.
# MAGIC * To simulate "new data arrived", re-run with a larger **days** value.
# MAGIC * All values are synthetic and illustrative. Replace this notebook with the real ingestion step for a customer case.

# COMMAND ----------

import datetime as dt
import json
import math
import re
from itertools import product
from pathlib import Path

import numpy as np

dbutils.widgets.text("catalog", "workspace", "Unity Catalog")
dbutils.widgets.text("schema", "demo_factory", "Schema")
dbutils.widgets.text("start_date", "2026-06-23", "First day (YYYY-MM-DD)")
dbutils.widgets.text("days", "100", "Number of days")
dbutils.widgets.dropdown("inject_bad_rows", "true", ["true", "false"], "Include a few bad records")

catalog = dbutils.widgets.get("catalog").strip()
schema = dbutils.widgets.get("schema").strip()
start_date = dt.date.fromisoformat(dbutils.widgets.get("start_date").strip())
days = int(dbutils.widgets.get("days"))
inject_bad_rows = dbutils.widgets.get("inject_bad_rows") == "true"

identifier = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
if not identifier.fullmatch(catalog) or not identifier.fullmatch(schema):
    raise ValueError("Catalog and schema must be simple Unity Catalog identifiers.")
if not 1 <= days <= 366:
    raise ValueError("days must be between 1 and 366.")

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}`")
spark.sql(f"CREATE VOLUME IF NOT EXISTS `{catalog}`.`{schema}`.`raw_demand`")
landing = Path(f"/Volumes/{catalog}/{schema}/raw_demand/landing")
landing.mkdir(parents=True, exist_ok=True)

REGIONS = ["Netherlands", "Germany", "France"]
CATEGORIES = ["Fresh food", "Beverages", "Household"]


def day_records(day_index: int, day: dt.date) -> list[dict]:
    # One RNG per day keeps every file reproducible, whatever the requested range.
    rng = np.random.default_rng(day_index)
    records = []
    for region_index, category_index in product(range(len(REGIONS)), range(len(CATEGORIES))):
        base = 175.0 + region_index * 45 + category_index * 30
        promotion = int(day_index % 23 < 4)
        seasonal = 35 * math.sin(2 * math.pi * day_index / 7 + category_index)
        actual = max(10.0, base + seasonal + promotion * 55 + int(rng.integers(-21, 22)))
        baseline = max(10.0, base + int(rng.integers(-38, 39)))
        improved = max(10.0, actual + int(rng.integers(-16, 17)))
        records.append(
            {
                "date": day.isoformat(),
                "region": REGIONS[region_index],
                "category": CATEGORIES[category_index],
                "actual": round(actual, 1),
                "baseline": round(baseline, 1),
                "improved": round(improved, 1),
                "promotion": promotion,
            }
        )
    if inject_bad_rows and day_index % 37 == 5:
        # Deliberately invalid record so the Silver expectations have something to catch.
        records[0]["actual"] = -1.0
    return records


written = skipped = 0
for day_index in range(days):
    day = start_date + dt.timedelta(days=day_index)
    target = landing / f"demand_{day.isoformat()}.json"
    if target.exists():
        skipped += 1
        continue
    target.write_text("\n".join(json.dumps(r) for r in day_records(day_index, day)) + "\n")
    written += 1

print(f"Landing folder: {landing}")
print(f"Files written: {written}, already present: {skipped}")

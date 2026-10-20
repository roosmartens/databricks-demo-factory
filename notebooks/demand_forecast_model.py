# Databricks notebook source
# MAGIC %md
# MAGIC # Demand forecast: train, track, register, publish
# MAGIC
# MAGIC Run this after `demand_medallion`. It replaces the synthetic "improved" forecast with a trained model:
# MAGIC
# MAGIC 1. **Features** from Silver history: day of week, planned promotions, market, category, and demand lags of 7+ days (a planner forecasting next week only knows last week).
# MAGIC 2. **Backtest** on an expanding window: every scored day is predicted by a model that never saw it, so the reported error is out-of-sample.
# MAGIC 3. **MLflow** tracks parameters and backtest metrics, and registers the final model in Unity Catalog with a `champion` alias.
# MAGIC 4. **Gold** gets `gold_daily_forecast`, the same shape as `gold_daily_demand`, so the app and Genie read it without changes.
# MAGIC
# MAGIC The data is still synthetic, so the error reduction shows how the method works, not a result the customer should expect.

# COMMAND ----------

# MAGIC %pip install -q "mlflow>=3.1" "scikit-learn>=1.4"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import re

import mlflow
import numpy as np
import pandas as pd
from mlflow.models import infer_signature
from mlflow.tracking import MlflowClient
from pyspark.sql import functions as F
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

dbutils.widgets.text("catalog", "main", "Unity Catalog")
dbutils.widgets.text("schema", "demo_factory", "Schema")
dbutils.widgets.text("fold_days", "14", "Backtest fold length (days)")
dbutils.widgets.text("min_train_days", "35", "Minimum training history (days)")

catalog = dbutils.widgets.get("catalog").strip()
schema = dbutils.widgets.get("schema").strip()
fold_days = int(dbutils.widgets.get("fold_days"))
min_train_days = int(dbutils.widgets.get("min_train_days"))

identifier = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
if not identifier.fullmatch(catalog) or not identifier.fullmatch(schema):
    raise ValueError("Catalog and schema must be simple Unity Catalog identifiers.")
if fold_days < 1 or min_train_days < 7:
    raise ValueError("fold_days must be >= 1 and min_train_days must be >= 7.")

silver_table = f"{catalog}.{schema}.silver_demand"
forecast_table = f"{catalog}.{schema}.gold_daily_forecast"
model_name = f"{catalog}.{schema}.demand_forecast"

current_user = spark.sql("SELECT current_user()").first()[0]
mlflow.set_registry_uri("databricks-uc")
mlflow.set_experiment(f"/Users/{current_user}/demand-forecast")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Features and backtest
# MAGIC
# MAGIC The data is small (one row per day, market and category), so pandas and scikit-learn on the driver are enough. At customer scale the same features would be built in Spark and training distributed per series.

# COMMAND ----------

CATEGORICAL = ["region", "category", "day_of_week"]
NUMERIC = ["promotion", "lag_7", "lag_14", "mean_lag_7_13"]
FEATURES = CATEGORICAL + NUMERIC


def build_features(frame: pd.DataFrame) -> pd.DataFrame:
    """One row per date, market and category with only lags a weekly planner would know."""
    frame = frame.sort_values(["region", "category", "demand_date"]).copy()
    series = frame.groupby(["region", "category"])["actual_units"]
    frame["lag_7"] = series.shift(7)
    frame["lag_14"] = series.shift(14)
    frame["mean_lag_7_13"] = series.transform(lambda s: s.shift(7).rolling(7).mean())
    frame["day_of_week"] = pd.to_datetime(frame["demand_date"]).dt.day_name()
    frame["promotion"] = frame["promotion"].astype(float)
    return frame.dropna(subset=NUMERIC).reset_index(drop=True)


def make_model(params: dict) -> Pipeline:
    encode = ColumnTransformer(
        [("categorical", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)],
        remainder="passthrough",
    )
    return Pipeline([("encode", encode), ("regressor", GradientBoostingRegressor(**params))])


def wape(actual, prediction) -> float:
    denominator = float(np.abs(actual).sum())
    return 100 * float(np.abs(actual - prediction).sum()) / denominator if denominator else 0.0


def backtest(features: pd.DataFrame, params: dict, min_train_days: int, fold_days: int):
    """Expanding-window backtest: each fold is predicted by a model trained only on earlier days."""
    dates = np.sort(features["demand_date"].unique())
    if len(dates) <= min_train_days:
        raise ValueError("Not enough history for one backtest fold; lower min_train_days.")
    scored, folds = [], []
    for start in range(min_train_days, len(dates), fold_days):
        fold_dates = dates[start : start + fold_days]
        train = features[features["demand_date"] < fold_dates[0]]
        test = features[features["demand_date"].isin(fold_dates)].copy()
        model = make_model(params).fit(train[FEATURES], train["actual_units"])
        test["forecast_units"] = np.maximum(0.0, model.predict(test[FEATURES]))
        scored.append(test)
        folds.append({
            "fold_start": str(pd.Timestamp(fold_dates[0]).date()),
            "model_wape": wape(test["actual_units"], test["forecast_units"]),
            "baseline_wape": wape(test["actual_units"], test["baseline_units"]),
        })
    return pd.concat(scored, ignore_index=True), folds

# COMMAND ----------

history = (
    spark.read.table(silver_table)
    .select("demand_date", "region", "category", "actual_units", "baseline_units", "promotion")
    .toPandas()
)
features = build_features(history)
params = {"n_estimators": 300, "learning_rate": 0.05, "max_depth": 3, "random_state": 42}

with mlflow.start_run(run_name="weekly-demand-forecast") as run:
    scored, folds = backtest(features, params, min_train_days, fold_days)
    backtest_wape = wape(scored["actual_units"], scored["forecast_units"])
    baseline_wape = wape(scored["actual_units"], scored["baseline_units"])

    mlflow.log_params({**params, "fold_days": fold_days, "min_train_days": min_train_days,
                       "features": ",".join(FEATURES), "source_table": silver_table})
    mlflow.log_metrics({
        "backtest_wape": backtest_wape,
        "baseline_wape": baseline_wape,
        "error_reduction_pct": 100 * (baseline_wape - backtest_wape) / baseline_wape,
        "backtest_folds": len(folds),
    })
    mlflow.log_table(pd.DataFrame(folds), "backtest_folds.json")

    final_model = make_model(params).fit(features[FEATURES], features["actual_units"])
    example = features[FEATURES].head(5)
    model_info = mlflow.sklearn.log_model(
        sk_model=final_model,
        name="model",
        signature=infer_signature(example, final_model.predict(example)),
        input_example=example,
        registered_model_name=model_name,
        # Our own model, loaded only by us; skops rejects tree models without a trusted-types list.
        serialization_format="cloudpickle",
    )

model_version = model_info.registered_model_version
MlflowClient().set_registered_model_alias(model_name, "champion", model_version)
print(f"Backtest WAPE {backtest_wape:.1f}% vs current method {baseline_wape:.1f}% over {len(folds)} folds")
print(f"Registered {model_name} version {model_version} as @champion (run {run.info.run_id})")
display(pd.DataFrame(folds))

# COMMAND ----------
# MAGIC %md
# MAGIC ## Gold: daily demand with the out-of-sample forecast
# MAGIC
# MAGIC Same columns as `gold_daily_demand`, where `improved_units` now holds the backtest forecast. Only backtested days are included, so every error in the app and in Genie is out-of-sample.

# COMMAND ----------

gold = (
    spark.createDataFrame(
        scored[["demand_date", "region", "category", "actual_units", "baseline_units",
                "forecast_units", "promotion"]]
    )
    .withColumn("demand_date", F.to_date("demand_date"))
    .groupBy("demand_date", "region", "category")
    .agg(
        F.sum("actual_units").alias("actual_units"),
        F.sum("baseline_units").alias("baseline_units"),
        F.round(F.sum("forecast_units"), 1).alias("improved_units"),
        F.sum(F.abs(F.col("actual_units") - F.col("baseline_units"))).alias("baseline_abs_error"),
        F.sum(F.abs(F.col("actual_units") - F.col("forecast_units"))).alias("improved_abs_error"),
        F.sum(F.abs("actual_units")).alias("absolute_actual_units"),
        F.sum("promotion").cast("int").alias("promotion_days"),
    )
    .withColumn("model_version", F.lit(str(model_version)))
)
gold.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    forecast_table
)

column_comments = {
    "demand_date": "Calendar day of demand.",
    "region": "Market (country).",
    "category": "Product category.",
    "actual_units": "Units actually demanded.",
    "baseline_units": "Forecast from the current planning method.",
    "improved_units": "Out-of-sample forecast from the registered demand_forecast model.",
    "baseline_abs_error": "Absolute error of the current method, in units.",
    "improved_abs_error": "Absolute error of the model forecast, in units.",
    "absolute_actual_units": "Absolute actual units; WAPE denominator.",
    "promotion_days": "1 when a promotion ran that day, else 0.",
    "model_version": "Unity Catalog model version that produced improved_units.",
}
spark.sql(
    f"COMMENT ON TABLE {forecast_table} IS 'Daily demand per market and category with the "
    f"current-method forecast and an out-of-sample model forecast (synthetic demo data).'"
)
for column, comment in column_comments.items():
    spark.sql(f"ALTER TABLE {forecast_table} ALTER COLUMN {column} COMMENT '{comment}'")

print(f"Gold forecast table: {forecast_table}")
display(spark.table(forecast_table).orderBy(F.desc("demand_date")).limit(20))

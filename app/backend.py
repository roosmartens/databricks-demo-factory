import os
import re
from functools import lru_cache

from app.demos import active_demo

_SCHEMA_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$")
ACCURACY_NOTE = "Out-of-sample, last 14 days · WAPE"


class DataSourceError(RuntimeError):
    """Raised when the selected dashboard data source cannot be queried."""


def _dashboard_from_rows(rows: list[dict], source: str, forecast_note: str) -> dict:
    actual = sum(row["actual_units"] for row in rows)
    baseline_error = sum(row["baseline_abs_error"] for row in rows)
    improved_error = sum(row["improved_abs_error"] for row in rows)
    absolute_actual = sum(row["absolute_actual_units"] for row in rows)
    baseline_wape = 100 * baseline_error / absolute_actual if absolute_actual else 0.0
    improved_wape = 100 * improved_error / absolute_actual if absolute_actual else 0.0

    public_rows = [
        {
            "date": row["date"],
            "actual_units": round(row["actual_units"], 1),
            "baseline_units": round(row["baseline_units"], 1),
            "improved_units": round(row["improved_units"], 1),
            "promotion_days": int(row["promotion_days"]),
        }
        for row in rows
    ]
    return {
        "source": source,
        "forecast_note": forecast_note,
        "freshness": rows[-1]["date"] if rows else None,
        "actual_volume": actual,
        "baseline_wape": baseline_wape,
        "improved_wape": improved_wape,
        "error_reduction_pct": (
            100 * (baseline_wape - improved_wape) / baseline_wape
            if baseline_wape
            else 0.0
        ),
        "daily_rows": public_rows,
        "chart_data": {
            "dates": [row["date"] for row in public_rows],
            "actual": [row["actual_units"] for row in public_rows],
            "baseline": [row["baseline_units"] for row in public_rows],
            "improved": [row["improved_units"] for row in public_rows],
        },
    }


_SUM_COLUMNS = ("actual_units", "baseline_units", "improved_units", "baseline_abs_error",
                "improved_abs_error", "absolute_actual_units", "promotion_days")


def _selected_filters(demo, selection: dict) -> list[tuple[str, str]]:
    """(column, value) pairs for the chosen filters; unknown names or values are rejected."""
    chosen = []
    for name, (column, options) in demo.accuracy_filters.items():
        value = selection.get(name)
        if value:
            if value not in options:
                raise ValueError(f"Unknown {name} filter.")
            chosen.append((column, value))
    return chosen


def _load_demo_accuracy(demo, chosen: list[tuple[str, str]], promotions_only: bool) -> dict:
    frame = _offline_accuracy(demo.key)
    for column, value in chosen:
        frame = frame[frame[column] == value]
    if promotions_only:
        frame = frame[frame["promotion_days"] > 0]
    grouped = frame.groupby("demand_date", as_index=False)[list(_SUM_COLUMNS)].sum()
    rows = [{"date": row.pop("demand_date"), **row}
            for row in grouped.sort_values("demand_date").to_dict(orient="records")]
    return _dashboard_from_rows(rows, "Synthetic demo data", ACCURACY_NOTE)


def _fetch(warehouse_id: str, query: str, parameters: list | None = None) -> list:
    try:
        from databricks import sql
        from databricks.sdk.core import Config
        from databricks.sql.exc import Error as DatabricksSqlError
    except ImportError as exc:
        raise DataSourceError(
            "Install the Databricks app dependencies to use the workspace backend."
        ) from exc

    config = Config()
    try:
        connection = sql.connect(
            server_hostname=config.host,
            http_path=f"/sql/1.0/warehouses/{warehouse_id}",
            credentials_provider=lambda: config.authenticate,
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, parameters or [])
                columns = [column[0] for column in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            connection.close()
    except DatabricksSqlError as exc:
        raise DataSourceError("The Databricks SQL warehouse query failed.") from exc


def _load_databricks_accuracy(demo, chosen: list[tuple[str, str]], promotions_only: bool) -> dict:
    warehouse_id = os.environ.get("DATABRICKS_WAREHOUSE_ID", "").strip()
    schema = os.environ.get("DATABRICKS_COPILOT_SCHEMA", "").strip()
    if not warehouse_id:
        raise DataSourceError("DATABRICKS_WAREHOUSE_ID is not configured.")
    if not _SCHEMA_PATTERN.fullmatch(schema):
        raise DataSourceError("DATABRICKS_COPILOT_SCHEMA must be a catalog.schema name.")
    table = f"{schema}.{demo.accuracy_table}"

    where = []
    parameters = []
    for column, value in chosen:
        where.append(f"{column} = ?")  # column names come from the demo's own filter definition
        parameters.append(value)
    if promotions_only:
        where.append("promotion_days > 0")
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    query = f"""
        SELECT
            demand_date,
            SUM(actual_units) AS actual_units,
            SUM(baseline_units) AS baseline_units,
            SUM(improved_units) AS improved_units,
            SUM(baseline_abs_error) AS baseline_abs_error,
            SUM(improved_abs_error) AS improved_abs_error,
            SUM(absolute_actual_units) AS absolute_actual_units,
            SUM(promotion_days) AS promotion_days
        FROM {table}
        {where_clause}
        GROUP BY demand_date
        ORDER BY demand_date
    """
    result = _fetch(warehouse_id, query, parameters)
    rows = [
        {
            "date": row["demand_date"].strftime("%Y-%m-%d"),
            **{key: float(row[key] or 0) for key in (
                "actual_units", "baseline_units", "improved_units", "baseline_abs_error",
                "improved_abs_error", "absolute_actual_units")},
            "promotion_days": int(row["promotion_days"] or 0),
        }
        for row in result
    ]
    return _dashboard_from_rows(rows, "Databricks Gold table", ACCURACY_NOTE)


def load_accuracy(selection: dict, promotions_only: bool) -> dict:
    """Forecast accuracy for the active demo, sliced by its filters (e.g. store, category)."""
    demo = active_demo()
    chosen = _selected_filters(demo, selection)
    backend = os.environ.get("DATA_BACKEND", "demo").strip().lower()
    if backend == "demo":
        return _load_demo_accuracy(demo, chosen, promotions_only)
    if backend == "databricks":
        return _load_databricks_accuracy(demo, chosen, promotions_only)
    raise DataSourceError("DATA_BACKEND must be either 'demo' or 'databricks'.")


@lru_cache(maxsize=8)
def _offline_accuracy(demo_key: str):
    import pandas as pd
    return pd.DataFrame.from_records(active_demo().build_accuracy())


@lru_cache(maxsize=8)
def _offline_snapshot(demo_key: str) -> dict:
    snapshot = active_demo().build_snapshot()
    snapshot["source"] = "Synthetic demo data"
    return snapshot


def load_snapshot() -> dict:
    """The active demo's snapshot, from synthetic data or its Databricks Gold tables."""
    demo = active_demo()
    backend = os.environ.get("DATA_BACKEND", "demo").strip().lower()
    if backend == "demo":
        return _offline_snapshot(demo.key)
    if backend != "databricks":
        raise DataSourceError("DATA_BACKEND must be either 'demo' or 'databricks'.")

    warehouse_id = os.environ.get("DATABRICKS_WAREHOUSE_ID", "").strip()
    schema = os.environ.get("DATABRICKS_COPILOT_SCHEMA", "").strip()
    if not warehouse_id:
        raise DataSourceError("DATABRICKS_WAREHOUSE_ID is not configured.")
    if not _SCHEMA_PATTERN.fullmatch(schema):
        raise DataSourceError("DATABRICKS_COPILOT_SCHEMA must be a catalog.schema name.")
    try:
        snapshot = demo.read_databricks(_fetch, warehouse_id, schema)
    except LookupError as exc:
        raise DataSourceError(str(exc)) from exc
    snapshot["source"] = "Databricks Gold tables"
    return snapshot

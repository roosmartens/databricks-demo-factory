"""Build the Genie space request for the demand forecast Gold table.

Standard library only, so it runs anywhere the Databricks CLI does:

    python genie/build_space.py --catalog main --schema demo_factory \
        --warehouse-id WAREHOUSE_ID --parent-path /Workspace/Users/you@example.com/genie \
        > genie_space_request.json

IDs are derived from fixed keys, so rebuilding produces the same space definition.
"""
import argparse
import json
import re
import uuid

TABLE_NAME = "gold_daily_forecast"
T = TABLE_NAME  # Genie needs every column in snippets qualified with the table alias.

TITLE = "Demand forecast explorer"
DESCRIPTION = (
    "Ask about daily demand, forecast error and promotions by market and category. "
    "Compares the current planning method with the out-of-sample forecast from the "
    "registered demand_forecast model. Synthetic demo data."
)

GOLD_COLUMNS = (
    "absolute_actual_units",
    "actual_units",
    "baseline_abs_error",
    "baseline_units",
    "category",
    "demand_date",
    "improved_abs_error",
    "improved_units",
    "model_version",
    "promotion_days",
    "region",
)

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_NAMESPACE = uuid.UUID("6f1c2b1e-7d0a-4f4e-9a52-3c1d8e0b9a10")


def _id(key: str) -> str:
    return uuid.uuid5(_NAMESPACE, key).hex


def _sorted(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda item: item["id"])


def _column_configs() -> list[dict]:
    configs = [
        {"column_name": "region", "description": ["Market (country) where demand occurred."],
         "synonyms": ["market", "country"],
         "enable_format_assistance": True, "enable_entity_matching": True},
        {"column_name": "category", "description": ["Product category."],
         "synonyms": ["product group"],
         "enable_format_assistance": True, "enable_entity_matching": True},
        {"column_name": "demand_date", "description": ["Calendar day of demand."],
         "synonyms": ["date", "day"], "enable_format_assistance": True},
        {"column_name": "actual_units", "description": ["Units actually demanded."],
         "synonyms": ["demand", "sales", "actuals"]},
        {"column_name": "baseline_units", "description": ["Forecast from today's planning method."],
         "synonyms": ["current forecast", "baseline forecast", "planner forecast"]},
        {"column_name": "improved_units",
         "description": ["Out-of-sample forecast from the registered demand_forecast model."],
         "synonyms": ["model forecast", "new forecast", "ML forecast"]},
        {"column_name": "baseline_abs_error",
         "description": ["Absolute error of the current method in units. Sum it; never average it."]},
        {"column_name": "improved_abs_error",
         "description": ["Absolute error of the model forecast in units. Sum it; never average it."]},
        {"column_name": "absolute_actual_units",
         "description": ["Absolute actual units, the WAPE denominator."]},
        {"column_name": "promotion_days",
         "description": ["1 when a promotion ran that day for this market and category, else 0."],
         "synonyms": ["promo", "promotion"]},
        {"column_name": "model_version",
         "description": ["Unity Catalog model version that produced improved_units."]},
    ]
    return sorted(configs, key=lambda config: config["column_name"])


def _sql_snippets() -> dict:
    return {
        "measures": _sorted([
            {"id": _id("measure:baseline_wape"), "alias": "current_method_wape",
             "display_name": "Current method WAPE (%)",
             "sql": [f"100 * SUM({T}.baseline_abs_error) / SUM({T}.absolute_actual_units)"],
             "synonyms": ["current forecast error", "baseline error", "today's accuracy"]},
            {"id": _id("measure:model_wape"), "alias": "model_wape",
             "display_name": "Model WAPE (%)",
             "sql": [f"100 * SUM({T}.improved_abs_error) / SUM({T}.absolute_actual_units)"],
             "synonyms": ["model forecast error", "new forecast error"]},
            {"id": _id("measure:total_demand"), "alias": "total_demand_units",
             "display_name": "Total demand (units)",
             "sql": [f"SUM({T}.actual_units)"],
             "synonyms": ["total demand", "volume"]},
        ]),
        "filters": _sorted([
            {"id": _id("filter:promotion"), "display_name": "Promotion days",
             "sql": [f"{T}.promotion_days > 0"],
             "synonyms": ["during promotions", "promo days"]},
        ]),
    }


def _example_sqls(table: str) -> list[dict]:
    wape_columns = (
        f"ROUND(100 * SUM({T}.baseline_abs_error) / SUM({T}.absolute_actual_units), 1) AS current_method_wape_pct, "
        f"ROUND(100 * SUM({T}.improved_abs_error) / SUM({T}.absolute_actual_units), 1) AS model_wape_pct"
    )
    return _sorted([
        {"id": _id("example:wape_by_category_promo"),
         "question": ["How does forecast error compare by category during promotions?"],
         "sql": [f"SELECT {T}.category, {wape_columns} FROM {table} WHERE {T}.promotion_days > 0 "
                 f"GROUP BY {T}.category ORDER BY current_method_wape_pct DESC"],
         "usage_guidance": ["Use for comparing WAPE across a dimension, optionally filtered."]},
        {"id": _id("example:weekly_trend"),
         "question": ["What is the weekly forecast error trend?"],
         "sql": [f"SELECT DATE_TRUNC('WEEK', {T}.demand_date) AS week_start, {wape_columns} "
                 f"FROM {table} GROUP BY DATE_TRUNC('WEEK', {T}.demand_date) ORDER BY week_start"],
         "usage_guidance": ["Use for error over time; WAPE is recomputed per period from summed errors."]},
        {"id": _id("example:largest_misses"),
         "question": ["Which market and category had the largest forecast misses in the last two weeks?"],
         "sql": [f"SELECT {T}.region, {T}.category, ROUND(SUM({T}.baseline_abs_error)) AS current_method_miss_units, "
                 f"ROUND(SUM({T}.improved_abs_error)) AS model_miss_units FROM {table} "
                 f"WHERE {T}.demand_date > (SELECT DATE_SUB(MAX({T}.demand_date), 14) FROM {table}) "
                 f"GROUP BY {T}.region, {T}.category ORDER BY current_method_miss_units DESC LIMIT 5"],
         "usage_guidance": ["'Last N days' is relative to the latest date in the table, not today."]},
    ])


def _text_instructions() -> list[dict]:
    return [{"id": _id("text:global"), "content": [
        "## PURPOSE\n"
        "- Help demand planners and their managers compare today's forecast with the model forecast.\n\n"
        "## DISAMBIGUATION\n"
        "- 'Forecast error' or 'accuracy' means WAPE unless the user names another measure.\n"
        "- 'Last week' or 'last N days' is relative to the latest demand_date in the table.\n\n"
        "## DATA QUALITY NOTES\n"
        "- The data is synthetic demo data.\n\n"
        "## Instructions you must follow when providing summaries\n"
        "- Round percentages to one decimal place and state the date range used.\n"
        "- Say the data is synthetic whenever you quote an error reduction."
    ]}]


def _sample_questions() -> list[dict]:
    questions = [
        "Where is today's forecast missing most?",
        "How much does the model reduce forecast error during promotions?",
        "Show weekly forecast error for Germany",
        "Which category has the highest demand?",
    ]
    return _sorted([{"id": _id(f"sample:{q}"), "question": [q]} for q in questions])


def _benchmarks(table: str) -> dict:
    return {"questions": _sorted([
        {"id": _id("benchmark:overall_wape"),
         "question": ["What is the overall forecast error of the current method and the model?"],
         "answer": [{"format": "SQL", "content": [
             f"SELECT ROUND(100 * SUM({T}.baseline_abs_error) / SUM({T}.absolute_actual_units), 1) AS current_method_wape_pct, "
             f"ROUND(100 * SUM({T}.improved_abs_error) / SUM({T}.absolute_actual_units), 1) AS model_wape_pct FROM {table}"]}]},
        {"id": _id("benchmark:demand_by_region"),
         "question": ["Total demand by market"],
         "answer": [{"format": "SQL", "content": [
             f"SELECT {T}.region, SUM({T}.actual_units) AS total_demand_units FROM {table} "
             f"GROUP BY {T}.region ORDER BY total_demand_units DESC"]}]},
    ])}


def build_serialized_space(catalog: str, schema: str) -> dict:
    if not _IDENTIFIER.fullmatch(catalog) or not _IDENTIFIER.fullmatch(schema):
        raise ValueError("Catalog and schema must be simple Unity Catalog identifiers.")
    table = f"{catalog}.{schema}.{TABLE_NAME}"
    return {
        "version": 2,
        "config": {"sample_questions": _sample_questions()},
        "data_sources": {"tables": [{"identifier": table, "column_configs": _column_configs()}]},
        "instructions": {
            "example_question_sqls": _example_sqls(table),
            "sql_snippets": _sql_snippets(),
            "text_instructions": _text_instructions(),
        },
        "benchmarks": _benchmarks(table),
    }


def build_create_request(catalog: str, schema: str, warehouse_id: str, parent_path: str) -> dict:
    return {
        "warehouse_id": warehouse_id,
        "title": TITLE,
        "description": DESCRIPTION,
        "parent_path": parent_path,
        "serialized_space": json.dumps(build_serialized_space(catalog, schema)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--catalog", default="main")
    parser.add_argument("--schema", default="demo_factory")
    parser.add_argument("--warehouse-id", required=True)
    parser.add_argument("--parent-path", required=True)
    args = parser.parse_args()
    request = build_create_request(args.catalog, args.schema, args.warehouse_id, args.parent_path)
    print(json.dumps(request, indent=2))


if __name__ == "__main__":
    main()

"""Build the Genie space request for the Groenhof inventory copilot Gold tables.

Standard library only, so it runs anywhere the Databricks CLI does:

    python genie/build_space.py --catalog main --schema grocery_copilot \
        --warehouse-id WAREHOUSE_ID --parent-path /Workspace/Users/you@example.com/genie \
        > genie_space_request.json

The tables are written by notebooks/grocery_copilot_lakehouse.py. IDs are derived from
fixed keys, so rebuilding produces the same space definition.
"""
import argparse
import json
import re
import uuid

RISK = "gold_store_product_risk"
ACCURACY = "gold_forecast_accuracy"
TABLE_NAMES = (ACCURACY, RISK)  # Genie wants tables sorted by identifier

TITLE = "Inventory risk and forecast accuracy"
DESCRIPTION = (
    "Ask which store-products will run out or be wasted in the next 7 days, how much value is "
    "at risk, and how the demand forecast compares with today's planning method. "
    "Synthetic demo data for a fictional grocery chain."
)

RISK_COLUMNS = (
    "category", "days_of_cover", "days_to_expiry", "expected_shortfall_units", "forecast_7d_units",
    "forecast_sigma", "lost_sales_eur", "model_version", "next_delivery_date",
    "next_delivery_fill_pct", "next_delivery_units", "on_hand_units", "product_name",
    "promo_days", "sku", "status", "stockout_date", "stockout_probability", "store_code",
    "store_name", "supplier_id", "supplier_name", "value_at_risk_eur", "waste_eur", "waste_units",
)
ACCURACY_COLUMNS = (
    "absolute_actual_units", "actual_units", "baseline_abs_error", "baseline_units", "category",
    "demand_date", "improved_abs_error", "improved_units", "model_version", "product_name",
    "promotion_days", "sku", "store_code", "store_name",
)
GOLD_COLUMNS = tuple(sorted(set(RISK_COLUMNS) | set(ACCURACY_COLUMNS)))

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_NAMESPACE = uuid.UUID("6f1c2b1e-7d0a-4f4e-9a52-3c1d8e0b9a10")

# Genie needs every column in snippets qualified with the table name.
R, A = RISK, ACCURACY


def _id(key: str) -> str:
    return uuid.uuid5(_NAMESPACE, key).hex


def _sorted(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda item: item["id"])


def _risk_column_configs() -> list[dict]:
    configs = [
        {"column_name": "store_name", "description": ["Store the stock is in."],
         "synonyms": ["store", "shop", "location"],
         "enable_format_assistance": True, "enable_entity_matching": True},
        {"column_name": "store_code", "description": ["Short store code, for example AMS-01."]},
        {"column_name": "product_name", "description": ["Product name."],
         "synonyms": ["product", "item", "article"],
         "enable_format_assistance": True, "enable_entity_matching": True},
        {"column_name": "category", "description": ["Product category."],
         "synonyms": ["product group"],
         "enable_format_assistance": True, "enable_entity_matching": True},
        {"column_name": "supplier_name", "description": ["Supplier of the product."],
         "synonyms": ["supplier", "vendor"],
         "enable_format_assistance": True, "enable_entity_matching": True},
        {"column_name": "status",
         "description": ["Risk status for the next 7 days: stockout, waste, watch or ok."],
         "synonyms": ["risk", "risk status"],
         "enable_format_assistance": True, "enable_entity_matching": True},
        {"column_name": "stockout_probability",
         "description": ["Chance (0 to 1) the shelf runs empty within 7 days, given forecast uncertainty."],
         "synonyms": ["chance of stockout", "probability of running out"]},
        {"column_name": "stockout_date", "description": ["First day the shelf is expected to be empty."],
         "synonyms": ["runs out on"]},
        {"column_name": "waste_units",
         "description": ["Units on hand that will not sell before the oldest batch expires."],
         "synonyms": ["expected waste", "spoilage"]},
        {"column_name": "value_at_risk_eur",
         "description": ["Modelled exposure in euro: expected lost sales at price plus waste at cost. Not a savings figure."],
         "synonyms": ["value at risk", "exposure", "money at risk"]},
        {"column_name": "lost_sales_eur", "description": ["Expected lost sales at shelf price in euro."]},
        {"column_name": "waste_eur", "description": ["Expected waste at cost in euro."]},
        {"column_name": "expected_shortfall_units",
         "description": ["Expected units of demand that cannot be served within 7 days."],
         "synonyms": ["shortage", "shortfall"]},
        {"column_name": "on_hand_units", "description": ["Units on the shelf and in the back room at 05:30."],
         "synonyms": ["stock", "inventory"]},
        {"column_name": "days_to_expiry", "description": ["Days until the oldest batch expires."]},
        {"column_name": "days_of_cover", "description": ["Days the current stock lasts at forecast demand."]},
        {"column_name": "forecast_7d_units", "description": ["Forecast demand for the next 7 days in units."]},
        {"column_name": "promo_days", "description": ["Planned promotion days in the next 7 days."]},
        {"column_name": "next_delivery_units", "description": ["Confirmed units in the next delivery."]},
        {"column_name": "next_delivery_date", "description": ["Date of the next supplier delivery."]},
        {"column_name": "next_delivery_fill_pct",
         "description": ["Share of the ordered quantity the supplier has confirmed, in percent."],
         "synonyms": ["confirmed fill rate"]},
        {"column_name": "model_version", "description": ["Unity Catalog model version that produced the forecast."]},
    ]
    return sorted(configs, key=lambda config: config["column_name"])


def _accuracy_column_configs() -> list[dict]:
    configs = [
        {"column_name": "store_name", "description": ["Store where the sales happened."],
         "synonyms": ["store", "shop"],
         "enable_format_assistance": True, "enable_entity_matching": True},
        {"column_name": "category", "description": ["Product category."],
         "synonyms": ["product group"],
         "enable_format_assistance": True, "enable_entity_matching": True},
        {"column_name": "product_name", "description": ["Product name."],
         "synonyms": ["product", "item"],
         "enable_format_assistance": True, "enable_entity_matching": True},
        {"column_name": "demand_date", "description": ["Calendar day in the backtest holdout."],
         "synonyms": ["date", "day"], "enable_format_assistance": True},
        {"column_name": "actual_units", "description": ["Units actually sold."],
         "synonyms": ["sales", "demand", "actuals"]},
        {"column_name": "baseline_units",
         "description": ["Today's method: units sold on the same weekday last week."],
         "synonyms": ["current forecast", "planner forecast", "last week"]},
        {"column_name": "improved_units",
         "description": ["Out-of-sample forecast from the demand forecast model."],
         "synonyms": ["model forecast", "new forecast"]},
        {"column_name": "baseline_abs_error",
         "description": ["Absolute error of today's method in units. Sum it; never average it."]},
        {"column_name": "improved_abs_error",
         "description": ["Absolute error of the model in units. Sum it; never average it."]},
        {"column_name": "absolute_actual_units", "description": ["Absolute actual units, the WAPE denominator."]},
        {"column_name": "promotion_days",
         "description": ["1 when a promotion ran on this day for this store-product, else 0."],
         "synonyms": ["promo", "promotion"]},
        {"column_name": "model_version", "description": ["Unity Catalog model version that produced improved_units."]},
    ]
    return sorted(configs, key=lambda config: config["column_name"])


def _sql_snippets() -> dict:
    return {
        "measures": _sorted([
            {"id": _id("measure:value_at_risk"), "alias": "total_value_at_risk_eur",
             "display_name": "Value at risk (€)",
             "sql": [f"SUM({R}.value_at_risk_eur)"],
             "synonyms": ["exposure", "money at risk"]},
            {"id": _id("measure:stockouts"), "alias": "likely_stockouts",
             "display_name": "Likely stockouts",
             "sql": [f"COUNT_IF({R}.status = 'stockout')"],
             "synonyms": ["items running out", "empty shelves"]},
            {"id": _id("measure:waste_units"), "alias": "total_waste_units",
             "display_name": "Expected waste (units)",
             "sql": [f"SUM({R}.waste_units)"],
             "synonyms": ["spoilage", "write-offs"]},
            {"id": _id("measure:baseline_wape"), "alias": "current_method_wape",
             "display_name": "Today's method WAPE (%)",
             "sql": [f"100 * SUM({A}.baseline_abs_error) / SUM({A}.absolute_actual_units)"],
             "synonyms": ["current forecast error", "baseline error"]},
            {"id": _id("measure:model_wape"), "alias": "model_wape",
             "display_name": "Model WAPE (%)",
             "sql": [f"100 * SUM({A}.improved_abs_error) / SUM({A}.absolute_actual_units)"],
             "synonyms": ["model forecast error", "forecast error", "accuracy"]},
        ]),
        "filters": _sorted([
            {"id": _id("filter:at_risk"), "display_name": "At risk",
             "sql": [f"{R}.status <> 'ok'"],
             "synonyms": ["risky", "problem items"]},
            {"id": _id("filter:promotion"), "display_name": "Promotion days",
             "sql": [f"{A}.promotion_days > 0"],
             "synonyms": ["during promotions", "promo days"]},
        ]),
    }


def _example_sqls(risk: str, accuracy: str) -> list[dict]:
    wape = (
        f"ROUND(100 * SUM({A}.baseline_abs_error) / SUM({A}.absolute_actual_units), 1) AS current_method_wape_pct, "
        f"ROUND(100 * SUM({A}.improved_abs_error) / SUM({A}.absolute_actual_units), 1) AS model_wape_pct"
    )
    return _sorted([
        {"id": _id("example:top_risks"),
         "question": ["Which store-products have the most value at risk?"],
         "sql": [f"SELECT {R}.store_name, {R}.product_name, {R}.status, "
                 f"ROUND({R}.stockout_probability * 100) AS stockout_probability_pct, "
                 f"{R}.stockout_date, {R}.waste_units, ROUND({R}.value_at_risk_eur) AS value_at_risk_eur "
                 f"FROM {risk} WHERE {R}.status <> 'ok' ORDER BY {R}.value_at_risk_eur DESC LIMIT 10"],
         "usage_guidance": ["Use for ranking risks. Value at risk is modelled exposure, not savings."]},
        {"id": _id("example:waste_by_store"),
         "question": ["How much waste do we expect per store?"],
         "sql": [f"SELECT {R}.store_name, SUM({R}.waste_units) AS waste_units, ROUND(SUM({R}.waste_eur)) AS waste_eur "
                 f"FROM {risk} GROUP BY {R}.store_name ORDER BY waste_eur DESC"],
         "usage_guidance": ["Use for waste by any dimension (store, category, supplier)."]},
        {"id": _id("example:stockouts_by_supplier"),
         "question": ["Which suppliers are behind the likely stockouts?"],
         "sql": [f"SELECT {R}.supplier_name, COUNT(*) AS stockouts, "
                 f"ROUND(MIN({R}.next_delivery_fill_pct)) AS lowest_confirmed_fill_pct "
                 f"FROM {risk} WHERE {R}.status = 'stockout' GROUP BY {R}.supplier_name "
                 f"ORDER BY stockouts DESC"],
         "usage_guidance": ["Use to connect shortages to supplier confirmations."]},
        {"id": _id("example:wape_by_category_promo"),
         "question": ["How does forecast error compare by category during promotions?"],
         "sql": [f"SELECT {A}.category, {wape} FROM {accuracy} WHERE {A}.promotion_days > 0 "
                 f"GROUP BY {A}.category ORDER BY current_method_wape_pct DESC"],
         "usage_guidance": ["WAPE is recomputed from summed errors for any slice."]},
    ])


def _text_instructions() -> list[dict]:
    return [{"id": _id("text:global"), "content": [
        "## PURPOSE\n"
        "- Help category managers and store managers of a grocery chain see where stock will run out "
        "or be wasted in the next 7 days, and how reliable the forecast behind it is.\n\n"
        f"## TABLES\n- {RISK}: one row per store-product for the next 7 days.\n"
        f"- {ACCURACY}: out-of-sample backtest per store-product and day.\n\n"
        "## DISAMBIGUATION\n"
        "- 'At risk' means status is stockout or waste or watch, that is, status <> 'ok'.\n"
        "- 'Forecast error' or 'accuracy' means WAPE from the accuracy table unless the user names another measure.\n"
        "- 'Last N days' is relative to the latest demand_date in the accuracy table, not today.\n"
        "- stockout_probability is between 0 and 1; show it as a percentage.\n\n"
        "## DATA QUALITY NOTES\n"
        "- The data is synthetic demo data for a fictional chain.\n"
        "- value_at_risk_eur is modelled exposure (lost sales at price plus waste at cost), not savings.\n\n"
        "## Instructions you must follow when providing summaries\n"
        "- Round percentages to one decimal place and euros to whole euros.\n"
        "- Say the data is synthetic whenever you quote a forecast error or a euro amount."
    ]}]


def _sample_questions() -> list[dict]:
    questions = [
        "Which store-products have the most value at risk?",
        "Where will we run out of strawberries this week?",
        "How much waste do we expect per store?",
        "How much does the model reduce forecast error during promotions?",
    ]
    return _sorted([{"id": _id(f"sample:{q}"), "question": [q]} for q in questions])


def _benchmarks(risk: str, accuracy: str) -> dict:
    return {"questions": _sorted([
        {"id": _id("benchmark:overall_wape"),
         "question": ["What is the overall forecast error of today's method and the model?"],
         "answer": [{"format": "SQL", "content": [
             f"SELECT ROUND(100 * SUM({A}.baseline_abs_error) / SUM({A}.absolute_actual_units), 1) AS current_method_wape_pct, "
             f"ROUND(100 * SUM({A}.improved_abs_error) / SUM({A}.absolute_actual_units), 1) AS model_wape_pct FROM {accuracy}"]}]},
        {"id": _id("benchmark:value_at_risk_by_store"),
         "question": ["Total value at risk by store"],
         "answer": [{"format": "SQL", "content": [
             f"SELECT {R}.store_name, ROUND(SUM({R}.value_at_risk_eur)) AS total_value_at_risk_eur FROM {risk} "
             f"GROUP BY {R}.store_name ORDER BY total_value_at_risk_eur DESC"]}]},
    ])}


def build_serialized_space(catalog: str, schema: str) -> dict:
    if not _IDENTIFIER.fullmatch(catalog) or not _IDENTIFIER.fullmatch(schema):
        raise ValueError("Catalog and schema must be simple Unity Catalog identifiers.")
    risk, accuracy = (f"{catalog}.{schema}.{name}" for name in (RISK, ACCURACY))
    return {
        "version": 2,
        "config": {"sample_questions": _sample_questions()},
        "data_sources": {"tables": [
            {"identifier": accuracy, "column_configs": _accuracy_column_configs()},
            {"identifier": risk, "column_configs": _risk_column_configs()},
        ]},
        "instructions": {
            "example_question_sqls": _example_sqls(risk, accuracy),
            "sql_snippets": _sql_snippets(),
            "text_instructions": _text_instructions(),
        },
        "benchmarks": _benchmarks(risk, accuracy),
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
    parser.add_argument("--schema", default="grocery_copilot")
    parser.add_argument("--warehouse-id", required=True)
    parser.add_argument("--parent-path", required=True)
    args = parser.parse_args()
    request = build_create_request(args.catalog, args.schema, args.warehouse_id, args.parent_path)
    print(json.dumps(request, indent=2))


if __name__ == "__main__":
    main()

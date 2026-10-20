import csv
import datetime
import io
import logging
import os

from flask import Flask, Response, jsonify, render_template, request

from app import copilot as copilot_engine
from app.backend import DataSourceError, load_dashboard, load_snapshot
from app.data import CATEGORIES, REGIONS

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

ALL_MARKETS = "All markets"
ALL_CATEGORIES = "All categories"


@app.template_filter("day")
def day_label(value: str | None) -> str:
    """'2026-10-22' -> 'Thu 22 Oct'."""
    if not value:
        return "–"
    return datetime.date.fromisoformat(str(value)[:10]).strftime("%a %d %b").replace(" 0", " ")


app.add_template_filter(copilot_engine.short_name, "short")


def _filters():
    region = request.args.get("region", ALL_MARKETS)
    category = request.args.get("category", ALL_CATEGORIES)
    promotions_only = request.args.get("promotions") == "1"

    if region not in (ALL_MARKETS, *REGIONS):
        return None, ("Unknown market filter.", 400)
    if category not in (ALL_CATEGORIES, *CATEGORIES):
        return None, ("Unknown category filter.", 400)

    return (region, category, promotions_only), None


def _selected_item(snapshot: dict, key: str | None) -> dict | None:
    """``key`` is ``STORE_CODE:SKU``; defaults to the store-product with most value at risk."""
    items = snapshot["items"]
    if key:
        for item in items:
            if f"{item['store_code']}:{item['sku']}" == key:
                return item
        return None
    return items[0] if items else None


@app.get("/")
def copilot():
    try:
        snapshot = load_snapshot()
    except DataSourceError:
        app.logger.exception("Unable to load the copilot snapshot")
        return render_template(
            "error.html",
            message="Inventory data could not be loaded. Check the app's data source configuration and try again.",
        ), 503

    item = _selected_item(snapshot, request.args.get("item"))
    if item is None:
        return render_template("error.html", message="Unknown store or product."), 404
    key = (item["store_code"], item["sku"])
    projection = [row for row in snapshot["daily"] if (row["store_code"], row["sku"]) == key]
    at_risk = [i for i in snapshot["items"] if i["status"] != "ok"]
    return render_template(
        "copilot.html",
        snapshot=snapshot,
        item=item,
        briefing=copilot_engine.recommend(item),
        projection=projection,
        at_risk=at_risk,
        totals={
            "stockouts": sum(i["status"] == "stockout" for i in at_risk),
            "waste": sum(i["status"] == "waste" for i in at_risk),
            "value_at_risk": sum(i["value_at_risk_eur"] for i in at_risk),
            "actions": sum(len(i["actions"]) for i in at_risk),
        },
        passages=len(copilot_engine.load_passages()),
        workspace_label=(
            "Demo workspace"
            if snapshot["source"] == "Synthetic demo data"
            else "Databricks workspace"
        ),
    )


@app.post("/api/ask")
def ask():
    body = request.get_json(silent=True) or {}
    question = str(body.get("question", "")).strip()
    if not question:
        return jsonify({"error": "Ask a question first."}), 400
    try:
        snapshot = load_snapshot()
    except DataSourceError:
        app.logger.exception("Unable to load the copilot snapshot")
        return jsonify({"error": "Inventory data could not be loaded."}), 503
    item = _selected_item(snapshot, body.get("item")) if body.get("item") else None
    return jsonify(copilot_engine.ask(question, item))


@app.get("/accuracy")
def accuracy():
    filters, error = _filters()
    if error:
        return render_template("error.html", message=error[0]), error[1]

    region, category, promotions_only = filters
    try:
        dashboard = load_dashboard(region, category, promotions_only)
    except DataSourceError:
        app.logger.exception("Unable to load the demand dashboard")
        return render_template(
            "error.html",
            message="Demand data could not be loaded. Check the app's data source configuration and try again.",
        ), 503

    return render_template(
        "index.html",
        dashboard=dashboard,
        regions=REGIONS,
        categories=CATEGORIES,
        workspace_label=(
            "Demo workspace"
            if dashboard["source"] == "Synthetic demo data"
            else "Databricks workspace"
        ),
        selected_region=region,
        selected_category=category,
        promotions_only=promotions_only,
    )


@app.get("/story")
def story():
    return render_template("story.html")


@app.get("/export.csv")
def export_csv():
    filters, error = _filters()
    if error:
        return render_template("error.html", message=error[0]), error[1]

    region, category, promotions_only = filters
    try:
        dashboard = load_dashboard(region, category, promotions_only)
    except DataSourceError:
        app.logger.exception("Unable to export demand data")
        return render_template(
            "error.html",
            message="Demand data could not be loaded. Check the app's data source configuration and try again.",
        ), 503

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=(
            "date",
            "actual_units",
            "baseline_units",
            "improved_units",
            "promotion_days",
        ),
    )
    writer.writeheader()
    writer.writerows(dashboard["daily_rows"])
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": 'attachment; filename="demand-summary.csv"'},
    )


@app.get("/healthz")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("DATABRICKS_APP_PORT", "8000")),
        debug=os.environ.get("FLASK_DEBUG", "").lower() == "true",
    )

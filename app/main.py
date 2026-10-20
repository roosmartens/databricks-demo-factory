import csv
import datetime
import io
import logging
import os

from flask import Flask, Response, jsonify, render_template, request

from app import themes
from app.backend import DataSourceError, load_dashboard, load_snapshot
from app.data import CATEGORIES, REGIONS
from app.demos import UnknownItem, active_demo
from app.demos.grocery.copilot import short_name

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


app.add_template_filter(short_name, "short")


@app.context_processor
def demo_and_theme():
    """Every template gets the active demo and a theme: ?theme=, the picker cookie, DEMO_THEME, the demo default."""
    demo = active_demo()
    theme = themes.resolve(request.args.get("theme") or request.cookies.get("theme")
                           or os.environ.get("DEMO_THEME") or demo.theme)
    return {"demo": demo, "theme_name": theme, "themes": themes.THEMES,
            "theme_head": lambda surface: themes.head_tags(theme, surface)}


def _filters():
    region = request.args.get("region", ALL_MARKETS)
    category = request.args.get("category", ALL_CATEGORIES)
    promotions_only = request.args.get("promotions") == "1"

    if region not in (ALL_MARKETS, *REGIONS):
        return None, ("Unknown market filter.", 400)
    if category not in (ALL_CATEGORIES, *CATEGORIES):
        return None, ("Unknown category filter.", 400)

    return (region, category, promotions_only), None


@app.get("/")
def home():
    demo = active_demo()
    try:
        snapshot = load_snapshot()
    except DataSourceError:
        app.logger.exception("Unable to load the demo snapshot")
        return render_template(
            "error.html",
            message="Demo data could not be loaded. Check the app's data source configuration and try again.",
        ), 503
    try:
        context = demo.page_context(snapshot, request.args)
    except UnknownItem as exc:
        return render_template("error.html", message=str(exc)), 404
    return render_template(
        demo.page_template,
        snapshot=snapshot,
        workspace_label=(
            "Demo workspace"
            if snapshot["source"] == "Synthetic demo data"
            else "Databricks workspace"
        ),
        **context,
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
        app.logger.exception("Unable to load the demo snapshot")
        return jsonify({"error": "Demo data could not be loaded."}), 503
    try:
        return jsonify(active_demo().ask(question, snapshot, body.get("item") or None))
    except UnknownItem as exc:
        return jsonify({"error": str(exc)}), 404


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

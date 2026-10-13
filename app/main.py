import csv
import io
import logging
import os

from flask import Flask, Response, render_template, request

from app.backend import DataSourceError, load_dashboard
from app.data import CATEGORIES, REGIONS

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

ALL_MARKETS = "All markets"
ALL_CATEGORIES = "All categories"


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
def index():
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

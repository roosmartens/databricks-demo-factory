import csv
import datetime
import io
import json
import logging
import os

from flask import Flask, Response, jsonify, render_template, request

from app import themes
from app.backend import DataSourceError, load_accuracy, load_snapshot
from app.demos import UnknownItem, active_demo
from app.demos.grocery.copilot import short_name

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


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
            "genie_url": os.environ.get("GENIE_SPACE_URL", "").strip() or None,
            "theme_head": lambda surface: themes.head_tags(theme, surface)}


def _filters():
    """The accuracy filters from the query string, validated against the demo's options."""
    demo = active_demo()
    selection = {name: request.args.get(name, "") for name in demo.accuracy_filters}
    for name, (_, options) in demo.accuracy_filters.items():
        if selection[name] and selection[name] not in options:
            return None, (f"Unknown {name} filter.", 400)
    return (selection, request.args.get("promotions") == "1"), None


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
        return jsonify(active_demo().ask(question, snapshot, body.get("item") or None,
                                         body.get("approved") or None))
    except UnknownItem as exc:
        return jsonify({"error": str(exc)}), 404


@app.post("/api/briefing")
def briefing():
    body = request.get_json(silent=True) or {}
    try:
        snapshot = load_snapshot()
    except DataSourceError:
        app.logger.exception("Unable to load the demo snapshot")
        return jsonify({"error": "Demo data could not be loaded."}), 503
    try:
        return jsonify(active_demo().briefing(snapshot, body.get("item") or None,
                                              body.get("approved") or None))
    except UnknownItem as exc:
        return jsonify({"error": str(exc)}), 404


FEEDBACK_KINDS = {"ask", "briefing"}


@app.post("/api/feedback")
def feedback():
    """A thumbs up or down on an answer. Logged, and appended to FEEDBACK_LOG (JSONL) when set;
    in the pilot this row goes to a Delta table and the bad answers become evaluation questions."""
    body = request.get_json(silent=True) or {}
    vote, kind = body.get("vote"), body.get("kind")
    if vote not in ("up", "down") or kind not in FEEDBACK_KINDS:
        return jsonify({"error": "Send vote 'up' or 'down' and kind 'ask' or 'briefing'."}), 400
    row = {
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "demo": active_demo().key, "kind": kind, "vote": vote,
        "item": str(body.get("item", ""))[:40], "question": str(body.get("question", ""))[:500],
        "mode": str(body.get("mode", ""))[:20],
        "sources": [str(s)[:120] for s in (body.get("sources") or [])][:5],
    }
    app.logger.info("feedback %s", json.dumps(row))
    path = os.environ.get("FEEDBACK_LOG", "").strip()
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
    return jsonify({"ok": True})


@app.get("/accuracy")
def accuracy():
    filters, error = _filters()
    if error:
        return render_template("error.html", message=error[0]), error[1]

    selection, promotions_only = filters
    try:
        dashboard = load_accuracy(selection, promotions_only)
    except DataSourceError:
        app.logger.exception("Unable to load forecast accuracy")
        return render_template(
            "error.html",
            message="Forecast accuracy could not be loaded. Check the app's data source configuration and try again.",
        ), 503

    return render_template(
        "accuracy.html",
        dashboard=dashboard,
        filters={name: options for name, (_, options) in active_demo().accuracy_filters.items()},
        selection=selection,
        promotions_only=promotions_only,
        workspace_label=(
            "Demo workspace"
            if dashboard["source"] == "Synthetic demo data"
            else "Databricks workspace"
        ),
    )


@app.get("/story")
def story():
    return render_template("story.html")


@app.get("/export.csv")
def export_csv():
    filters, error = _filters()
    if error:
        return render_template("error.html", message=error[0]), error[1]

    selection, promotions_only = filters
    try:
        dashboard = load_accuracy(selection, promotions_only)
    except DataSourceError:
        app.logger.exception("Unable to export forecast accuracy")
        return render_template(
            "error.html",
            message="Forecast accuracy could not be loaded. Check the app's data source configuration and try again.",
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
        headers={"Content-Disposition": 'attachment; filename="forecast-accuracy.csv"'},
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

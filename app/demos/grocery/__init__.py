"""Grocery Inventory Copilot: the worked example for the demo factory.

Groenhof Markets (fictional) runs out of fresh products in one store while another store
throws the same products away. ``engine`` unifies three sources and predicts stockouts and
waste; ``copilot`` explains them from supplier knowledge; the page and deck live in
``app/templates/demos/grocery/``.
"""
import json

from flask import url_for

from app.demos import Demo, UnknownItem
from app.demos.grocery import copilot, engine


def _approved(snapshot: dict, raw) -> list[str]:
    """Simulated approvals travel in the URL (``approved=id1,id2``), so the app stays stateless."""
    ids = [i for i in (raw.split(",") if isinstance(raw, str) else raw or []) if i]
    unknown = set(ids) - engine.action_ids(snapshot)
    if unknown:
        raise UnknownItem("Unknown action.")
    return list(dict.fromkeys(ids))


def _label(snapshot: dict, action_id: str) -> str:
    for item in snapshot["items"]:
        for a in item["actions"]:
            if a.get("id") == action_id:
                if a["kind"] == "alt_supplier":
                    return f"Alternative-supplier order, {a['cases']} cases"
                return (f"Transfer {a['units']} × {item['product_name']}: "
                        f"{a['from'] if 'from' in a else item['store_name']} → "
                        f"{a['to'] if 'to' in a else item['store_name']}")
    return action_id


def _view(snapshot: dict, approved: list[str]) -> dict:
    return engine.apply_actions(snapshot, set(approved)) if approved else snapshot


def _selected(snapshot: dict, key: str | None) -> dict:
    """``key`` is ``STORE_CODE:SKU``; defaults to the store-product with most value at risk."""
    items = snapshot["items"]
    if not key:
        if not items:
            raise UnknownItem("The snapshot is empty.")
        return items[0]
    for item in items:
        if f"{item['store_code']}:{item['sku']}" == key:
            return item
    raise UnknownItem("Unknown store or product.")


def page_context(snapshot: dict, args: dict) -> dict:
    approved = _approved(snapshot, args.get("approved"))
    view = _view(snapshot, approved)
    item = _selected(view, args.get("item"))
    key = (item["store_code"], item["sku"])
    item_key = f"{item['store_code']}:{item['sku']}"
    at_risk = [i for i in view["items"] if i["status"] != "ok"]
    briefing = copilot.recommend(item)
    for step in briefing["steps"]:
        if step["approvable"]:
            toggled = (set(approved) - {step["id"]}) if step["approved"] else (set(approved) | {step["id"]})
            step["toggle_url"] = url_for("home", item=item_key, approved=",".join(sorted(toggled)) or None)
    return {
        "item": item,
        "briefing": briefing,
        "projection": [r for r in view["daily"] if (r["store_code"], r["sku"]) == key],
        "at_risk": at_risk,
        "totals": {
            "stockouts": sum(i["status"] == "stockout" for i in at_risk),
            "waste": sum(i["status"] == "waste" for i in at_risk),
            "value_at_risk": sum(i["value_at_risk_eur"] for i in at_risk),
            "actions": sum(len(i["actions"]) for i in at_risk),
        },
        "passages": len(copilot.load_passages()),
        "approved": approved,
        "approved_param": ",".join(approved) or None,
        "approved_labels": [_label(snapshot, a) for a in approved],
        "impact": view.get("impact"),
        "reset_url": url_for("home", item=item_key),
    }


def ask(question: str, snapshot: dict, key: str | None, approved: str | None = None) -> dict:
    view = _view(snapshot, _approved(snapshot, approved))
    item = _selected(view, key) if key else None
    return copilot.ask(question, item)


def briefing(snapshot: dict, key: str | None, approved: str | None = None) -> dict:
    """One live generated briefing for the selected store-product."""
    view = _view(snapshot, _approved(snapshot, approved))
    return copilot.ai_briefing(_selected(view, key))


def read_databricks(fetch, warehouse_id: str, schema: str) -> dict:
    """Read the Gold tables written by notebooks/grocery_copilot_lakehouse.py."""
    items = fetch(warehouse_id, f"SELECT * FROM {schema}.gold_store_product_risk "
                                "ORDER BY value_at_risk_eur DESC")
    daily = fetch(warehouse_id, f"SELECT * FROM {schema}.gold_store_product_projection "
                                "ORDER BY store_code, sku, date")
    meta = fetch(warehouse_id, f"SELECT * FROM {schema}.gold_copilot_run LIMIT 1")
    if not items or not meta:
        raise LookupError("The copilot Gold tables are empty; run the notebook first.")
    for item in items:
        item["actions"] = json.loads(item.pop("actions_json") or "[]")
    for row in daily:
        row["date"] = str(row["date"])[:10]
    return {"as_of": str(meta[0]["as_of"])[:10], "items": items, "daily": daily,
            "quality": json.loads(meta[0]["quality_json"]),
            "backtest": json.loads(meta[0]["backtest_json"])}


def build_accuracy() -> list[dict]:
    return engine.accuracy_rows(engine.unify(engine.make_sources())["sales"])


DEMO = Demo(
    key="grocery",
    title="Inventory copilot",
    brand="groenhof",
    theme="fresh-market",
    page_template="demos/grocery/copilot.html",
    deck_template="demos/grocery/deck.html",
    build_snapshot=engine.build_snapshot,
    read_databricks=read_databricks,
    page_context=page_context,
    ask=ask,
    briefing=briefing,
    build_accuracy=build_accuracy,
    accuracy_table="gold_forecast_accuracy",
    accuracy_filters={
        "store": ("store_name", tuple(engine.STORES["store_name"])),
        "category": ("category", tuple(engine.PRODUCTS["category"].unique())),
    },
)

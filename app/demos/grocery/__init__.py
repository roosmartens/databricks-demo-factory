"""Grocery Inventory Copilot: the worked example for the demo factory.

Groenhof Markets (fictional) runs out of fresh products in one store while another store
throws the same products away. ``engine`` unifies three sources and predicts stockouts and
waste; ``copilot`` explains them from supplier knowledge; the page and deck live in
``app/templates/demos/grocery/``.
"""
import json

from app.demos import Demo, UnknownItem
from app.demos.grocery import copilot, engine


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
    item = _selected(snapshot, args.get("item"))
    key = (item["store_code"], item["sku"])
    at_risk = [i for i in snapshot["items"] if i["status"] != "ok"]
    return {
        "item": item,
        "briefing": copilot.recommend(item),
        "projection": [r for r in snapshot["daily"] if (r["store_code"], r["sku"]) == key],
        "at_risk": at_risk,
        "totals": {
            "stockouts": sum(i["status"] == "stockout" for i in at_risk),
            "waste": sum(i["status"] == "waste" for i in at_risk),
            "value_at_risk": sum(i["value_at_risk_eur"] for i in at_risk),
            "actions": sum(len(i["actions"]) for i in at_risk),
        },
        "passages": len(copilot.load_passages()),
    }


def ask(question: str, snapshot: dict, key: str | None) -> dict:
    item = _selected(snapshot, key) if key else None
    return copilot.ask(question, item)


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
)

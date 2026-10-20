"""Replenishment copilot for the grocery demo: briefings and answers grounded in the snapshot.

Uses the shared retrieval in ``app.rag`` over this demo's ``knowledge/`` documents.
"""
import datetime as dt
import json
from pathlib import Path

from app import rag

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

SYSTEM_PROMPT = (
    "You are the replenishment copilot for Groenhof Markets, a Dutch grocery chain. "
    "Answer store and category managers in plain business language. Use only the facts in the "
    "risk snapshot and the numbered passages. Cite passages as [1], [2]. Recommend concrete "
    "actions with quantities and deadlines. If the context does not answer the question, say so."
)


def retrieve(query: str, k: int = 3, context: str = "") -> list[dict]:
    return rag.retrieve(KNOWLEDGE_DIR, query, k=k, context=context)


def load_passages() -> tuple[dict, ...]:
    return rag.load_passages(KNOWLEDGE_DIR)


def short_name(product_name: str) -> str:
    """'Whole milk 1L' -> 'whole milk', for questions in plain language."""
    return " ".join(w for w in product_name.lower().split() if not any(c.isdigit() for c in w))


def _fmt_day(date: str | None) -> str:
    if not date:
        return "this week"
    return dt.date.fromisoformat(date).strftime("%A %d %B").replace(" 0", " ")


def _pct(probability: float) -> str:
    return "over 95%" if probability >= 0.95 else f"{round(100 * probability)}%"


def situation(item: dict) -> str:
    """One-sentence summary of a store-product, from the Gold snapshot."""
    where = f"{item['store_name']}, {item['product_name']}"
    if item["status"] == "stockout":
        line = (f"{where}: likely to run out on {_fmt_day(item['stockout_date'])} "
                f"({_pct(item['stockout_probability'])} chance this week). "
                f"{item['on_hand_units']:.0f} units on hand cover {item['days_of_cover']} days")
        if item["promo_days"]:
            line += f", while a promotion runs {item['promo_days']} of the next 7 days"
        if item["next_delivery_fill_pct"] is not None and item["next_delivery_fill_pct"] < 100:
            line += (f", and {item['supplier_name']} confirmed only "
                     f"{item['next_delivery_fill_pct']}% of the next order")
        return line + "."
    if item["status"] == "waste":
        return (f"{where}: about {item['waste_units']:.0f} of {item['on_hand_units']:.0f} units will "
                f"not sell before the oldest batch expires in {item['days_to_expiry']} days "
                f"(about {item['waste_eur']:.0f} euro at cost).")
    if item["status"] == "watch":
        return f"{where}: worth watching, {_pct(item['stockout_probability'])} stockout risk."
    return f"{where}: no action needed, stock covers forecast demand."


def _context_block(item: dict, passages: list[dict]) -> str:
    facts = {k: item[k] for k in (
        "store_name", "product_name", "supplier_name", "status", "stockout_probability",
        "stockout_date", "on_hand_units", "days_of_cover", "forecast_7d_units", "promo_days",
        "next_delivery_date", "next_delivery_fill_pct", "waste_units", "value_at_risk_eur")}
    numbered = "\n".join(f"[{i}] {p['title']} / {p['section']}: {p['text']}"
                         for i, p in enumerate(passages, start=1))
    actions = "\n".join(f"- {a['text']}" for a in item.get("actions", []))
    return (f"Risk snapshot (from the Gold table and the forecast model):\n{json.dumps(facts)}\n\n"
            f"Candidate actions from the replenishment rules:\n{actions or '- none'}\n\n"
            f"Passages:\n{numbered}")


def _call_llm(question: str, item: dict, passages: list[dict]) -> str | None:
    return rag.call_llm(SYSTEM_PROMPT, _context_block(item, passages), question)


def recommend(item: dict) -> dict:
    """The copilot's briefing for one store-product: situation, actions, and their sources."""
    passages, steps = [], []
    for action in item.get("actions", []):
        hits = retrieve(action["query"], k=1)
        ref = None
        if hits:
            key = (hits[0]["doc"], hits[0]["section"])
            known = [(p["doc"], p["section"]) for p in passages]
            if key not in known:
                passages.append(hits[0])
                known.append(key)
            ref = known.index(key) + 1
        steps.append({"text": action["text"], "kind": action["kind"], "ref": ref})
    # The supplier's own latest news explains a shortage best, so keep only its passages.
    supplier_word = item["supplier_name"].split()[0].lower()
    why = [p for p in retrieve(f"{item['supplier_name']} update yield confirming volumes", k=5)
           if supplier_word in f"{p['section']} {p['text']}".lower()][:1]
    if why and item["status"] in ("stockout", "watch"):
        key = (why[0]["doc"], why[0]["section"])
        if key not in [(p["doc"], p["section"]) for p in passages]:
            passages.insert(0, why[0])
            for step in steps:
                step["ref"] = step["ref"] + 1 if step["ref"] else None
    question = "What should we do about this, and why?"
    llm = _call_llm(question, item, passages)
    return {"situation": situation(item), "steps": steps, "sources": passages,
            "why": (rag.first_sentences(why[0]["text"])
                    if why and item["status"] in ("stockout", "watch") else None),
            "llm_answer": llm, "mode": "llm" if llm else "offline"}


def ask(question: str, item: dict | None) -> dict:
    """Free-text question, grounded in the selected store-product when there is one."""
    question = question.strip()[:500]
    context = short_name(item["product_name"]) if item else ""
    passages = retrieve(question, k=3, context=context)
    llm = _call_llm(question, item, passages) if item else None
    if llm:
        return {"answer": llm, "sources": passages, "mode": "llm"}
    if not passages:
        return {"answer": "I could not find this in the supplier knowledge base. Try asking about "
                          "a supplier, a substitute, markdowns or transfers.",
                "sources": [], "mode": "offline"}
    lines = [f"{rag.first_sentences(p['text'])} [{i}]" for i, p in enumerate(passages, start=1)]
    lead = f"{situation(item)}\n\n" if item else ""
    return {"answer": lead + "\n\n".join(lines), "sources": passages, "mode": "offline"}

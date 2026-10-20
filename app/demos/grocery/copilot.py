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


def _context_block(item: dict, passages: list[dict], steps: list[dict] | None = None) -> str:
    facts = {k: item[k] for k in (
        "store_name", "product_name", "supplier_name", "status",
        "stockout_date", "on_hand_units", "days_of_cover", "forecast_7d_units", "promo_days",
        "next_delivery_date", "next_delivery_fill_pct", "waste_units", "value_at_risk_eur")}
    facts["stockout_probability_pct"] = round(100 * item["stockout_probability"])
    numbered = "\n".join(f"[{i}] {p['title']} / {p['section']}: {p['text']}"
                         for i, p in enumerate(passages, start=1))
    if steps is None:
        steps = [{"text": a["text"], "ref": None} for a in item.get("actions", [])]
    actions = "\n".join(f"- {s['text']}" + (f" (policy in passage [{s['ref']}])" if s["ref"] else "")
                        for s in steps)
    return (f"Risk snapshot (from the Gold table and the forecast model):\n{json.dumps(facts)}\n\n"
            f"Candidate actions from the replenishment rules:\n{actions or '- none'}\n\n"
            f"Passages:\n{numbered}")


BRIEFING_QUESTION = (
    "Write a briefing for the store manager in at most 110 words: one sentence on what is "
    "happening and why, then up to three short action lines using the candidate actions with "
    "their quantities and the passage number shown next to each, then one line on what the data "
    "cannot tell us. Say which quantity applies to this store. Copy figures exactly as "
    "given and never calculate new ones. Cite the passage behind every claim about suppliers "
    "or policy as [1], [2]."
)


def ai_briefing(item: dict) -> dict:
    """One generated briefing, grounded in the model output and the cited passages.

    The answer is only returned as ``llm`` when it cites real passages and uses no figure
    that was not in the context; otherwise the caller gets the deterministic briefing.
    """
    base = recommend(item)
    context = _context_block(item, base["sources"], base["steps"])
    answer = rag.call_llm(SYSTEM_PROMPT, context, BRIEFING_QUESTION)
    if not answer:
        reason = "no endpoint configured" if not rag.llm_endpoint() else "endpoint call failed"
        return {"mode": "offline", "reason": reason, "sources": base["sources"],
                "answer": None, "endpoint": rag.llm_endpoint() or None}
    checks = rag.check_grounding(answer, len(base["sources"]), context)
    if not checks["passed"]:
        return {"mode": "offline", "reason": "guardrail: " + (
            f"invented figures {checks['invented_numbers']}" if checks["invented_numbers"]
            else "missing or invalid citations"),
                "sources": base["sources"], "answer": None, "checks": checks,
                "endpoint": rag.llm_endpoint()}
    return {"mode": "llm", "answer": answer, "sources": base["sources"], "checks": checks,
            "endpoint": rag.llm_endpoint()}


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
        steps.append({"text": action["text"], "kind": action["kind"], "ref": ref,
                      "id": action.get("id"), "approvable": action.get("approvable", False),
                      "approved": action.get("approved", False),
                      "cost_eur": action.get("cost_eur")})
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
    return {"situation": situation(item), "steps": steps, "sources": passages,
            "why": (rag.first_sentences(why[0]["text"])
                    if why and item["status"] in ("stockout", "watch") else None),
            "mode": "offline"}


def ask(question: str, item: dict | None) -> dict:
    """Free-text question, grounded in the selected store-product when there is one."""
    question = question.strip()[:500]
    context = short_name(item["product_name"]) if item else ""
    passages = retrieve(question, k=3, context=context)
    context = _context_block(item, passages) if item else ""
    llm = rag.call_llm(SYSTEM_PROMPT, context, question) if item else None
    if llm and rag.check_grounding(llm, len(passages), context)["passed"]:
        return {"answer": llm, "sources": passages, "mode": "llm"}
    if not passages:
        return {"answer": "I could not find this in the supplier knowledge base. Try asking about "
                          "a supplier, a substitute, markdowns or transfers.",
                "sources": [], "mode": "offline"}
    lines = [f"{rag.first_sentences(p['text'])} [{i}]" for i, p in enumerate(passages, start=1)]
    lead = f"{situation(item)}\n\n" if item else ""
    return {"answer": lead + "\n\n".join(lines), "sources": passages, "mode": "offline"}

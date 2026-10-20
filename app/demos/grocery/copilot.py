"""Replenishment copilot for the grocery demo: briefings and answers grounded in the snapshot.

Uses the shared retrieval in ``app.rag`` over this demo's ``knowledge/`` documents.
"""
import datetime as dt
import json
import re
from pathlib import Path

from app import rag

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

SYSTEM_PROMPT = (
    "You are the replenishment copilot for Groenhof Markets, a Dutch grocery chain. "
    "Answer store and category managers in plain business language. Use only the facts in the "
    "risk snapshot and the numbered passages. Cite passages as [1], [2]. Recommend concrete "
    "actions with quantities and deadlines. If the context does not answer the question, say so."
)


def retrieve(query: str, k: int = 3, context: str = "", context_weight: float = 0.5) -> list[dict]:
    return rag.retrieve(KNOWLEDGE_DIR, query, k=k, context=context, context_weight=context_weight)


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


# What the numbers cannot tell the store manager, by situation. Saying it out loud is what
# makes people trust the rest of the briefing.
UNKNOWNS = {
    "stockout": "The forecast cannot see a competitor's promotion or tomorrow's weather; "
                "check the shelf at 10:00 before ordering more.",
    "watch": "The risk is moderate; confirm the next delivery with the supplier before acting.",
    "waste": "The model assumes oldest-first selling; if the batch is spread over several "
             "displays, waste may be higher.",
    "ok": "Nothing to do; the forecast covers this week.",
}


def template_briefing(item: dict, base: dict | None = None) -> str:
    """The 05:30 briefing without a language model: what, why, do, and what we don't know.

    Same structure the LLM is asked for, built only from the snapshot and cited passages, so
    it is always available and always correct; the LLM only makes it read more naturally.
    """
    base = base or recommend(item)
    lines = [situation(item)]
    if base.get("why"):
        lines.append(f"Why: {base['why']} [1]")
    for step in base["steps"][:3]:
        lines.append(f"Do: {step['text']}" + (f" [{step['ref']}]" if step["ref"] else ""))
    lines.append(f"Watch out: {UNKNOWNS[item['status']]}")
    return "\n\n".join(lines)


def ai_briefing(item: dict) -> dict:
    """The briefing for one store-product: written by the LLM when it passes the guardrails.

    The answer is only returned as ``llm`` when it cites real passages and uses no figure
    that was not in the context; otherwise the caller gets the template briefing and the reason.
    """
    base = recommend(item)
    fallback = {"answer": template_briefing(item, base), "sources": base["sources"],
                "endpoint": rag.llm_endpoint() or None}
    context = _context_block(item, base["sources"], base["steps"])
    answer = rag.call_llm(SYSTEM_PROMPT, context, BRIEFING_QUESTION)
    if not answer:
        reason = "no model endpoint connected" if not rag.llm_endpoint() else "endpoint call failed"
        return fallback | {"mode": "template", "reason": reason}
    checks = rag.check_grounding(answer, len(base["sources"]), context)
    if not checks["passed"]:
        return fallback | {"mode": "template", "checks": checks, "reason": "guardrail: " + (
            f"the model used figures not in the data ({', '.join(checks['invented_numbers'])})"
            if checks["invented_numbers"] else "the model did not cite its sources")}
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


# Questions about counts, totals and trends across stores are Genie's job (text-to-SQL over the
# Gold tables), not the copilot's (answers from documents for one decision).
_NUMBERS_QUESTION = re.compile(
    r"\b(how many|how much|total|sum|average|trend|compare|ranking|rank|top \d+|last (week|month|"
    r"quarter|year)|per store|by store|by category|which stores|percentage of)\b", re.I)


# "Why is this happening / what should I do" is the briefing's job for the selected item.
_ABOUT_THIS_DECISION = re.compile(
    r"^\s*(why\b|what should (i|we) do|what do (i|we) do|what to do|summari[sz]e|explain this)", re.I)


# Keyword search does not know that "instead" means "substitute". Offline, a short domain
# glossary bridges that; on Databricks, Vector Search embeddings do it without a list.
_GLOSSARY = (
    (re.compile(r"\b(instead|replace|replacement|swap|substitut\w*)\b", re.I), "substitutes for"),
    (re.compile(r"\b(another|other|alternative|backup|second) suppl", re.I), "approved alternative"),
    (re.compile(r"\b(happened before|last time|before|learn\w*|incident)\b", re.I),
     "lessons learned week root cause"),
    (re.compile(r"\b(throw away|waste|bin|discount|mark ?down)\b", re.I), "markdown ladder"),
)


def expand(question: str) -> str:
    return " ".join([question] + [terms for pattern, terms in _GLOSSARY if pattern.search(question)])


def is_numbers_question(question: str) -> bool:
    return bool(_NUMBERS_QUESTION.search(question))


_PRODUCT_WORDS = ("strawberr", "avocado", "banana", "milk", "yoghurt", "dairy", "sourdough",
                  "bakery", "bread", "chicken", "meat", "tomato", "lettuce", "produce")


def _names_product(section: str) -> bool:
    return any(w in section.lower() for w in _PRODUCT_WORDS)


def _mentions_item(item: dict | None):
    """Section title matcher for the selected product, its category and its supplier."""
    if not item:
        return lambda section: False
    words = [w for w in short_name(item["product_name"]).split() if len(w) > 3]
    words += [item["category"].lower()]
    words += [w for w in str(item.get("supplier_name") or "").lower().split() if len(w) > 3][:1]
    stems = [w.rstrip("s").rstrip("ie") if w.endswith("ies") else w.rstrip("s") for w in words]
    return lambda section: any(stem in section.lower() for stem in stems)


def ask(question: str, item: dict | None) -> dict:
    """Follow-up question about the selected decision, answered from supplier knowledge."""
    question = question.strip()[:500]
    if is_numbers_question(question):
        return {"mode": "route", "sources": [],
                "answer": "That is a numbers question, so Genie answers it with SQL on the same "
                          "Gold tables. I answer from the supplier documents."}
    if item and _ABOUT_THIS_DECISION.search(question):
        base = recommend(item)
        return {"answer": template_briefing(item, base), "sources": base["sources"],
                "mode": "briefing"}
    # Relevance is judged on the question alone, so the selected product cannot drag in
    # passages the question is not about. The product then decides the order, and a
    # section about a different product is dropped (no Huelva strawberries for bread).
    query = expand(question)
    ranked = retrieve(query, k=8)
    top = ranked[0]["score"] if ranked else 0
    mine = _mentions_item(item)
    passages = [p for p in ranked
                if p["score"] >= 0.6 * top or (mine(p["section"]) and p["score"] >= 0.3 * top)]
    if item:
        passages = [p for p in passages if mine(p["section"]) or not _names_product(p["section"])]
        # Near-ties go to the selected product: "substitutes?" means substitutes for this one.
        passages.sort(key=lambda p: (not (mine(p["section"]) and p["score"] >= 0.75 * top), -p["score"]))
    passages = passages[:3]
    prompt_context = _context_block(item, passages) if item else ""
    llm = rag.call_llm(SYSTEM_PROMPT, prompt_context, question) if item and passages else None
    if llm and rag.check_grounding(llm, len(passages), prompt_context)["passed"]:
        return {"answer": llm, "sources": passages, "mode": "llm"}
    if not passages:
        about = f" for {short_name(item['product_name'])}" if item else ""
        return {"answer": f"The supplier documents do not cover this{about}, so I will not guess.",
                "sources": [], "mode": "offline"}
    lines = [f"{rag.best_sentences(p['text'], query)} [{i}]"
             for i, p in enumerate(passages, start=1)]
    return {"answer": "\n\n".join(lines), "sources": passages, "mode": "offline"}

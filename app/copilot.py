"""Replenishment copilot: retrieval over supplier knowledge, grounded in the risk snapshot.

Local mode retrieves passages with BM25 from ``app/knowledge`` and assembles the answer from
them, so the demo runs offline and every sentence can be traced to a source. On Databricks,
set ``COPILOT_VECTOR_INDEX`` (Mosaic AI Vector Search) and ``COPILOT_SERVING_ENDPOINT`` (a chat
model on Model Serving); the same prompt and citations are then used with a real LLM.
"""
import json
import logging
import math
import os
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
_WORD = re.compile(r"[a-z0-9]+")
_STOP = set("a an and are as at be by for from has have if in is it its of on or so that the "
            "their there this to was were will with what which who why how do does should we our "
            "i can".split())
log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are the replenishment copilot for Groenhof Markets, a Dutch grocery chain. "
    "Answer store and category managers in plain business language. Use only the facts in the "
    "risk snapshot and the numbered passages. Cite passages as [1], [2]. Recommend concrete "
    "actions with quantities and deadlines. If the context does not answer the question, say so."
)


def _tokens(text: str) -> list[str]:
    """Lower-case words without stop words, with a crude plural/verb stem."""
    words = [t for t in _WORD.findall(text.lower()) if t not in _STOP]
    return [_stem(t) for t in words]


def _stem(word: str) -> str:
    if len(word) <= 4:
        return word
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("ed"):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


@lru_cache(maxsize=1)
def load_passages() -> tuple[dict, ...]:
    """Split every knowledge document into one passage per ``##`` section."""
    passages = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        title, section, lines = path.stem, None, []
        for line in path.read_text().splitlines() + ["## "]:
            if line.startswith("# "):
                title = line[2:].strip()
            elif line.startswith("## "):
                if section and lines:
                    text = " ".join(lines).strip()
                    passages.append({"doc": path.name, "title": title, "section": section,
                                     "text": text, "tokens": _tokens(f"{title} {section} {text}")})
                section, lines = line[3:].strip(), []
            elif section is not None and line.strip():
                lines.append(line.strip())
    return tuple(passages)


def retrieve(query: str, k: int = 3, context: str = "") -> list[dict]:
    """BM25 over passages; swapped for a Vector Search query on Databricks.

    ``context`` terms (the selected product) count half, so the question leads.
    """
    if os.environ.get("COPILOT_VECTOR_INDEX"):
        try:
            return _retrieve_vector_search(f"{query} {context}".strip(), k)
        except Exception:  # keep the demo alive; the offline index has the same documents
            log.exception("Vector Search query failed; using the local index")
    passages = load_passages()
    terms = [(t, 1.0) for t in _tokens(query)] + [(t, 0.5) for t in _tokens(context)]
    n = len(passages)
    avg = sum(len(p["tokens"]) for p in passages) / n
    df = Counter(t for p in passages for t in set(p["tokens"]))
    scored = []
    for p in passages:
        tf = Counter(p["tokens"])
        score = 0.0
        for t, weight in terms:
            if t in tf:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                score += weight * idf * tf[t] * 2.2 / (
                    tf[t] + 1.2 * (0.25 + 0.75 * len(p["tokens"]) / avg))
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda pair: -pair[0])
    return [{key: p[key] for key in ("doc", "title", "section", "text")} | {"score": round(s, 2)}
            for s, p in scored[:k]]


def _retrieve_vector_search(query: str, k: int) -> list[dict]:
    from databricks.sdk import WorkspaceClient

    index = os.environ["COPILOT_VECTOR_INDEX"]
    response = WorkspaceClient().api_client.do(
        "POST", f"/api/2.0/vector-search/indexes/{index}/query",
        body={"query_text": query, "num_results": k,
              "columns": ["doc", "title", "section", "text"]})
    columns = [c["name"] for c in response["manifest"]["columns"]]
    return [dict(zip(columns, row)) for row in response["result"]["data_array"]]


def short_name(product_name: str) -> str:
    """'Whole milk 1L' -> 'whole milk', for questions in plain language."""
    return " ".join(w for w in product_name.lower().split() if not any(c.isdigit() for c in w))


def _first_sentences(text: str, n: int = 2) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:n])


def _fmt_day(date: str | None) -> str:
    if not date:
        return "this week"
    import datetime as dt
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
    endpoint = os.environ.get("COPILOT_SERVING_ENDPOINT", "").strip()
    if not endpoint:
        return None
    try:
        from databricks.sdk import WorkspaceClient

        response = WorkspaceClient().api_client.do(
            "POST", f"/serving-endpoints/{endpoint}/invocations",
            body={"messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"{_context_block(item, passages)}\n\nQuestion: {question}"},
            ], "max_tokens": 500, "temperature": 0.1})
        return response["choices"][0]["message"]["content"]
    except Exception:
        log.exception("Model Serving call failed; using the offline answer")
        return None


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
            "why": (_first_sentences(why[0]["text"])
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
    lines = [f"{_first_sentences(p['text'])} [{i}]" for i, p in enumerate(passages, start=1)]
    lead = f"{situation(item)}\n\n" if item else ""
    return {"answer": lead + "\n\n".join(lines), "sources": passages, "mode": "offline"}

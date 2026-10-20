"""Retrieval and generation shared by every demo: the "activate your knowledge" layer.

Each demo keeps its documents as Markdown in its own ``knowledge/`` folder, one passage per
``##`` section. Locally, passages are ranked with BM25, so demos run offline and every
answer can be traced to a source. On Databricks, set ``COPILOT_VECTOR_INDEX`` (Mosaic AI Vector
Search) and ``COPILOT_SERVING_ENDPOINT`` (a chat model on Model Serving) to use the same
context with a real index and LLM; both fall back to offline mode on errors.
"""
import logging
import math
import os
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

_WORD = re.compile(r"[a-z0-9]+")
_STOP = set("a an and are as at be by for from has have if in is it its of on or so that the "
            "their there this to was were will with what which who why how do does should we our "
            "i can".split())
log = logging.getLogger(__name__)


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


@lru_cache(maxsize=8)
def load_passages(knowledge_dir: Path) -> tuple[dict, ...]:
    """Split every knowledge document into one passage per ``##`` section."""
    passages = []
    for path in sorted(Path(knowledge_dir).glob("*.md")):
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


def retrieve(knowledge_dir: Path, query: str, k: int = 3, context: str = "") -> list[dict]:
    """BM25 over passages; swapped for a Vector Search query on Databricks.

    ``context`` terms (for example the selected product) count half, so the question leads.
    """
    if os.environ.get("COPILOT_VECTOR_INDEX"):
        try:
            return _retrieve_vector_search(f"{query} {context}".strip(), k)
        except Exception:  # keep the demo alive; the offline index has the same documents
            log.exception("Vector Search query failed; using the local index")
    passages = load_passages(Path(knowledge_dir))
    if not passages:
        return []
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


def first_sentences(text: str, n: int = 2) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:n])


_CITATION = re.compile(r"\[(\d+)\]")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def check_grounding(answer: str, n_passages: int, context: str) -> dict:
    """Guardrails for a generated answer: real citations, and no figures the model invented.

    ``context`` is exactly what the model was shown. A number in the answer must appear in it
    (after removing the [n] markers), so the model cannot do its own arithmetic.
    """
    cited = sorted({int(n) for n in _CITATION.findall(answer)})
    invalid = [n for n in cited if not 1 <= n <= n_passages]
    shown = {m.replace(",", ".") for m in _NUMBER.findall(_CITATION.sub("", context))}
    shown |= {str(int(float(m))) for m in shown if float(m) == int(float(m))}
    invented = sorted({m for m in _NUMBER.findall(_CITATION.sub("", answer))
                       if m.replace(",", ".") not in shown})
    return {"cited": cited, "invalid_citations": invalid, "invented_numbers": invented,
            "passed": bool(cited) and not invalid and not invented}


def llm_endpoint() -> str:
    return os.environ.get("COPILOT_SERVING_ENDPOINT", "").strip()


def call_llm(system_prompt: str, context: str, question: str) -> str | None:
    """Ask the configured Model Serving chat endpoint; ``None`` means use the offline answer."""
    endpoint = llm_endpoint()
    if not endpoint:
        return None
    try:
        from databricks.sdk import WorkspaceClient

        response = WorkspaceClient().api_client.do(
            "POST", f"/serving-endpoints/{endpoint}/invocations",
            body={"messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{context}\n\nQuestion: {question}"},
            ], "max_tokens": 500, "temperature": 0.1})
        content = response["choices"][0]["message"]["content"]
        return content.strip() if isinstance(content, str) and content.strip() else None
    except Exception:
        log.exception("Model Serving call failed; using the offline answer")
        return None

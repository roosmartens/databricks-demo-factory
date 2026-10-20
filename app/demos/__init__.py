"""Demo registry: each demo is a self-contained package under ``app/demos/<key>/``.

A demo brings its own synthetic sources and model (``engine.py``), knowledge documents
(``knowledge/``), page and deck templates (``templates/demos/<key>/``) and a default theme.
Everything else is shared: the app shell, the deck engine, retrieval, themes, the
Databricks backend. Select a demo with ``DEMO=<key>`` (default: ``grocery``).
See ``docs/NEW_DEMO.md`` to add one.
"""
import os
from dataclasses import dataclass
from importlib import import_module
from typing import Callable

DEFAULT_DEMO = "grocery"
AVAILABLE = ("grocery",)  # add your demo's package name here


@dataclass(frozen=True)
class Demo:
    key: str
    title: str  # product name shown in the nav, e.g. "Inventory copilot"
    brand: str  # wordmark of the fictional customer, e.g. "groenhof"
    theme: str  # default theme name from app/themes.py
    page_template: str  # the demo's main page, served at /
    deck_template: str  # the slides, included in the shared deck shell at /story
    build_snapshot: Callable[[], dict]  # offline data for the page
    read_databricks: Callable[..., dict]  # (fetch, warehouse_id, schema) -> same shape
    page_context: Callable[[dict, dict], dict]  # (snapshot, query args) -> template context
    ask: Callable[[str, dict, str | None], dict]  # (question, snapshot, item key) -> answer


class UnknownItem(LookupError):
    """The page was asked for an entity the snapshot does not contain."""


def active_demo() -> Demo:
    key = os.environ.get("DEMO", DEFAULT_DEMO).strip().lower()
    if key not in AVAILABLE:
        raise ValueError(f"DEMO must be one of {', '.join(AVAILABLE)}.")
    return import_module(f"app.demos.{key}").DEMO

# Build a new demo on top of the factory

The grocery copilot (`app/demos/grocery/`) is the worked example. A new demo is a copy of that folder plus its templates. Everything else is shared and stays as it is.

## What is shared and what is per demo

| Shared (don't copy) | Per demo (copy and change) |
| --- | --- |
| App shell, nav and theme picker: `app/main.py`, `app/templates/_topbar.html` | Data, model and risk logic: `app/demos/<key>/engine.py` |
| Retrieval and LLM calls: `app/rag.py` | Briefing and Q&A wording: `app/demos/<key>/copilot.py` |
| Databricks SQL access and offline/online switch: `app/backend.py` | Knowledge documents: `app/demos/<key>/knowledge/*.md` (one passage per `##` section) |
| Deck engine (16:9 stage, keys, edit mode, export): `templates/story.html`, `static/story.js`, `static/story.css` | Main page: `app/templates/demos/<key>/<page>.html` |
| Themes: `app/themes.py` | Slides: `app/templates/demos/<key>/deck.html` |
| Styles for cards, tables, charts, chips: `static/styles.css` | Lakehouse notebook: `notebooks/<key>_lakehouse.py` |
| | Speaker notes: `slides/` (or a copy per demo) |

## Steps (about an hour with a coding agent)

1. **Copy the example:** `cp -r app/demos/grocery app/demos/<key>` and `cp -r app/templates/demos/grocery app/templates/demos/<key>`.
2. **Register it:** add `"<key>"` to `AVAILABLE` in `app/demos/__init__.py`, then edit the `DEMO = Demo(...)` block in your `__init__.py`: title, brand, theme, and template paths.
3. **Model the business:** rewrite `engine.py`. Keep the contract the page relies on: `build_snapshot()` returns a dict with `as_of`, `items` (one row per core entity, sorted by priority, each with `actions`), `daily` (time series for the chart), `quality` and `backtest`. Rename the fields to fit the industry (patient, subscriber, machine...).
4. **Write the knowledge:** 4–6 short Markdown files in `knowledge/`: policies, contracts, past incidents, partner updates. These are what the copilot cites, so write them like the customer's real documents.
5. **Adjust the copilot:** in `copilot.py` change `SYSTEM_PROMPT`, `situation()` (the one-sentence summary) and the retrieval queries in `recommend()`.
6. **Page and deck:** edit the copied templates. Keep the four-layer strip on the page and the five-slide arc in the deck (problem, architecture, what we built, value, first 30 days).
7. **Pick or add a theme:** set `theme=` in your `Demo`. To add one, add an entry to `THEMES` in `app/themes.py` with `app` and `deck` token overrides, `fonts_url` and `theme_color`. Every colour, the corner `radius` and the fonts are tokens. See `:root` at the top of `styles.css` and `story.css` for the full list.
8. **Run it:** `DEMO=<key> python -m app.main`, then add tests next to `tests/test_copilot.py`.

## Theme switches

- Per demo: `Demo.theme`.
- For the whole app: `DEMO_THEME=lakehouse-night`.
- Live in the room: the picker in the app header (remembered in a cookie), or `?theme=<name>` on any URL, including `/story`.

## Prompt for your coding agent

```
Read docs/NEW_DEMO.md and app/demos/grocery/. Create a new demo "<key>" for this case:
[PASTE CASE]
Follow the steps in docs/NEW_DEMO.md. Keep it runnable offline with deterministic synthetic
data, label everything as illustrative, and add tests for the new business calculations.
Do not change shared files unless the new demo cannot work without it, and say why if you do.
```

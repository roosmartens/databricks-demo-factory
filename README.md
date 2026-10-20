# Databricks Demo Factory: Grocery Inventory Copilot

A customer-facing demo for a fictional Dutch grocery chain, **Groenhof Markets**. Stores run out of fresh products while other stores throw the same products away, because sales, stock and supplier news live in systems nobody connects. The demo shows all four layers as one flow:

| Layer | What it does | Where |
| --- | --- | --- |
| 1 · Governed data | Postgres POS and promotions, MySQL store stock and a supplier-portal export, unified on **store × product**, with bad rows quarantined | `app/demos/grocery/engine.py` (`make_sources`, `unify`), notebook sections 1–2 |
| 2 · Predict | Backtested demand forecast, then stockout probability and expected waste per store-product | `engine.py`: `SeasonalPromoForecaster`, `build_snapshot`, notebook sections 3–4 |
| 3 · Explain | Copilot over supplier agreements, grower harvest updates, policies and past incidents; recommends actions and cites sources | `app/rag.py`, `app/demos/grocery/copilot.py`, `app/demos/grocery/knowledge/*.md`, notebook section 5 |
| 4 · Act | Copilot page with ranked risks, a 7-day chart, cited actions and an "ask" box; 5-slide deck | `/`, `/story` |

Everything is synthetic and deterministic, so the story is the same every run.

**It's a factory, and grocery is the worked example.** The demo lives in `app/demos/grocery/` (data, model, knowledge, copilot wording) and `app/templates/demos/grocery/` (page and slides). The app shell, deck engine, retrieval, Databricks backend and themes are shared. To build another demo, follow [`docs/NEW_DEMO.md`](./docs/NEW_DEMO.md).

**Themes:** every colour, corner radius and font is a CSS token, set per theme in `app/themes.py`. Grocery defaults to the light **Fresh Market** theme; **Lakehouse Night** is the original dark deck. Switch with the picker in the app header, `?theme=lakehouse-night` on any URL, or `DEMO_THEME`. The presenter script, 30-day plan and objection handling are in [`slides/SPEAKER_NOTES.md`](./slides/SPEAKER_NOTES.md).

## 1. Run locally (no Databricks account or credentials required)

Prerequisite: Python 3.11 or newer and Git. In Terminal:

```bash
cd databricks-demo-factory
bash scripts/setup.sh
source .venv/bin/activate
python -m app.main
```

- http://localhost:8000: the **inventory copilot** (start here in the demo)
- http://localhost:8000/story: the **5-slide deck** (`→` to advance, `E` to edit text, "Download HTML" for an offline copy)
- http://localhost:8000/accuracy: chain-level forecast accuracy by market and category (the earlier demand-planning dashboard)

Locally the copilot retrieves passages with BM25 and assembles its answer from them, so it runs offline and every sentence has a source. On Databricks, set `COPILOT_VECTOR_INDEX` and `COPILOT_SERVING_ENDPOINT` to use Vector Search and an LLM on Model Serving with the same context and citations. If either call fails, the app falls back to offline mode.

The [Frontend Slides skill](./.github/skills/frontend-slides/SKILL.md) and its MIT license and supporting assets are included for presentation work.

## 2. Run tests

```bash
source .venv/bin/activate
bash scripts/check.sh
```

## 3. Publish to a new GitHub repository

Create an **empty, private** GitHub repository named `databricks-demo-factory` (do not initialize it with another README). In this directory:

```bash
git init
git add .
git commit -m "Initial demo starter kit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/databricks-demo-factory.git
git push -u origin main
```

GitHub will prompt you to authenticate if needed. Never commit `.env` files or workspace credentials.

## 4. Databricks CLI and agent skills (optional until your local app works)

Check your CLI:

```bash
databricks version
databricks auth profiles
```

Select the intended workspace profile explicitly. Current Databricks AI Tools install command is `databricks aitools install` for CLI versions that support it; see the official agent skills repository. Older CLI versions may not include this feature.

## 5a. Databricks: the grocery copilot lakehouse

Run [`notebooks/grocery_copilot_lakehouse.py`](./notebooks/grocery_copilot_lakehouse.py) from this repo's Git folder (it imports `app/`). Default target: `main.grocery_copilot`.

1. **Bronze**: the four sources as delivered (`bronze_pos_sales_daily`, `bronze_promo_calendar`, `bronze_store_inventory`, `bronze_supplier_deliveries`).
2. **Silver**: conformed onto store × product, with quarantine counts.
3. **Model**: backtest logged to MLflow; pyfunc registered as `grocery_demand_forecast@champion`.
4. **Gold**: `gold_store_product_risk`, `gold_store_product_projection` and `gold_copilot_run`, which the app reads when `DATA_BACKEND=databricks` and `DATABRICKS_COPILOT_SCHEMA=main.grocery_copilot`.
5. **Knowledge**: `supplier_knowledge_chunks` (Change Data Feed on). Set the `vector_endpoint` widget to create a Delta Sync Vector Search index.

The notebook has not been run against a live workspace in this repo's CI; check it once in your workspace before the demo.

## 5b. Databricks data processing and forecast model (forecast accuracy page)

Run two notebooks in the Databricks workspace UI, in this order. Both default to `main.demo_factory`; change their widgets if your workspace uses a different catalog or schema.

1. [`notebooks/demand_medallion.py`](./notebooks/demand_medallion.py) builds the medallion tables:
   - **Bronze** creates deterministic source-like demo records in Delta.
   - **Silver** standardizes types, filters invalid records, and derives forecast errors.
   - **Gold** (`gold_daily_demand`) aggregates by date, market, and category while retaining the dimensions needed by the app.
2. [`notebooks/demand_forecast_model.py`](./notebooks/demand_forecast_model.py) replaces the synthetic "improved" forecast with a trained one:
   - Trains a scikit-learn gradient-boosting model on Silver history (day of week, planned promotions, market, category, and demand lags of 7+ days).
   - Backtests it on an expanding window, so every scored day is predicted by a model that never saw it.
   - Tracks parameters and backtest metrics in MLflow, registers the model in Unity Catalog as `main.demo_factory.demand_forecast`, and sets the `champion` alias.
   - Writes `gold_daily_forecast`, the same shape as `gold_daily_demand` with the model forecast in `improved_units`, plus table and column comments.

On the synthetic data the backtest gives a WAPE of about 5.5% against 14.1% for the current method. That shows the method working on generated data; it is not a result to promise a customer.

Replace the synthetic Bronze generator with the case's ingestion step when the customer data source is known. The example writes batch Delta tables with overwrite semantics; production refresh and ingestion choices should match the actual source and update cadence.

## 6. Deploy to Databricks Apps

Run both notebooks first, then create a Databricks App and add a SQL warehouse resource with the key `sql-warehouse`. The app uses that resource to query the Gold forecast table. Confirm that the app service principal can use the warehouse and read the table.

Set values in your current shell, using a named CLI profile:

```bash
export DATABRICKS_PROFILE="YOUR_PROFILE"
export DATABRICKS_USER_EMAIL="you@example.com"
export DATABRICKS_APP_NAME="your-existing-app-name"
bash scripts/deploy-app.sh
```

This syncs the project and deploys using `app.yaml` and the Databricks-enabled `requirements.txt`. The production app expects `main.demo_factory.gold_daily_forecast`; update `DATABRICKS_GOLD_TABLE` in `app.yaml` if you changed the notebooks' catalog or schema, or point it at `gold_daily_demand` if you skip the model notebook. It does **not** create a Databricks App resource, SQL warehouse, Unity Catalog tables, or other paid resources. Deployment needs network access and suitable permissions. Validate CLI commands against your installed version.

## 7. Genie space for natural-language questions

[`genie/build_space.py`](./genie/build_space.py) defines a Genie space ("Demand forecast explorer") on `gold_daily_forecast`: column descriptions and synonyms (market, promo, model forecast), entity matching on market and category, governed WAPE measures, three example queries, sample questions, and two benchmarks. To create it in your workspace after running both notebooks:

```bash
export DATABRICKS_PROFILE="YOUR_PROFILE"
export DATABRICKS_USER_EMAIL="you@example.com"
export DATABRICKS_WAREHOUSE_ID="your-warehouse-id"
bash scripts/create-genie-space.sh
```

The script creates the space under `/Workspace/Users/<you>/genie`. Each run creates a new space, so delete an old one in the Genie UI before re-running. Users need `CAN USE` on the warehouse and `SELECT` on the table. Try "How much does the model reduce forecast error during promotions?" before the session.

## 8. Once the actual case arrives

- Put the customer brief into `prompts/ADAPT_CASE.md`.
- Replace the synthetic Bronze generator in `notebooks/demand_medallion.py` with the case's ingestion and processing logic, and revisit the features in `notebooks/demand_forecast_model.py`.
- Update the Flask UI and local synthetic data source in `app/`, and the column descriptions and questions in `genie/build_space.py`.
- Use `slides/SLIDE_STORYLINE.md` for the executive pitch.
- Retest the local app **before** making Databricks connectivity a dependency.

## What this starter kit does NOT do yet

The local Flask app does not run Spark or the model; in local mode the "improved" forecast is synthetic and labeled as illustrative. The trained model runs only in the Databricks notebook, on synthetic data, so its backtest error is a demonstration of the method, not observed savings. Nothing here provisions cloud resources or generates PowerPoint slides.

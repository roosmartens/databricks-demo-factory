# Databricks Demo Factory

A reusable, **case-independent** starter kit for a customer-facing Databricks demo. It runs locally with deterministic synthetic data and separates the web app from a PySpark medallion notebook for Databricks.

## 1. Run locally (no Homebrew, Databricks account, or credentials required)

Prerequisite: Python 3.11 or newer and Git. In Terminal:

```bash
cd databricks-demo-factory
bash scripts/setup.sh
source .venv/bin/activate
python -m app.main
```

Open http://localhost:8000. The local app uses synthetic data and does not need Databricks credentials.
Open http://localhost:8000/story for a ten-slide, Databricks-themed HTML customer story: one idea per slide, with diagrams and numbers instead of bullets. It covers discovery, problem, OKRs, current state, an illustrative value scenario, target architecture, the demo, a six-week pilot, and the ask. Presenter script and objection handling: `slides/SPEAKER_NOTES.md`.

The [Frontend Slides skill](./.github/skills/frontend-slides/SKILL.md) and its MIT license/supporting assets are included for future presentation work. The current deck follows its fixed 16:9 stage and navigation guidance while retaining Flask templates and static assets for the existing app.

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

## 5. Databricks data processing and forecast model

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

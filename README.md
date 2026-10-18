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

## 5. Databricks data processing

[`notebooks/demand_medallion.py`](./notebooks/demand_medallion.py) is a Databricks Python notebook source file. Open it in the Databricks workspace UI to run the sample PySpark flow:

- **Bronze** creates deterministic source-like demo records in Delta.
- **Silver** standardizes types, filters invalid records, and derives forecast errors.
- **Gold** aggregates by date, market, and category while retaining the dimensions needed by the app.

The notebook defaults to `main.demo_factory`; change its widgets if your workspace uses a different catalog or schema. Replace the synthetic Bronze generator with the case's ingestion step when the customer data source is known. The example writes batch Delta tables with overwrite semantics; production refresh and ingestion choices should match the actual source and update cadence.

## 6. Deploy to Databricks Apps

Run the notebook first, then create a Databricks App and add a SQL warehouse resource with the key `sql-warehouse`. The app uses that resource to query the Gold table. Confirm that the app service principal can use the warehouse and read the table.

Set values in your current shell, using a named CLI profile:

```bash
export DATABRICKS_PROFILE="YOUR_PROFILE"
export DATABRICKS_USER_EMAIL="you@example.com"
export DATABRICKS_APP_NAME="your-existing-app-name"
bash scripts/deploy-app.sh
```

This syncs the project and deploys using `app.yaml` and the Databricks-enabled `requirements.txt`. The production app expects `main.demo_factory.gold_daily_demand`; update `DATABRICKS_GOLD_TABLE` in `app.yaml` if you changed the notebook's catalog or schema. It does **not** create a Databricks App resource, SQL warehouse, Unity Catalog tables, or other paid resources. Deployment needs network access and suitable permissions. Validate CLI commands against your installed version.

## 6. Once the actual case arrives

- Put the customer brief into `prompts/ADAPT_CASE.md`.
- Replace the synthetic Bronze generator in `notebooks/demand_medallion.py` with the case's ingestion and processing logic.
- Update the Flask UI and local synthetic data source in `app/`.
- Use `slides/SLIDE_STORYLINE.md` for the executive pitch.
- Retest the local app **before** making Databricks connectivity a dependency.

## What this starter kit does NOT do yet

The local Flask app does not run Spark; Spark processing runs in the Databricks notebook. The starter notebook generates sample Delta tables but does not provision cloud resources, train a model, or automatically generate PowerPoint slides. Forecast predictions are synthetic illustrative values, not an actual trained model or observed savings.

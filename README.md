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

## 5. Deploy the full demo to Databricks (bundle)

One [Declarative Automation Bundle](https://docs.databricks.com/dev-tools/bundles/) (`databricks.yml` + `resources/`) creates everything:

| Resource | What it does |
| --- | --- |
| Job `demand-planning-refresh` | Runs three tasks in order: generate raw files, refresh the pipeline, grant the app read access |
| `src/notebooks/generate_raw_data.py` | Writes one synthetic JSON file per day into a Unity Catalog volume (`raw_demand`). Safe to re-run; only new days are written. Includes 3 deliberately bad records |
| Pipeline `demand-planning-medallion` | Lakeflow Spark Declarative Pipeline (serverless): **Bronze** (Auto Loader) → **Silver** (typed, validated with expectations) → **Gold** (materialized view by date, market, category) |
| App `demand-planner-<you>` | This Flask app on Databricks Apps, reading `gold_daily_demand` through a SQL warehouse |

Defaults: catalog `workspace`, schema `demo_factory`, warehouse `Serverless Starter Warehouse`. Change them in `databricks.yml` and keep `DATABRICKS_GOLD_TABLE` in `app.yaml` in sync.

```bash
databricks auth profiles                                        # choose your profile
databricks bundle validate --strict --target dev --profile YOUR_PROFILE
databricks bundle deploy   --target dev --profile YOUR_PROFILE  # creates the pipeline, job and app
databricks bundle run demand_job --target dev --profile YOUR_PROFILE   # builds the tables
databricks bundle run demand_app --target dev --profile YOUR_PROFILE   # starts and deploys the app
```

Run the job before the app so the table exists. The job's last task grants the app's service principal `USE CATALOG` on the catalog and `USE SCHEMA` and `SELECT` on the schema.

To simulate new data arriving, run the generator notebook task with a larger `days` value, then run the job again. Bronze picks up only the new files.

Clean up when you are done: `databricks bundle destroy --target dev --profile YOUR_PROFILE` removes the pipeline, job and app. Tables, schema and volume stay unless you drop them.

`notebooks/demand_medallion.py` is an older, single-notebook version of the same flow. It writes the same table names, so do not run it in the same schema as the pipeline.

## 6. Once the actual case arrives

- Put the customer brief into `prompts/ADAPT_CASE.md`.
- Replace `src/notebooks/generate_raw_data.py` with the case's ingestion, and adapt the Bronze/Silver/Gold files in `src/pipeline/transformations/`.
- Update the Flask UI and local synthetic data source in `app/`.
- Use `slides/SLIDE_STORYLINE.md` for the executive pitch.
- Retest the local app **before** making Databricks connectivity a dependency.

## What this starter kit does NOT do yet

The local Flask app does not run Spark; Spark processing runs in the Databricks pipeline. The bundle creates Databricks resources that can incur cost, but does not train a model, or automatically generate PowerPoint slides. Forecast predictions are synthetic illustrative values, not an actual trained model or observed savings.

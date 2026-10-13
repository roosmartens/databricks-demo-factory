# Databricks Demo Factory

A reusable, **case-independent** starter kit for a customer-facing Databricks demo. Runs locally with deterministic synthetic data; can be deployed as a Streamlit Databricks App later.

## 1. Run locally (no Homebrew, Databricks account, or credentials required)

Prerequisite: Python 3.11 or 3.12 and Git. In Terminal:

```bash
cd databricks-demo-factory
bash scripts/setup.sh
source .venv/bin/activate
python -m streamlit run app/main.py
```

Open the localhost address shown in Terminal (normally http://localhost:8501).

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

## 5. Deploy to Databricks Apps

Create a Databricks App in the workspace UI first, note its name, and ensure the chosen account/workspace supports Apps. Confirm that the app service principal has access to its source and any external resources.

Set values in your current shell, using a named CLI profile:

```bash
export DATABRICKS_PROFILE="YOUR_PROFILE"
export DATABRICKS_USER_EMAIL="you@example.com"
export DATABRICKS_APP_NAME="your-existing-app-name"
bash scripts/deploy-app.sh
```

This syncs the project and deploys using `app.yaml`. It does **not** create a Databricks App resource, SQL warehouse, Unity Catalog tables or other paid resources. Deployment needs network access and suitable permissions. Validate CLI commands against your installed version.

## 6. Once the actual case arrives

- Put the customer brief into `prompts/ADAPT_CASE.md`.
- Replace the example metrics and data logic in `app/data.py`.
- Adapt the demo user journey in `app/main.py`.
- Use `slides/SLIDE_STORYLINE.md` for the executive pitch.
- Retest the local app **before** making Databricks connectivity a dependency.

## What this starter kit does NOT do yet

It does not run Spark, persist Delta tables, train a model, provision cloud resources, or automatically generate PowerPoint slides. Add only the parts genuinely useful for the eventual customer case. Sample forecast predictions are synthetic illustrative values, not an actual trained model. The scenario calculator uses assumptions, not observed savings.

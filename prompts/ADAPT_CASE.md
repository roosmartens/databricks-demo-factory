You are adapting this reusable demo kit to a real customer case for a 60-minute Databricks Solutions Architect panel (75% customer story, 25% demo). Read first: `.github/instructions/build-demo-pitch.instructions.md`, `README.md`, `slides/SLIDE_STORYLINE.md`, `slides/SPEAKER_NOTES.md`.

## Ground rules

- The story matters more than the build. Budget about 1.5 hours for the build; finish early.
- Do not invent customer facts, measurable impact or ML validation. Label every number as an assumption or illustrative; synthetic data is never a customer result.
- Vertical and scenario are aligned with the hiring manager. If the case does not state them, list assumptions instead of guessing.
- Keep the existing Lakehouse Night look and the structure below.

## What is in the kit

| Area | Files |
| --- | --- |
| Web app (Flask) | `app/backend.py`, `app/data.py` (local fallback), `app/main.py`, `app/templates/index.html`, `app/static/{styles.css,dashboard.js}` |
| Story deck (10 slides) | `app/templates/story.html`, `app/static/{story.css,story.js}`, uses `.github/skills/frontend-slides/` |
| Talk track | `slides/SPEAKER_NOTES.md`, `slides/SLIDE_STORYLINE.md` |
| Databricks bundle | `databricks.yml`, `resources/demand.{pipeline,job,app}.yml`, `app.yaml` |
| Synthetic data | `src/notebooks/generate_raw_data.py` |
| Medallion pipeline | `src/pipeline/transformations/{bronze,silver,gold}_*.py` |
| Permissions | `src/notebooks/grant_app_access.py` |
| Tests | `tests/test_web.py` |

## Steps

1. Summarize the business decision, personas (business, data, IT, architecture), OKRs, current pain and success measures. List open discovery questions for the first 10 minutes.
2. Propose a 5-minute demo journey and 3-4 KPIs that follow the story.
3. Replace the synthetic data generator, bronze/silver/gold layers and gold columns with the case domain. Rename files, resources and the `demand` naming consistently. Keep a few deliberate bad rows so silver expectations are visible.
4. Update `app/data.py` (local fallback), `app/backend.py`, the dashboard template and JS to the new gold columns and KPIs. The app must still run locally with `DATA_BACKEND=demo`.
5. Update `tests/test_web.py`; run `.venv/bin/python -m pytest -q` and `git diff --check`.
6. Update the 10-slide deck and `slides/SPEAKER_NOTES.md` for the case (discovery, problem, OKRs, current state, illustrative value, target architecture, demo, pilot, ask). Few words per slide, diagrams and numbers over bullets. Keep the slide-count test passing. Do not claim Genie, dashboards or models unless built.
7. Explain the Databricks resources and permissions needed (catalog/schema, volume, pipeline, warehouse, app service principal grants).

## Deploy (only after tests pass; resources incur cost)

- `app.yaml` `DATABRICKS_GOLD_TABLE` must equal `<catalog>.<schema>.<gold table>` from `databricks.yml`.
- Use a new schema name per case (or `databricks bundle destroy`). Never run `notebooks/demand_medallion.py` in the same schema as the pipeline.
- `databricks bundle validate --profile DEFAULT`, then `deploy --target dev`, `run <job>`, `run <app>`.
- Stop the app when done: `databricks apps stop <app-name> --profile DEFAULT`.

## Customer case

[PASTE CASE HERE]

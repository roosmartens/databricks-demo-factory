import pytest

from app.main import app
from app.backend import load_accuracy
from app.demos.grocery import engine


def test_accuracy_page_renders_synthetic_grocery_backtest(monkeypatch):
    monkeypatch.setenv("DATA_BACKEND", "demo")
    response = app.test_client().get("/accuracy")

    assert response.status_code == 200
    assert b"Can we trust the forecast?" in response.data
    assert b"Synthetic demo data" in response.data
    assert b"Sales vs forecast" in response.data
    assert b"Amsterdam Centrum" in response.data


def test_customer_story_has_five_slides():
    response = app.test_client().get("/story")

    assert response.status_code == 200
    assert response.data.count(b"data-slide") == 5
    assert b"Shortage in Amsterdam." in response.data
    assert b"One set of rules" in response.data
    assert b"Prove it in 30 days" in response.data
    assert b'class="deck-stage"' in response.data
    assert b"Open the live copilot" in response.data
    assert b"Download HTML" in response.data


def test_accuracy_matches_the_engine_backtest(monkeypatch):
    monkeypatch.setenv("DATA_BACKEND", "demo")
    dashboard = load_accuracy({}, False)
    expected = engine.backtest(engine.unify(engine.make_sources())["sales"])

    assert dashboard["baseline_wape"] == pytest.approx(expected["current_wape"], abs=1e-3)
    assert dashboard["improved_wape"] == pytest.approx(expected["model_wape"], abs=1e-3)
    assert dashboard["improved_wape"] < dashboard["baseline_wape"]


def test_filters_are_applied(monkeypatch):
    monkeypatch.setenv("DATA_BACKEND", "demo")
    everything = load_accuracy({}, False)
    one_store = load_accuracy({"store": "Utrecht Oudegracht", "category": "Dairy"}, True)
    response = app.test_client().get("/accuracy?store=Utrecht+Oudegracht&category=Dairy&promotions=1")

    assert response.status_code == 200
    assert 0 < one_store["actual_volume"] < everything["actual_volume"]
    assert b"No sales for these filters" not in response.data


def test_unknown_filter_is_rejected():
    response = app.test_client().get("/accuracy?store=invalid")

    assert response.status_code == 400
    assert b"Unknown store filter." in response.data


def test_missing_databricks_configuration_does_not_fall_back(monkeypatch):
    monkeypatch.setenv("DATA_BACKEND", "databricks")
    monkeypatch.delenv("DATABRICKS_WAREHOUSE_ID", raising=False)
    monkeypatch.delenv("DATABRICKS_COPILOT_SCHEMA", raising=False)

    response = app.test_client().get("/accuracy")

    assert response.status_code == 503
    assert b"could not be loaded" in response.data
    assert b"Synthetic demo data" not in response.data


def test_databricks_accuracy_queries_the_gold_table(monkeypatch):
    seen = {}

    def fake_fetch(warehouse_id, query, parameters=None):
        seen.update(query=query, parameters=parameters)
        return [{"demand_date": __import__("datetime").date(2026, 10, 19), "actual_units": 10,
                 "baseline_units": 12, "improved_units": 10, "baseline_abs_error": 2,
                 "improved_abs_error": 0, "absolute_actual_units": 10, "promotion_days": 0}]

    monkeypatch.setenv("DATA_BACKEND", "databricks")
    monkeypatch.setenv("DATABRICKS_WAREHOUSE_ID", "wh")
    monkeypatch.setenv("DATABRICKS_COPILOT_SCHEMA", "main.grocery_copilot")
    monkeypatch.setattr("app.backend._fetch", fake_fetch)
    dashboard = load_accuracy({"category": "Dairy"}, False)

    assert "main.grocery_copilot.gold_forecast_accuracy" in seen["query"]
    assert "category = ?" in seen["query"] and seen["parameters"] == ["Dairy"]
    assert dashboard["source"] == "Databricks Gold table"
    assert dashboard["improved_wape"] == 0


def test_csv_export_contains_daily_totals(monkeypatch):
    monkeypatch.setenv("DATA_BACKEND", "demo")
    response = app.test_client().get("/export.csv?store=Eindhoven+Strijp")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert b"date,actual_units,baseline_units,improved_units,promotion_days" in response.data


def test_local_backtest_is_labelled_out_of_sample(monkeypatch):
    monkeypatch.setenv("DATA_BACKEND", "demo")
    response = app.test_client().get("/accuracy")

    assert "Out-of-sample, last 14 days".encode() in response.data

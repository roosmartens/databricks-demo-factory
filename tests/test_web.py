import pytest

from app.main import app
from app.backend import load_dashboard
from app.data import make_demo_data, summarize


def test_dashboard_renders_synthetic_data(monkeypatch):
    monkeypatch.setenv("DATA_BACKEND", "demo")
    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"Plan with confidence." in response.data
    assert b"Synthetic demo data" in response.data
    assert b"Demand over time" in response.data


def test_local_dashboard_metrics_match_demo_data(monkeypatch):
    monkeypatch.setenv("DATA_BACKEND", "demo")
    dashboard = load_dashboard("All markets", "All categories", False)
    expected = summarize(make_demo_data())

    assert dashboard["actual_volume"] == pytest.approx(expected["actual_volume"])
    assert dashboard["baseline_wape"] == pytest.approx(expected["baseline_wape"])
    assert dashboard["improved_wape"] == pytest.approx(expected["improved_wape"])


def test_filters_are_applied(monkeypatch):
    monkeypatch.setenv("DATA_BACKEND", "demo")
    response = app.test_client().get("/?region=Germany&category=Beverages&promotions=1")

    assert response.status_code == 200
    assert b"Through <strong>2026-09-" in response.data
    assert b"No demand for these filters" not in response.data


def test_unknown_filter_is_rejected():
    response = app.test_client().get("/?region=invalid")

    assert response.status_code == 400
    assert b"Unknown market filter." in response.data


def test_missing_databricks_configuration_does_not_fall_back(monkeypatch):
    monkeypatch.setenv("DATA_BACKEND", "databricks")
    monkeypatch.delenv("DATABRICKS_WAREHOUSE_ID", raising=False)
    monkeypatch.delenv("DATABRICKS_GOLD_TABLE", raising=False)

    response = app.test_client().get("/")

    assert response.status_code == 503
    assert b"could not be loaded" in response.data
    assert b"Synthetic demo data" not in response.data


def test_csv_export_contains_daily_totals(monkeypatch):
    monkeypatch.setenv("DATA_BACKEND", "demo")
    response = app.test_client().get("/export.csv?region=France")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert b"date,actual_units,baseline_units,improved_units,promotion_days" in response.data

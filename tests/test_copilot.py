import pytest

from app import copilot
from app.grocery import build_snapshot, make_sources, unify
from app.main import app


@pytest.fixture(scope="module")
def snapshot():
    return build_snapshot()


def _item(snapshot, store, sku):
    return next(i for i in snapshot["items"] if i["store_code"] == store and i["sku"] == sku)


def test_sources_are_unified_on_store_product():
    silver = unify(make_sources())
    quality = silver["quality"]

    assert quality["store_products"] == 36
    assert quality["pos_quarantined"] == 2
    assert quality["inventory_keys_standardized"] > 0
    assert set(silver["inventory"]["store_code"]) == {"AMS-01", "UTR-02", "RTM-03", "EHV-04"}


def test_snapshot_is_deterministic(snapshot):
    again = build_snapshot()
    assert [i["value_at_risk_eur"] for i in again["items"]] == [
        i["value_at_risk_eur"] for i in snapshot["items"]]


def test_forecast_beats_last_week_out_of_sample(snapshot):
    backtest = snapshot["backtest"]
    assert backtest["model_wape"] < backtest["current_wape"]


def test_demo_story_risks(snapshot):
    top = snapshot["items"][0]
    assert (top["store_code"], top["sku"]) == ("AMS-01", "SKU-1001")
    assert top["status"] == "stockout"
    assert top["stockout_date"] == "2026-10-22"
    assert _item(snapshot, "UTR-02", "SKU-1001")["status"] == "waste"
    assert _item(snapshot, "EHV-04", "SKU-1006")["status"] == "stockout"
    assert _item(snapshot, "RTM-03", "SKU-1008")["status"] == "waste"


def test_surplus_is_transferred_once(snapshot):
    transfers = [a for i in snapshot["items"] if i["sku"] == "SKU-1001"
                 for a in i["actions"] if a["kind"] == "transfer" and "from" in a]
    donor = _item(snapshot, "UTR-02", "SKU-1001")
    assert transfers
    assert sum(a["units"] for a in transfers) <= donor["waste_units"]


def test_briefing_cites_the_grower_update(snapshot):
    briefing = copilot.recommend(snapshot["items"][0])
    assert briefing["mode"] == "offline"
    assert "Zeeland" in briefing["why"]
    assert all(step["ref"] for step in briefing["steps"])
    assert max(step["ref"] for step in briefing["steps"]) <= len(briefing["sources"])


def test_retrieval_finds_the_right_policy():
    assert copilot.retrieve("What are the rules for store transfers?")[0]["section"] == "Store transfers"
    assert "Huelva" in copilot.retrieve("alternative supplier for strawberries")[0]["section"]


def test_copilot_page_and_ask_api(monkeypatch):
    monkeypatch.setenv("DATA_BACKEND", "demo")
    client = app.test_client()

    page = client.get("/")
    assert page.status_code == 200
    assert b"Today&#39;s shelf risks" in page.data or b"Today's shelf risks" in page.data
    assert b"Recommended actions" in page.data

    assert client.get("/?item=EHV-04:SKU-1006").status_code == 200
    assert client.get("/?item=nope").status_code == 404

    answer = client.post("/api/ask", json={"question": "What are the rules for store transfers?",
                                           "item": "AMS-01:SKU-1001"})
    assert answer.status_code == 200
    assert answer.json["sources"][0]["section"] == "Store transfers"
    assert client.post("/api/ask", json={}).status_code == 400

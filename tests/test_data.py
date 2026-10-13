from app.data import make_demo_data, summarize, wape


def test_data_is_deterministic():
    assert make_demo_data().equals(make_demo_data())


def test_expected_rows():
    assert len(make_demo_data(periods=10)) == 90


def test_metrics():
    d = make_demo_data()
    s = summarize(d)
    assert s["actual_volume"] > 0
    assert s["improved_wape"] < s["baseline_wape"]
    assert wape(d["actual"], d["actual"]) == 0

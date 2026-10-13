"""Replace this file first when the customer case arrives.
Deterministic synthetic demand and forecast data; no workspace access required.
"""
import numpy as np
import pandas as pd

REGIONS = ["Netherlands", "Germany", "France"]
CATEGORIES = ["Fresh food", "Beverages", "Household"]


def make_demo_data(seed: int = 42, periods: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end=pd.Timestamp("2026-09-30"), periods=periods, freq="D")
    records = []
    for r_ix, region in enumerate(REGIONS):
        for c_ix, category in enumerate(CATEGORIES):
            t = np.arange(periods)
            base = 175 + r_ix * 45 + c_ix * 30
            seasonal = 35 * np.sin(2 * np.pi * t / 7 + c_ix)
            promo = (t % 23 < 4).astype(int)
            actual = np.maximum(10, base + seasonal + promo * 55 + rng.normal(0, 22, periods))
            baseline = np.maximum(10, base + rng.normal(0, 38, periods))
            improved = np.maximum(10, actual + rng.normal(0, 16, periods))
            for idx, date in enumerate(dates):
                records.append({"date": date, "region": region, "category": category,
                                "actual": round(float(actual[idx]), 1),
                                "baseline": round(float(baseline[idx]), 1),
                                "improved": round(float(improved[idx]), 1),
                                "promotion": int(promo[idx])})
    return pd.DataFrame.from_records(records)


def wape(actual, prediction) -> float:
    """Weighted absolute percentage error; 0-100 percent for positive demand."""
    denominator = float(np.abs(actual).sum())
    return 100 * float(np.abs(actual - prediction).sum()) / denominator if denominator else 0.0


def summarize(frame: pd.DataFrame) -> dict:
    baseline = wape(frame["actual"], frame["baseline"])
    improved = wape(frame["actual"], frame["improved"])
    return {"actual_volume": float(frame["actual"].sum()),
            "baseline_wape": baseline,
            "improved_wape": improved,
            "error_reduction_pct": (100 * (baseline - improved) / baseline) if baseline else 0.0}

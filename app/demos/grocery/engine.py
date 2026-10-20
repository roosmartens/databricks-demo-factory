"""Groenhof Markets: synthetic grocery data and the stockout/waste engine.

The customer described three systems nobody has connected, each with its own keys:

- Postgres point of sale: ``store_id`` (int) and ``sku``
- MySQL store inventory: ``store_code`` and ``ean``
- Supplier portal (SaaS CSV export): ``gtin`` and ``supplier_id``

``unify`` maps all three onto one core entity, the **store-product** (store_code x sku),
``SeasonalPromoForecaster`` predicts daily demand per store-product, and ``build_snapshot``
turns forecast + stock + confirmed deliveries into stockout and waste risk with actions.

Everything is deterministic so the demo tells the same story every run. The Databricks
notebook imports this module, so local mode and the lakehouse produce the same numbers.
"""
import math

import numpy as np
import pandas as pd

AS_OF = pd.Timestamp("2026-10-20")  # "today" in the demo: a Tuesday
HISTORY_DAYS = 56                   # weeks of generated sales history (8 weeks)
HORIZON_DAYS = 7                    # how far ahead we forecast and assess risk
# Weekday multiplier on demand, Monday..Sunday: 1.0 = an average day, 1.3 = 30% busier (Saturday)
DOW_FACTORS = (0.85, 0.85, 0.9, 0.95, 1.15, 1.3, 1.0)
STOCKOUT_THRESHOLD = 0.5            # chance of running out >= 50% -> status "stockout"
WATCH_THRESHOLD = 0.2               # chance of 20-50% -> status "watch"
# Operating rules from the (fictional) policy and supplier documents in knowledge/.
MIN_TRANSFER = 20                      # smallest worthwhile store-to-store transfer, in units
TRANSFER_COST_PER_UNIT = 0.15          # euro per unit, internal van run
# Shelf life (days) the product must still have on arrival; other categories are not transferred
TRANSFER_SHELF_DAYS = {"Fresh produce": 2, "Dairy": 1}
CASE_UNITS = 10                        # punnets per Huelva case
ALT_MIN_CASES = 20                     # Huelva minimum order in cases (20 x 10 = 200 units)
ALT_SUPPLIER_FILL_PCT = 80             # buyers may use the alternative when the main supplier confirms less than this %

# size = volume multiplier relative to Utrecht (1.0): Amsterdam sells 35% more
STORES = pd.DataFrame.from_records([
    {"store_id": 101, "store_code": "AMS-01", "store_name": "Amsterdam Centrum", "size": 1.35},
    {"store_id": 102, "store_code": "UTR-02", "store_name": "Utrecht Oudegracht", "size": 1.0},
    {"store_id": 103, "store_code": "RTM-03", "store_name": "Rotterdam Kop van Zuid", "size": 1.15},
    {"store_id": 104, "store_code": "EHV-04", "store_name": "Eindhoven Strijp", "size": 0.85},
])

PRODUCTS = pd.DataFrame.from_records([
    # sku, ean (barcode), name, category, shelf life (days), price (EUR), cost (EUR, what we pay),
    # supplier, base daily units (average sales per day in a size-1.0 store)
    ("SKU-1001", "8712000100015", "Strawberries 400g", "Fresh produce", 4, 3.49, 1.90, "ZBG", 42),
    ("SKU-1002", "8712000100022", "Vine tomatoes 500g", "Fresh produce", 7, 2.29, 1.10, "WKC", 38),
    ("SKU-1003", "8712000100039", "Iceberg lettuce", "Fresh produce", 5, 1.19, 0.55, "WKC", 30),
    ("SKU-1004", "8712000100046", "Bananas 1kg", "Fresh produce", 6, 1.89, 0.95, "TFI", 55),
    ("SKU-1005", "8712000100053", "Avocados 2-pack", "Fresh produce", 5, 2.99, 1.45, "TFI", 26),
    ("SKU-1006", "8712000100060", "Whole milk 1L", "Dairy", 9, 1.25, 0.70, "NLZ", 70),
    ("SKU-1007", "8712000100077", "Greek yoghurt 500g", "Dairy", 21, 2.49, 1.20, "NLZ", 24),
    ("SKU-1008", "8712000100084", "Sourdough loaf", "Bakery", 2, 3.29, 1.20, "BDM", 28),
    ("SKU-1009", "8712000100091", "Chicken breast 500g", "Meat", 6, 5.99, 3.60, "BRP", 22),
], columns=["sku", "ean", "product_name", "category", "shelf_life_days",
            "unit_price", "unit_cost", "supplier_id", "base_units"])

# lead_time_days: days from order to delivery. fill_rate_90d: share of ordered volume actually
# delivered over the last 90 days. alt_*: fallback supplier, its lead time and price premium (%).
# can_expedite: whether a faster delivery is possible.
SUPPLIERS = pd.DataFrame.from_records([
    {"supplier_id": "ZBG", "supplier_name": "Zeeland Berry Growers", "lead_time_days": 1,
     "fill_rate_90d": 0.97, "alt_supplier": "Huelva Berry Cooperative", "alt_lead_days": 2,
     "alt_premium_pct": 18, "can_expedite": False},
    {"supplier_id": "WKC", "supplier_name": "Westland Kas Collectief", "lead_time_days": 1,
     "fill_rate_90d": 0.98, "alt_supplier": None, "alt_lead_days": None, "alt_premium_pct": None,
     "can_expedite": True},
    {"supplier_id": "TFI", "supplier_name": "Tropic Fresh Import", "lead_time_days": 2,
     "fill_rate_90d": 0.93, "alt_supplier": None, "alt_lead_days": None, "alt_premium_pct": None,
     "can_expedite": False},  # not during port congestion
    {"supplier_id": "NLZ", "supplier_name": "Noorderland Zuivel", "lead_time_days": 1,
     "fill_rate_90d": 0.99, "alt_supplier": None, "alt_lead_days": None, "alt_premium_pct": None,
     "can_expedite": True},
    {"supplier_id": "BDM", "supplier_name": "Bakkerij De Molen", "lead_time_days": 1,
     "fill_rate_90d": 0.99, "alt_supplier": None, "alt_lead_days": None, "alt_premium_pct": None,
     "can_expedite": True},
    {"supplier_id": "BRP", "supplier_name": "Brabant Poultry", "lead_time_days": 2,
     "fill_rate_90d": 0.96, "alt_supplier": None, "alt_lead_days": None, "alt_premium_pct": None,
     "can_expedite": True},
])

# Promo uplift: sales multiplier while a promotion runs, per category (1.6 = +60% units).
PROMO_UPLIFT = {"Fresh produce": 1.6, "Dairy": 1.35, "Bakery": 1.3, "Meat": 1.45}
# (sku, first day, last day) as day offsets from AS_OF: a "2+1" (buy 2, get 1 free)
# strawberry promotion from Thursday (+2) to Sunday (+5) of the demo week.
PLANNED_PROMOS = [("SKU-1001", 2, 5)]

# An "override" replaces the generator's normal value for one case, so the demo has
# scripted situations to walk through; everything else is business as usual.
# (store_code, sku): (days of cover on hand, days until the oldest batch expires).
# "Days of cover" = how many days current stock lasts at normal sales pace.
STOCK_OVERRIDES = {
    ("AMS-01", "SKU-1001"): (0.9, 3),   # promo + harvest shortfall -> stockout first
    ("UTR-02", "SKU-1001"): (5.0, 3),   # over-ordered strawberries -> waste, transfer donor
    ("RTM-03", "SKU-1008"): (2.6, 1),   # sourdough over-baked -> waste
    ("EHV-04", "SKU-1006"): (1.1, 7),   # missed dairy delivery slot -> stockout
    ("UTR-02", "SKU-1009"): (4.2, 2),   # chicken over-stocked -> waste
    ("RTM-03", "SKU-1005"): (3.0, 4),   # avocados, ripening delay at port -> watch
}
# Supplier portal: (store_code or "*" for all stores, sku) -> (first delivery day offset,
# confirmed fill rate). Fill rate = share of the ordered units the supplier confirms it will
# deliver (0.7 = 30% short).
DELIVERY_OVERRIDES = {
    ("*", "SKU-1001"): (1, 0.7),        # ZBG confirms ~70% of orders after heavy rain in Zeeland
    ("EHV-04", "SKU-1006"): (2, 1.0),   # order missed Monday's 14:00 cut-off
    ("RTM-03", "SKU-1005"): (2, 0.7),   # TFI: containers held at the Port of Rotterdam
}


def _promo_days(sku: str, index: int) -> int:
    """History promos: each product runs a 3-day promo every 21 days, offset by product."""
    return int((index + int(sku[-2:]) * 5) % 21 < 3)


def make_sources(seed: int = 7) -> dict:
    """Raw extracts as each source system would deliver them, quirks included."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end=AS_OF - pd.Timedelta(days=1), periods=HISTORY_DAYS, freq="D")
    sales = []
    for store in STORES.itertuples():
        for product in PRODUCTS.itertuples():
            for index, date in enumerate(dates):
                promo = _promo_days(product.sku, index)
                mean = (product.base_units * store.size * DOW_FACTORS[date.dayofweek]
                        * (PROMO_UPLIFT[product.category] if promo else 1.0))
                units = int(round(mean * rng.lognormal(0, 0.12)))
                sales.append({"store_id": store.store_id, "sku": product.sku,
                              "sale_date": date.strftime("%Y-%m-%d"), "units_sold": units,
                              "promo_flag": promo})
    # Real extracts are messy: an unknown SKU from a till test, and returns booked as sales.
    sales.append({"store_id": 103, "sku": "SKU-9999", "sale_date": dates[-3].strftime("%Y-%m-%d"),
                  "units_sold": 1, "promo_flag": 0})
    sales.append({"store_id": 101, "sku": "SKU-1004", "sale_date": dates[-2].strftime("%Y-%m-%d"),
                  "units_sold": -4, "promo_flag": 0})
    pos = pd.DataFrame.from_records(sales)

    # Promotion calendar, also in the Postgres commercial schema.
    promos = [{"sku": sku, "promo_date": (AS_OF + pd.Timedelta(days=d)).strftime("%Y-%m-%d"),
               "mechanic": "2+1"}
              for sku, first, last in PLANNED_PROMOS for d in range(first, last + 1)]
    promo_calendar = pd.DataFrame.from_records(promos)

    inventory, deliveries = [], []
    for store in STORES.itertuples():
        for product in PRODUCTS.itertuples():
            daily = product.base_units * store.size
            default_cover = {"Dairy": 3.0, "Bakery": 1.1}.get(product.category, 1.8)
            cover, expiry = STOCK_OVERRIDES.get(
                (store.store_code, product.sku), (default_cover, product.shelf_life_days - 1))
            code = store.store_code.lower() if store.store_code == "AMS-01" else store.store_code
            inventory.append({"store_code": f" {code}" if code != store.store_code else code,
                              "ean": product.ean, "on_hand_units": int(round(daily * cover)),
                              "oldest_batch_days_to_expiry": expiry,
                              "snapshot_ts": AS_OF.strftime("%Y-%m-%d 05:30:00")})

            first, fill = DELIVERY_OVERRIDES.get(
                (store.store_code, product.sku),
                DELIVERY_OVERRIDES.get(("*", product.sku), (1, 1.0)))
            cycle = 2
            promo_days = {d for sku, a, b in PLANNED_PROMOS if sku == product.sku
                          for d in range(a, b + 1)}
            for offset in range(first, HORIZON_DAYS, cycle):
                # Planners do order up for promotions; the cycle covers today and tomorrow.
                cover = sum(DOW_FACTORS[(AS_OF + pd.Timedelta(days=d)).dayofweek]
                            * (PROMO_UPLIFT[product.category] if d in promo_days else 1.0)
                            for d in range(offset, offset + cycle))
                ordered = int(round(product.base_units * store.size * cover * 1.05))
                deliveries.append({
                    "gtin": product.ean, "supplier_id": product.supplier_id,
                    "ship_to": store.store_code,
                    "delivery_date": (AS_OF + pd.Timedelta(days=offset)).strftime("%Y-%m-%d"),
                    "ordered_units": ordered,
                    "confirmed_units": int(round(ordered * fill)),
                })
    return {
        "postgres.pos.sales_daily": pos,
        "postgres.commercial.promo_calendar": promo_calendar,
        "mysql.wms.store_inventory": pd.DataFrame.from_records(inventory),
        "saas.supplier_portal.confirmed_deliveries": pd.DataFrame.from_records(deliveries),
    }


def unify(sources: dict) -> dict:
    """Silver: conform keys onto store_code x sku, standardize types, quarantine bad rows."""
    pos = sources["postgres.pos.sales_daily"].merge(
        STORES[["store_id", "store_code"]], on="store_id", how="left")
    known_sku = pos["sku"].isin(PRODUCTS["sku"])
    valid = known_sku & pos["store_code"].notna() & (pos["units_sold"] >= 0)
    quarantine = pos[~valid].assign(
        reason=np.where(~known_sku[~valid], "Unknown SKU", "Negative units (return booked as sale)"))
    sales = (pos[valid]
             .assign(date=lambda f: pd.to_datetime(f["sale_date"]),
                     units=lambda f: f["units_sold"].astype(float),
                     promo=lambda f: f["promo_flag"].astype(int))
             [["store_code", "sku", "date", "units", "promo"]]
             .reset_index(drop=True))

    raw_inventory = sources["mysql.wms.store_inventory"]
    inventory = raw_inventory.assign(
        store_code=raw_inventory["store_code"].str.strip().str.upper())
    standardized = int((inventory["store_code"] != raw_inventory["store_code"]).sum())
    inventory = inventory.merge(PRODUCTS[["ean", "sku"]], on="ean", how="inner")

    deliveries = (sources["saas.supplier_portal.confirmed_deliveries"]
                  .rename(columns={"ship_to": "store_code"})
                  .merge(PRODUCTS[["ean", "sku"]], left_on="gtin", right_on="ean")
                  .assign(date=lambda f: pd.to_datetime(f["delivery_date"])))

    promos = sources["postgres.commercial.promo_calendar"].assign(
        date=lambda f: pd.to_datetime(f["promo_date"]))

    quality = {
        "pos_rows": int(len(pos)),
        "pos_quarantined": int(len(quarantine)),
        "quarantine_reasons": quarantine["reason"].value_counts().to_dict(),
        "inventory_rows": int(len(raw_inventory)),
        "inventory_keys_standardized": standardized,
        "delivery_rows": int(len(deliveries)),
        "store_products": int(sales.groupby(["store_code", "sku"]).ngroups),
    }
    return {"sales": sales, "inventory": inventory, "deliveries": deliveries,
            "promos": promos, "quality": quality}


class SeasonalPromoForecaster:
    """Daily demand per store-product: recent level x day-of-week shape x promo uplift.

    Deliberately simple and explainable; in the pilot it is the baseline a gradient-boosted
    model has to beat. ``sigma`` is the residual spread used for stockout probabilities.
    """

    def fit(self, sales: pd.DataFrame, level_days: int = 28) -> "SeasonalPromoForecaster":
        frame = sales.merge(PRODUCTS[["sku", "category"]], on="sku")
        frame["dow"] = frame["date"].dt.dayofweek
        normal = frame[frame["promo"] == 0]
        dow = normal.groupby(["category", "dow"])["units"].mean()
        self.dow_ = (dow / dow.groupby(level="category").transform("mean")).to_dict()

        frame["deseasonalized"] = frame["units"] / [
            self.dow_[(c, d)] for c, d in zip(frame["category"], frame["dow"])]
        recent = frame[frame["date"] > frame["date"].max() - pd.Timedelta(days=level_days)]
        self.level_ = (recent[recent["promo"] == 0]
                       .groupby(["store_code", "sku"])["deseasonalized"].mean().to_dict())
        level = frame.set_index(["store_code", "sku"]).index.map(self.level_)
        ratio = (frame["deseasonalized"] / np.asarray(level, dtype=float))[frame["promo"] == 1]
        self.uplift_ = ratio.groupby(frame.loc[frame["promo"] == 1, "sku"]).mean().to_dict()

        fitted = self.predict(recent)
        resid = recent["units"].to_numpy() - fitted
        self.sigma_ = (pd.Series(resid, index=recent.index)
                       .groupby([recent["store_code"], recent["sku"]]).std().to_dict())
        return self

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        category = frame["sku"].map(PRODUCTS.set_index("sku")["category"])
        dow = frame["date"].dt.dayofweek
        out = []
        for store, sku, cat, d, promo in zip(frame["store_code"], frame["sku"], category, dow,
                                             frame["promo"]):
            value = self.level_[(store, sku)] * self.dow_[(cat, d)]
            if promo:
                value *= self.uplift_.get(sku, PROMO_UPLIFT[cat])
            out.append(max(0.0, value))
        return np.asarray(out)


def wape(actual, prediction) -> float:
    denominator = float(np.abs(actual).sum())
    return 100 * float(np.abs(np.asarray(actual) - np.asarray(prediction)).sum()) / denominator \
        if denominator else 0.0


def _holdout(sales: pd.DataFrame, holdout_days: int) -> pd.DataFrame:
    """Holdout days with the model's out-of-sample forecast and last week's units next to actuals."""
    cutoff = sales["date"].max() - pd.Timedelta(days=holdout_days)
    train, test = sales[sales["date"] <= cutoff], sales[sales["date"] > cutoff].copy()
    model = SeasonalPromoForecaster().fit(train)
    test["model"] = model.predict(test)
    last_week = sales.assign(date=sales["date"] + pd.Timedelta(days=7))[
        ["store_code", "sku", "date", "units"]].rename(columns={"units": "last_week"})
    return test.merge(last_week, on=["store_code", "sku", "date"], how="left")


def accuracy_rows(sales: pd.DataFrame, holdout_days: int = 14) -> list[dict]:
    """Gold: one row per store-product and holdout day, planners' method vs the model.

    Absolute errors are stored in units so any slice (store, category, promo days) can be
    re-aggregated into WAPE by summing errors, never by averaging percentages.
    """
    test = _holdout(sales, holdout_days)
    meta = PRODUCTS.set_index("sku")[["product_name", "category"]]
    names = STORES.set_index("store_code")["store_name"]
    rows = []
    for r in test.itertuples():
        actual, baseline, model = float(r.units), float(r.last_week), float(r.model)
        rows.append({
            "store_code": r.store_code, "store_name": names[r.store_code], "sku": r.sku,
            "product_name": meta.at[r.sku, "product_name"], "category": meta.at[r.sku, "category"],
            "demand_date": r.date.strftime("%Y-%m-%d"), "promotion_days": int(r.promo),
            "actual_units": actual, "baseline_units": round(baseline, 1),
            "improved_units": round(model, 1),
            "baseline_abs_error": round(abs(actual - baseline), 3),
            "improved_abs_error": round(abs(actual - model), 3),
            "absolute_actual_units": abs(actual),
        })
    return rows


def backtest(sales: pd.DataFrame, holdout_days: int = 14) -> dict:
    """Out-of-sample check vs. how planners forecast today: same weekday last week."""
    test = _holdout(sales, holdout_days)
    model_wape = wape(test["units"], test["model"])
    current_wape = wape(test["units"], test["last_week"])
    return {"holdout_days": holdout_days, "model_wape": model_wape, "current_wape": current_wape,
            "error_reduction_pct": 100 * (current_wape - model_wape) / current_wape}


def _normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _normal_pdf(x: float) -> float:
    return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)


def _expected_shortfall(mu: float, sd: float, available: float) -> float:
    """E[max(demand - available, 0)] for normally distributed demand."""
    if sd <= 0:
        return max(0.0, mu - available)
    z = (mu - available) / sd
    return (mu - available) * _normal_cdf(z) + sd * _normal_pdf(z)


def build_snapshot(silver: dict | None = None) -> dict:
    """Gold: one risk row per store-product plus its 7-day projection."""
    silver = silver or unify(make_sources())
    sales = silver["sales"]
    model = SeasonalPromoForecaster().fit(sales)

    future = pd.DataFrame(
        [(s, p, AS_OF + pd.Timedelta(days=d))
         for s, p in model.level_ for d in range(HORIZON_DAYS)],
        columns=["store_code", "sku", "date"])
    promo_keys = set(zip(silver["promos"]["sku"], silver["promos"]["date"]))
    future["promo"] = [int((s, d) in promo_keys) for s, d in zip(future["sku"], future["date"])]
    future["forecast_units"] = model.predict(future)
    delivered = silver["deliveries"].groupby(["store_code", "sku", "date"])["confirmed_units"].sum()
    ordered = silver["deliveries"].groupby(["store_code", "sku", "date"])["ordered_units"].sum()
    future["delivery_units"] = [float(delivered.get(k, 0.0)) for k in
                                zip(future["store_code"], future["sku"], future["date"])]
    future["ordered_units"] = [float(ordered.get(k, 0.0)) for k in
                               zip(future["store_code"], future["sku"], future["date"])]

    stock = silver["inventory"].set_index(["store_code", "sku"])
    products = PRODUCTS.set_index("sku")
    suppliers = SUPPLIERS.set_index("supplier_id")
    stores = STORES.set_index("store_code")
    items, daily = [], []
    for (store_code, sku), frame in future.groupby(["store_code", "sku"], sort=True):
        product, inv = products.loc[sku], stock.loc[(store_code, sku)]
        supplier = suppliers.loc[product["supplier_id"]]
        days = [{"date": row.date.strftime("%Y-%m-%d"), "promo": int(row.promo),
                 "forecast_units": round(float(row.forecast_units), 1),
                 "delivery_units": row.delivery_units, "ordered_units": row.ordered_units}
                for row in frame.itertuples()]
        sigma = round(float(model.sigma_[(store_code, sku)]), 2)
        on_hand, expiry = float(inv["on_hand_units"]), int(inv["oldest_batch_days_to_expiry"])
        risk = assess(sku, on_hand, expiry, sigma, days)
        daily.extend({"store_code": store_code, "sku": sku, **row} for row in risk.pop("projection"))
        items.append({
            "store_code": store_code, "store_name": stores.loc[store_code, "store_name"],
            "sku": sku, "product_name": product["product_name"], "category": product["category"],
            "supplier_id": product["supplier_id"], "supplier_name": supplier["supplier_name"],
            "on_hand_units": on_hand, "days_to_expiry": expiry, "forecast_sigma": sigma, **risk,
        })

    items.sort(key=lambda item: -item["value_at_risk_eur"])
    plan_actions(items)
    return {"as_of": AS_OF.strftime("%Y-%m-%d"), "items": items, "daily": daily,
            "quality": silver["quality"], "backtest": backtest(sales)}


def assess(sku: str, on_hand: float, expiry: int, sigma: float, days: list[dict]) -> dict:
    """Stockout and waste risk for one store-product over the 7-day horizon.

    ``days`` holds one dict per day: date, promo, forecast_units, delivery_units, ordered_units.
    Used for the baseline and again after a simulated action changes stock or deliveries.
    """
    product = PRODUCTS.set_index("sku").loc[sku]
    on_hand, sigma, expiry = float(on_hand), float(sigma), int(expiry)
    days = [{**r, "promo": int(r["promo"]), **{k: float(r[k]) for k in (
        "forecast_units", "delivery_units", "ordered_units")}} for r in days]
    cum_mu, arrived, projected = 0.0, 0.0, on_hand
    p_stockout, shortfall, stockout_date, projection = 0.0, 0.0, None, []
    for n, row in enumerate(days, start=1):
        arrived += row["delivery_units"]  # deliveries land before opening
        projected += row["delivery_units"] - row["forecast_units"]
        cum_mu += row["forecast_units"]
        sd = sigma * math.sqrt(n)
        available = on_hand + arrived
        p_stockout = max(p_stockout, 1 - _normal_cdf((available - cum_mu) / sd) if sd else
                         float(cum_mu > available))
        shortfall = max(shortfall, _expected_shortfall(cum_mu, sd, available))
        if stockout_date is None and projected < 0:
            stockout_date = row["date"]
        projection.append({**row, "projected_stock": round(projected, 1)})

    waste_units = max(0.0, on_hand - sum(r["forecast_units"] for r in days[:expiry]))
    delivery = next((r for r in days if r["delivery_units"] > 0), None)
    avg_daily = sum(r["forecast_units"] for r in days) / len(days)
    lost_sales = shortfall * float(product["unit_price"])
    waste_value = waste_units * float(product["unit_cost"])
    if p_stockout >= STOCKOUT_THRESHOLD:
        status = "stockout"
    elif waste_units >= max(15.0, 0.2 * on_hand):
        status = "waste"
    elif p_stockout >= WATCH_THRESHOLD:
        status = "watch"
    else:
        status = "ok"
    return {
        "status": status,
        "stockout_probability": round(p_stockout, 3),
        "stockout_date": stockout_date,
        "days_of_cover": round(on_hand / avg_daily, 1) if avg_daily else None,
        "forecast_7d_units": round(sum(r["forecast_units"] for r in days), 1),
        "promo_days": sum(r["promo"] for r in days),
        "next_delivery_date": delivery["date"] if delivery else None,
        "next_delivery_units": float(delivery["delivery_units"]) if delivery else 0.0,
        "next_delivery_fill_pct": (round(100 * delivery["delivery_units"] / delivery["ordered_units"])
                                   if delivery and delivery["ordered_units"] else None),
        "expected_shortfall_units": round(shortfall, 1),
        "waste_units": round(waste_units, 1),
        "lost_sales_eur": round(lost_sales, 2),
        "waste_eur": round(waste_value, 2),
        "value_at_risk_eur": round(lost_sales + waste_value, 2),
        "projection": projection,
    }


def _shortage(item: dict) -> int:
    return math.ceil(item["expected_shortfall_units"] + item["forecast_sigma"])


def _split_evenly(total: int, weights: dict) -> dict:
    """Integer shares of ``total`` proportional to ``weights``; the shares add up to ``total``."""
    weight_sum = sum(weights.values())
    shares = {k: int(total * w / weight_sum) for k, w in weights.items()}
    leftover = total - sum(shares.values())
    for key in sorted(weights, key=lambda k: -(total * weights[k] / weight_sum - shares[k]))[:leftover]:
        shares[key] += 1
    return shares


def plan_actions(items: list[dict]) -> None:
    """Attach next-best actions to every item, allocating shared supply exactly once.

    Surplus units move to the stores losing the most first (policy: at least 20 units, enough
    shelf life on arrival). Whatever shortage remains goes into one consolidated order per
    alternative supplier (minimum 20 cases), split across the stores that need it.
    The copilot explains each action with supplier knowledge.
    """
    by_key = {(i["store_code"], i["sku"]): i for i in items}
    suppliers = SUPPLIERS.set_index("supplier_id")
    for item in items:
        item["actions"] = []

    surplus = {}
    for item in items:
        shelf_needed = TRANSFER_SHELF_DAYS.get(item["category"])
        if (item["status"] == "waste" and shelf_needed
                and item["days_to_expiry"] - 1 >= shelf_needed and item["waste_units"] >= MIN_TRANSFER):
            surplus[(item["store_code"], item["sku"])] = int(item["waste_units"])

    remaining, transfers = {}, []
    receivers = [i for i in items if i["status"] in ("stockout", "watch")]  # items are sorted by value at risk
    for item in receivers:
        need = _shortage(item)
        donors = sorted((k for k in surplus if k[1] == item["sku"] and surplus[k] >= MIN_TRANSFER),
                        key=lambda k: -surplus[k])
        for key in donors:
            units = min(surplus[key], need)
            if units < MIN_TRANSFER:
                continue
            surplus[key] -= units
            need -= units
            transfers.append((key, (item["store_code"], item["sku"]), units))
        remaining[(item["store_code"], item["sku"])] = need

    out_units = {}
    for donor_key, receiver_key, units in transfers:
        donor, receiver = by_key[donor_key], by_key[receiver_key]
        tid = f"transfer:{donor['store_code']}>{receiver['store_code']}:{donor['sku']}"
        arrival = (AS_OF + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        base = {"id": tid, "approvable": True, "units": units, "from_code": donor["store_code"],
                "to_code": receiver["store_code"], "arrival_date": arrival,
                "cost_eur": round(units * TRANSFER_COST_PER_UNIT, 2),
                "query": "store transfer chilled van run minimum units"}
        receiver["actions"].append({**base, "kind": "transfer", "from": donor["store_name"],
                                    "text": f"Transfer {units} units from {donor['store_name']} on "
                                            f"tomorrow's 06:00 chilled run. Request it in the store app "
                                            f"before 22:00 tonight; they would otherwise expire there."})
        donor["actions"].append({**base, "kind": "transfer_out", "to": receiver["store_name"],
                                 "text": f"Send {units} units to {receiver['store_name']} on tomorrow's "
                                         f"06:00 chilled run; they cannot sell them before they expire here."})
        out_units[donor_key] = out_units.get(donor_key, 0) + units

    # One consolidated order per alternative supplier and product.
    orders = {}
    for item in receivers:
        supplier = suppliers.loc[item["supplier_id"]]
        key = (item["store_code"], item["sku"])
        eligible = (supplier["alt_supplier"] and remaining[key] > 0
                    and item["next_delivery_fill_pct"] is not None
                    and item["next_delivery_fill_pct"] < ALT_SUPPLIER_FILL_PCT)
        if eligible:
            orders.setdefault((item["supplier_id"], item["sku"]), {})[item["store_code"]] = remaining[key]
    for (supplier_id, sku), needs in orders.items():
        supplier = suppliers.loc[supplier_id]
        order_units = max(ALT_MIN_CASES, math.ceil(sum(needs.values()) / CASE_UNITS)) * CASE_UNITS
        shares = _split_evenly(order_units, needs)
        product = PRODUCTS.set_index("sku").loc[sku]
        arrival = (AS_OF + pd.Timedelta(days=int(supplier["alt_lead_days"]))).strftime("%Y-%m-%d")
        premium = round(order_units * float(product["unit_cost"]) * supplier["alt_premium_pct"] / 100, 2)
        for store_code, units in shares.items():
            item = by_key[(store_code, sku)]
            item["actions"].append({
                "kind": "alt_supplier", "id": f"order:{supplier_id}:{sku}", "approvable": True,
                "units": units, "order_units": order_units, "cases": order_units // CASE_UNITS,
                "allocations": shares, "arrival_date": arrival, "cost_eur": premium,
                "text": f"Order {order_units // CASE_UNITS} cases ({order_units} units, the "
                        f"{ALT_MIN_CASES}-case minimum applies) from {supplier['alt_supplier']}, due "
                        f"{int(supplier['alt_lead_days'])} days out at +{int(supplier['alt_premium_pct'])}% "
                        f"cost. This store gets {units}, covering its {needs[store_code]} unit gap"
                        + (" plus a share of the minimum." if units > needs[store_code] else "."),
                "query": f"{supplier['supplier_name']} alternative supplier shortfall"})

    ordered = {(code, sku) for (_, sku), needs in orders.items() for code in needs}
    for item in receivers:
        supplier = suppliers.loc[item["supplier_id"]]
        key = (item["store_code"], item["sku"])
        if key not in ordered and remaining[key] > 0 and supplier["can_expedite"]:
            item["actions"].append({
                "kind": "expedite", "approvable": False,
                "text": f"Ask {supplier['supplier_name']} for an expedited drop of about "
                        f"{remaining[key]} units before the next scheduled delivery.",
                "query": f"{supplier['supplier_name']} expedited drop"})
        if item["promo_days"]:
            item["actions"].append({
                "kind": "promo", "approvable": False,
                "text": "Cap the promotion for this store or switch the hero product, and tell "
                        "marketing 48 hours ahead.",
                "query": "promotion supply risk confirmed below promo forecast"})
        item["actions"].append({
            "kind": "substitute", "approvable": False,
            "text": "Plan a substitute display so the shelf is never empty if the gap remains.",
            "query": f"substitutes for {item['product_name'].rsplit(' ', 1)[0]}"})

    for item in items:
        if item["status"] != "waste":
            continue
        left = int(item["waste_units"]) - out_units.get((item["store_code"], item["sku"]), 0)
        if left >= 5:
            supplier = suppliers.loc[item["supplier_id"]]
            item["actions"].append({
                "kind": "markdown", "approvable": False,
                "text": f"Mark down the {left} remaining units of the oldest batch following the "
                        f"{item['category'].lower()} markdown ladder.",
                "query": f"markdown ladder for {item['category']}"})
            item["actions"].append({
                "kind": "reduce_order", "approvable": False,
                "text": f"Reduce the next order by about {left} units.",
                "query": f"{supplier['supplier_name']} standing order change"})


def _effects(snapshot: dict, approved: set[str]) -> tuple[dict, dict]:
    """Stock changes and extra deliveries implied by approved actions, from the planned actions."""
    stock_delta: dict = {}
    extra_delivery: dict = {}
    seen = set()
    for item in snapshot["items"]:
        for action in item["actions"]:
            if action.get("id") not in approved or action["id"] in seen:
                continue
            seen.add(action["id"])
            if action["kind"] in ("transfer", "transfer_out"):
                sku = item["sku"]
                stock_delta[(action["from_code"], sku)] = stock_delta.get((action["from_code"], sku), 0) - action["units"]
                key = (action["to_code"], sku, action["arrival_date"])
                extra_delivery[key] = extra_delivery.get(key, 0) + action["units"]
            elif action["kind"] == "alt_supplier":
                for store_code, units in action["allocations"].items():
                    key = (store_code, item["sku"], action["arrival_date"])
                    extra_delivery[key] = extra_delivery.get(key, 0) + units
    return stock_delta, extra_delivery


def action_ids(snapshot: dict) -> set[str]:
    return {a["id"] for i in snapshot["items"] for a in i["actions"] if a.get("id")}


def apply_actions(snapshot: dict, approved: set[str]) -> dict:
    """Re-run the risk calculation as if the approved actions had happened (a simulation).

    Works on a snapshot alone, so it behaves the same for the local engine and for Gold
    tables read from Databricks. Returns a new snapshot with ``impact`` against the original.
    """
    unknown = approved - action_ids(snapshot)
    if unknown:
        raise ValueError(f"Unknown action: {sorted(unknown)[0]}")
    stock_delta, extra_delivery = _effects(snapshot, approved)
    rows = {}
    for row in snapshot["daily"]:
        rows.setdefault((row["store_code"], row["sku"]), []).append(row)

    items, daily = [], []
    for item in snapshot["items"]:
        key = (item["store_code"], item["sku"])
        days = [dict(r) for r in rows[key]]
        for r in days:
            r["delivery_units"] += extra_delivery.get((*key, r["date"]), 0)
        on_hand = item["on_hand_units"] + stock_delta.get(key, 0)
        changed = key in stock_delta or any(k[:2] == key for k in extra_delivery)
        new = dict(item)
        if changed:
            risk = assess(item["sku"], on_hand, item["days_to_expiry"], item["forecast_sigma"],
                          [{k: r[k] for k in ("date", "promo", "forecast_units", "delivery_units",
                                              "ordered_units")} for r in days])
            days = [{**r, **p} for r, p in zip(days, risk.pop("projection"))]
            new.update(risk, on_hand_units=on_hand)
        new["actions"] = [{**a, "approved": a.get("id") in approved} for a in item["actions"]]
        items.append(new)
        daily.extend(days)

    after = {**snapshot, "items": items, "daily": daily}
    after["impact"] = _impact(snapshot, after, approved)
    return after


def _impact(before: dict, after: dict, approved: set[str]) -> dict:
    def totals(snap):
        risky = [i for i in snap["items"] if i["status"] != "ok"]
        return {"value_at_risk": sum(i["value_at_risk_eur"] for i in risky),
                "stockouts": sum(i["status"] == "stockout" for i in risky),
                "waste": sum(i["status"] == "waste" for i in risky),
                "lost_sales": sum(i["lost_sales_eur"] for i in snap["items"]),
                "waste_eur": sum(i["waste_eur"] for i in snap["items"])}

    cost, seen = 0.0, set()
    for item in before["items"]:
        for action in item["actions"]:
            if action.get("id") in approved and action["id"] not in seen:
                seen.add(action["id"])
                cost += action["cost_eur"]
    b, a = totals(before), totals(after)
    return {"before": b, "after": a, "approved": sorted(approved), "action_cost_eur": round(cost, 2),
            "net_eur": round(b["value_at_risk"] - a["value_at_risk"] - cost, 2)}

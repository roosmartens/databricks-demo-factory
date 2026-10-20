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
HISTORY_DAYS = 56
HORIZON_DAYS = 7
DOW_FACTORS = (0.85, 0.85, 0.9, 0.95, 1.15, 1.3, 1.0)  # Monday..Sunday
STOCKOUT_THRESHOLD = 0.5
WATCH_THRESHOLD = 0.2

STORES = pd.DataFrame.from_records([
    {"store_id": 101, "store_code": "AMS-01", "store_name": "Amsterdam Centrum", "size": 1.35},
    {"store_id": 102, "store_code": "UTR-02", "store_name": "Utrecht Oudegracht", "size": 1.0},
    {"store_id": 103, "store_code": "RTM-03", "store_name": "Rotterdam Kop van Zuid", "size": 1.15},
    {"store_id": 104, "store_code": "EHV-04", "store_name": "Eindhoven Strijp", "size": 0.85},
])

PRODUCTS = pd.DataFrame.from_records([
    # sku, ean, name, category, shelf life (days), price, cost, supplier, base daily units
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

PROMO_UPLIFT = {"Fresh produce": 1.6, "Dairy": 1.35, "Bakery": 1.3, "Meat": 1.45}
# Planned "2+1" strawberry promotion from Thursday to Sunday of the demo week.
PLANNED_PROMOS = [("SKU-1001", 2, 5)]

# Scripted situations the demo walks through; everything else is business as usual.
# (store_code, sku): days of cover on hand, days until the oldest batch expires
STOCK_OVERRIDES = {
    ("AMS-01", "SKU-1001"): (0.9, 3),   # promo + harvest shortfall -> stockout first
    ("UTR-02", "SKU-1001"): (3.6, 2),   # over-ordered strawberries -> waste, transfer donor
    ("RTM-03", "SKU-1008"): (2.6, 1),   # sourdough over-baked -> waste
    ("EHV-04", "SKU-1006"): (1.1, 7),   # missed dairy delivery slot -> stockout
    ("UTR-02", "SKU-1009"): (4.2, 2),   # chicken over-stocked -> waste
    ("RTM-03", "SKU-1005"): (3.0, 4),   # avocados, ripening delay at port -> watch
}
# Supplier portal: (store_code or "*", sku) -> (first delivery day offset, confirmed fill rate)
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


def backtest(sales: pd.DataFrame, holdout_days: int = 14) -> dict:
    """Out-of-sample check vs. how planners forecast today: same weekday last week."""
    cutoff = sales["date"].max() - pd.Timedelta(days=holdout_days)
    train, test = sales[sales["date"] <= cutoff], sales[sales["date"] > cutoff].copy()
    model = SeasonalPromoForecaster().fit(train)
    test["model"] = model.predict(test)
    last_week = sales.assign(date=sales["date"] + pd.Timedelta(days=7))[
        ["store_code", "sku", "date", "units"]].rename(columns={"units": "last_week"})
    test = test.merge(last_week, on=["store_code", "sku", "date"], how="left")
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
    for (store_code, sku), days in future.groupby(["store_code", "sku"], sort=True):
        product, inv = products.loc[sku], stock.loc[(store_code, sku)]
        supplier = suppliers.loc[product["supplier_id"]]
        sigma = float(model.sigma_[(store_code, sku)])
        on_hand = float(inv["on_hand_units"])
        expiry = int(inv["oldest_batch_days_to_expiry"])

        cum_mu, arrived, projected = 0.0, 0.0, on_hand
        p_stockout, shortfall, stockout_date = 0.0, 0.0, None
        for n, row in enumerate(days.itertuples(), start=1):
            arrived += row.delivery_units  # deliveries land before opening
            projected += row.delivery_units - row.forecast_units
            cum_mu += row.forecast_units
            sd = sigma * math.sqrt(n)
            available = on_hand + arrived
            p_stockout = max(p_stockout, 1 - _normal_cdf((available - cum_mu) / sd) if sd else
                             float(cum_mu > available))
            shortfall = max(shortfall, _expected_shortfall(cum_mu, sd, available))
            if stockout_date is None and projected < 0:
                stockout_date = row.date.strftime("%Y-%m-%d")
            daily.append({"store_code": store_code, "sku": sku,
                          "date": row.date.strftime("%Y-%m-%d"), "promo": int(row.promo),
                          "forecast_units": round(float(row.forecast_units), 1),
                          "delivery_units": row.delivery_units,
                          "ordered_units": row.ordered_units,
                          "projected_stock": round(projected, 1)})

        sell_before_expiry = float(days["forecast_units"].iloc[:expiry].sum())
        waste_units = max(0.0, on_hand - sell_before_expiry)
        next_delivery = days[days["delivery_units"] > 0].head(1)
        avg_daily = float(days["forecast_units"].mean())
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
        items.append({
            "store_code": store_code, "store_name": stores.loc[store_code, "store_name"],
            "sku": sku, "product_name": product["product_name"], "category": product["category"],
            "supplier_id": product["supplier_id"], "supplier_name": supplier["supplier_name"],
            "status": status,
            "stockout_probability": round(p_stockout, 3),
            "stockout_date": stockout_date,
            "on_hand_units": on_hand, "days_to_expiry": expiry,
            "days_of_cover": round(on_hand / avg_daily, 1) if avg_daily else None,
            "forecast_7d_units": round(float(days["forecast_units"].sum()), 1),
            "promo_days": int(days["promo"].sum()),
            "next_delivery_date": (next_delivery["date"].iloc[0].strftime("%Y-%m-%d")
                                   if len(next_delivery) else None),
            "next_delivery_units": (float(next_delivery["delivery_units"].iloc[0])
                                    if len(next_delivery) else 0.0),
            "next_delivery_fill_pct": (round(100 * float(next_delivery["delivery_units"].iloc[0])
                                             / float(next_delivery["ordered_units"].iloc[0]))
                                       if len(next_delivery) else None),
            "expected_shortfall_units": round(shortfall, 1),
            "waste_units": round(waste_units, 1),
            "lost_sales_eur": round(lost_sales, 2),
            "waste_eur": round(waste_value, 2),
            "value_at_risk_eur": round(lost_sales + waste_value, 2),
            "forecast_sigma": round(sigma, 2),
        })

    items.sort(key=lambda item: -item["value_at_risk_eur"])
    # Each surplus unit is offered once, to the store-products losing the most first.
    surplus = {(i["store_code"], i["sku"]): i["waste_units"] for i in items
               if i["status"] == "waste" and i["waste_units"] >= 20}
    for item in items:
        item["actions"] = recommend_actions(item, items, surplus)
    return {"as_of": AS_OF.strftime("%Y-%m-%d"), "items": items, "daily": daily,
            "quality": silver["quality"], "backtest": backtest(sales)}


def recommend_actions(item: dict, items: list[dict], surplus: dict | None = None) -> list[dict]:
    """Structured next-best actions; the copilot explains them with supplier knowledge.

    ``surplus`` maps (store_code, sku) to units another store can give away; transfers
    planned here are subtracted from it.
    """
    surplus = {} if surplus is None else surplus
    actions = []
    supplier = SUPPLIERS.set_index("supplier_id").loc[item["supplier_id"]]
    peers = [p for p in items if p["sku"] == item["sku"] and p["store_code"] != item["store_code"]]
    if item["status"] in ("stockout", "watch"):
        need = math.ceil(item["expected_shortfall_units"] + item["forecast_sigma"])
        donors = sorted((p for p in peers if surplus.get((p["store_code"], p["sku"]), 0) >= 20),
                        key=lambda p: -surplus[(p["store_code"], p["sku"])])
        if donors:
            donor = donors[0]
            key = (donor["store_code"], donor["sku"])
            units = int(min(surplus[key], need))
            surplus[key] -= units
            need -= units
            actions.append({"kind": "transfer", "units": units, "from": donor["store_name"],
                            "text": f"Transfer {units} units from {donor['store_name']} on "
                                    f"tomorrow's 06:00 chilled run; they would otherwise expire there.",
                            "query": "store transfer chilled van run minimum units"})
        if supplier["alt_supplier"] and need > 0:
            units = max(need, 20)
            actions.append({"kind": "alt_supplier", "units": units,
                            "text": f"Order {units} units from {supplier['alt_supplier']} "
                                    f"({int(supplier['alt_lead_days'])}-day lead time, "
                                    f"+{int(supplier['alt_premium_pct'])}% cost).",
                            "query": f"{supplier['supplier_name']} alternative supplier shortfall"})
        elif supplier["can_expedite"]:
            actions.append({"kind": "expedite",
                            "text": f"Ask {supplier['supplier_name']} for an expedited drop "
                                    f"before the next scheduled delivery.",
                            "query": f"{supplier['supplier_name']} expedited drop"})
        if item["promo_days"]:
            actions.append({"kind": "promo", "text": "Cap the promotion for this store or switch "
                                                     "the hero product, and tell marketing 48 hours ahead.",
                            "query": "promotion supply risk confirmed below promo forecast"})
        actions.append({"kind": "substitute", "text": "Plan a substitute display so the shelf is "
                                                      "never empty if the gap remains.",
                        "query": f"substitutes for {item['product_name'].rsplit(' ', 1)[0]}"})
    elif item["status"] == "waste":
        receivers = [p for p in peers if p["status"] == "stockout"]
        if receivers and item["waste_units"] >= 20:
            name = receivers[0]["store_name"]
            actions.append({"kind": "transfer", "units": int(item["waste_units"]), "to": name,
                            "text": f"Send the {int(item['waste_units'])} units you cannot sell "
                                    f"in time to {name}, which is short.",
                            "query": "store transfer chilled van run minimum units"})
        actions.append({"kind": "markdown",
                        "text": f"Mark down the oldest batch following the {item['category'].lower()} "
                                f"markdown ladder.",
                        "query": f"markdown ladder for {item['category']}"})
        actions.append({"kind": "reduce_order",
                        "text": f"Reduce the next order by about {int(item['waste_units'])} units.",
                        "query": f"{supplier['supplier_name']} standing order change"})
    return actions

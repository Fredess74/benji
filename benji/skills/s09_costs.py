"""09 Calculate Energy Costs from confirmed bills (and optional user tariff inputs).

* Coverage is evaluated per meter/account: one complete meter cannot hide a second, incomplete meter.
* Fixed charges are kept apart from usage-based charges: savings estimates only use the usage-based rate,
  because customer charges remain after consumption falls. Demand charges are reported but never assumed
  to fall (no load model yet).
* Unknown bill amounts stay unknown (null). A known subtotal is shown with its coverage; missing prices are
  never turned into $0.
"""

from __future__ import annotations

from ..billing import (SUMMER_MONTHS, WINTER_MONTHS, as_date, bill_cost, bill_days, by_fuel, by_meter,
                       canonical_unit, charges, latest_window, mid_month, safe_canonical)
from ..units import to_kbtu
from .base import COMPLETED, NEEDS_DATA, Evidence, SkillContext, SkillResult

MIN_DAYS_FOR_ANNUALIZING = 180
MIN_DAYS_FOR_HEATING_SPLIT = 330
MAX_METER_END_SPREAD_DAYS = 35


def variable_cost(quantity: float, usage_rate: float) -> float:
    """Usage-based cost for a quantity at a flat usage-based rate."""
    return quantity * usage_rate


def heating_split(bills: list[dict], covered_days: int) -> tuple[dict | None, str | None]:
    """Split one year of gas use into baseload (hot water/cooking) and weather-sensitive heating.

    Requires >= 330 covered days including both summer (Jun-Aug) and winter (Dec-Feb) bills.
    Baseload = average daily use of SUMMER bills only (when space heating is off) x billing days.
    Labelled as a modelled estimate; not weather-normalised.
    """
    if covered_days < MIN_DAYS_FOR_HEATING_SPLIT:
        return None, (f"Needs about a full year of gas bills ({MIN_DAYS_FOR_HEATING_SPLIT}+ days); only "
                      f"{covered_days} days are covered.")
    pts = [(b, q, bill_days(b)) for b in bills if (q := safe_canonical(b)) is not None and bill_days(b) > 0]
    summer = [(q, d) for b, q, d in pts if mid_month(b) in SUMMER_MONTHS]
    winter = [b for b, _, _ in pts if mid_month(b) in WINTER_MONTHS]
    if sum(d for _, d in summer) < 28 or not winter:
        return None, "Needs gas bills from both summer (Jun-Aug) and winter (Dec-Feb) to separate heating from baseload."
    base_daily = sum(q for q, _ in summer) / sum(d for _, d in summer)
    total = sum(q for _, q, _ in pts)
    baseload = sum(min(q, base_daily * d) for _, q, d in pts)
    return {"total": round(total, 2), "baseload": round(baseload, 2), "heating": round(total - baseload, 2),
            "baseload_daily": round(base_daily, 3),
            "method": "Baseload = average daily gas use in summer bills (Jun-Aug) x billing days; the remainder of "
                      "one year of bills is attributed to space heating. Not weather-normalised.",
            "data_label": "modelled_estimate"}, None


def meter_summary(fuel: str, account: str, bills: list[dict]) -> tuple[list[dict], dict]:
    window, cov = latest_window(bills)
    return window, {"account": account, **cov, "bill_count": len(window)}


def fuel_summary(fuel: str, bills: list[dict], override: dict | None = None) -> dict:
    meters, window = [], []
    for (_, acct), mb in sorted(by_meter(bills).items()):
        w, m = meter_summary(fuel, acct, mb)
        meters.append(m)
        window += w
    ends = [as_date(m["window_end"]) for m in meters]
    starts = [as_date(m["window_start"]) for m in meters]
    spread = (max(ends) - min(ends)).days if ends else 0
    covered = min(m["covered_days"] for m in meters) if meters else 0
    complete = bool(meters) and all(m["complete"] for m in meters) and spread <= MAX_METER_END_SPREAD_DAYS
    cov = {"window_start": min(starts).isoformat() if starts else None,
           "window_end": max(ends).isoformat() if ends else None,
           "covered_days": covered, "window_days": 365, "complete": complete, "meter_count": len(meters),
           "meter_end_spread_days": spread}
    qty = sum(q for b in window if (q := safe_canonical(b)) is not None)
    split = {"fixed": 0.0, "variable": 0.0, "demand": 0.0, "tax_other": 0.0, "credits": 0.0, "unclassified": 0.0}
    classified_qty = 0.0
    for b in window:
        c = charges(b)
        for k in split:
            split[k] += c[k]
        if b.get("line_items"):
            classified_qty += safe_canonical(b) or 0.0
    costs = [bill_cost(b) for b in window]
    known = [c for c in costs if c is not None]
    all_known = bool(window) and len(known) == len(window)
    usage_rate, rate_source = None, None
    if override and override.get("usage_rate") is not None:
        usage_rate, rate_source = float(override["usage_rate"]), "user_tariff_input"
    elif classified_qty > 0 and split["variable"] > 0:
        usage_rate, rate_source = split["variable"] / classified_qty, "derived_from_bill_line_items"
    recorded_cost = round(sum(known), 2) if all_known else None
    out = {
        "fuel": fuel, "unit": canonical_unit(fuel), "coverage": cov, "meters": meters,
        "bill_ids": [b["id"] for b in window],
        "recorded_quantity": round(qty, 2), "recorded_kbtu": round(to_kbtu(fuel, qty), 1),
        "recorded_cost_usd": recorded_cost,
        "known_cost_subtotal_usd": round(sum(known), 2) if known else None,
        "cost_coverage": {"bills_with_cost": len(known), "bills_total": len(window)},
        "charges_usd": {k: round(v, 2) for k, v in split.items()},
        "usage_based_rate": round(usage_rate, 5) if usage_rate is not None else None,
        "usage_based_rate_source": rate_source,
        "average_all_in_rate": round(recorded_cost / qty, 5) if recorded_cost is not None and qty else None,
        "annual_quantity": None, "annual_cost_usd": None, "annualized": False,
    }
    if complete:
        out["annual_quantity"], out["annual_cost_usd"] = out["recorded_quantity"], recorded_cost
    elif covered >= MIN_DAYS_FOR_ANNUALIZING and len(meters) == 1:
        f = 365 / covered
        out["annual_quantity"] = round(qty * f, 2)
        out["annual_cost_usd"] = round(recorded_cost * f, 2) if recorded_cost is not None else None
        out["annualized"] = True
    if fuel == "natural_gas":
        out["heating_split"], out["heating_split_unavailable_reason"] = (
            heating_split(window, covered) if complete else
            (None, "Heating attribution needs 12 months of gas bills for every gas meter."))
    return out


def run(ctx: SkillContext) -> SkillResult:
    bills = ctx.confirmed_bills
    res = SkillResult("09", COMPLETED)
    if not bills:
        res.status = NEEDS_DATA
        res.message = "Confirm bills to calculate costs."
        return res
    overrides = ctx.settings.get("tariff_overrides", {})
    fuels = {f: fuel_summary(f, fb, overrides.get(f)) for f, fb in by_fuel(bills).items()}
    res.outputs = {"fuels": fuels}
    for f, s in fuels.items():
        cov = s["coverage"]
        if s["annualized"]:
            res.assumptions.append({
                "id": f"costs.annualized.{f}", "data_label": "assumption",
                "text": f"ASSUMPTION: {f} annual totals are scaled from {cov['covered_days']} recorded days "
                        f"to 365 days. Seasonal variation makes this uncertain."})
        if not cov["complete"] and not s["annualized"]:
            incomplete = [m["account"] for m in s["meters"] if not m["complete"]]
            res.warnings.append(f"{f}: no annual estimate. Incomplete meter(s): {', '.join(incomplete) or 'none'}"
                                + (f"; meter periods end {cov['meter_end_spread_days']} days apart" if
                                   cov["meter_end_spread_days"] > MAX_METER_END_SPREAD_DAYS else "") + ".")
        if s["recorded_cost_usd"] is None:
            cc = s["cost_coverage"]
            res.missing_inputs.append({"field": f"bills.{f}.total_usd",
                                       "action": f"Enter amounts for {cc['bills_total'] - cc['bills_with_cost']} of "
                                                 f"{cc['bills_total']} {f} bill(s); cost is shown only for known bills."})
        if s["usage_based_rate"] is None:
            res.missing_inputs.append({"field": f"tariff.{f}", "action": f"Add fixed vs. usage-based charges to {f} "
                                       "bills or enter the usage-based rate so savings can be priced."})
        if s["charges_usd"]["demand"] > 0:
            res.warnings.append(f"{f}: demand charges ${s['charges_usd']['demand']:,.2f} are not assumed to change "
                                "(no load model).")
        if s.get("heating_split"):
            res.assumptions.append({"id": f"costs.heating_split.{f}", "data_label": "modelled_estimate",
                                    "text": s["heating_split"]["method"]})
        elif f == "natural_gas":
            res.warnings.append(f"Heating attribution unavailable: {s['heating_split_unavailable_reason']}")
        cost_txt = (f"${s['recorded_cost_usd']:,.2f}" if s["recorded_cost_usd"] is not None else
                    f"cost unknown for {s['cost_coverage']['bills_total'] - s['cost_coverage']['bills_with_cost']} bill(s)"
                    + (f" (known subtotal ${s['known_cost_subtotal_usd']:,.2f})" if s["known_cost_subtotal_usd"] is not None else ""))
        res.evidence.append(Evidence(
            f"costs.{f}", f"{f}: {s['recorded_quantity']:,.0f} {s['unit']} and {cost_txt} recorded over "
            f"{cov['covered_days']} days ({cov['window_start']} to {cov['window_end']}, {cov['meter_count']} meter(s)).",
            "user_provided", value=s["recorded_cost_usd"]))
    res.message = "; ".join(
        f"{f}: " + (f"${s['recorded_cost_usd']:,.0f} recorded" if s["recorded_cost_usd"] is not None else "cost incomplete")
        for f, s in fuels.items())
    return res

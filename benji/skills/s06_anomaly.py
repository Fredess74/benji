"""06 Detect Unusual Consumption in the building's own history.

Method (deterministic, not weather-normalised):
* Convert each bill to average daily use (quantity / billing days) so period length
  does not create false alarms.
* Compare with the same billing month one year earlier when available (seasonal match);
  otherwise skip the bill rather than compare winter with summer.
* Flag changes beyond +/- threshold (default 25%). Record operating changes the user entered
  so a flagged change can be explained rather than assumed to be waste.
"""

from __future__ import annotations

from datetime import timedelta

from ..billing import as_date, bill_days, by_meter, canonical_unit, safe_canonical
from .base import COMPLETED, NEEDS_DATA, Evidence, SkillContext, SkillResult

DEFAULT_THRESHOLD = 0.25


def _mid(b):
    s, e = as_date(b["period_start"]), as_date(b["period_end"])
    return s + (e - s) / 2


def detect(bills: list[dict], operating_changes: list[dict], threshold: float = DEFAULT_THRESHOLD) -> dict:
    anomalies, compared, skipped = [], 0, 0
    for (fuel, account), fb in by_meter(bills).items():
        points = [(b, q / d) for b in fb if (q := safe_canonical(b)) is not None and (d := bill_days(b)) > 0]
        for b, daily in points:
            target = _mid(b) - timedelta(days=365)
            prior = [(p, v) for p, v in points if abs((_mid(p) - target).days) <= 16]
            if not prior:
                skipped += 1
                continue
            compared += 1
            p, pv = min(prior, key=lambda x: abs((_mid(x[0]) - target).days))
            if pv <= 0:
                continue
            change = daily / pv - 1
            if abs(change) >= threshold:
                start, end = as_date(b["period_start"]), as_date(b["period_end"])
                related = [oc for oc in operating_changes
                           if as_date(p["period_end"]) <= as_date(oc["date"]) <= end]
                anomalies.append({
                    "bill_id": b["id"], "compared_with_bill_id": p["id"], "fuel": fuel,
                    "period": [str(b["period_start"]), str(b["period_end"])],
                    "daily_use": round(daily, 2), "prior_year_daily_use": round(pv, 2),
                    "unit": f"{canonical_unit(fuel)}/day", "change_pct": round(change * 100, 1),
                    "direction": "increase" if change > 0 else "decrease",
                    "related_operating_changes": related,
                    "explanation": (
                        f"Average daily {fuel.replace('_', ' ')} use was {change * 100:+.0f}% versus the same period a "
                        f"year earlier. " + (
                            "The user recorded an operating change in between: "
                            + "; ".join(oc["description"] for oc in related) + "."
                            if related else
                            "No operating change was recorded; weather, occupancy, metering or equipment could "
                            "explain it. Benji does not weather-normalise yet.")),
                    "context_questions": [] if related else [
                        "Did occupancy, operating hours or tenants change in this period?",
                        "Was the bill based on an estimated meter read?",
                        "Was any heating, cooling or hot-water equipment repaired, replaced or left running?",
                    ],
                })
    return {"anomalies": anomalies, "periods_compared": compared, "periods_without_prior_year": skipped,
            "threshold_pct": threshold * 100, "weather_normalized": False}


def run(ctx: SkillContext) -> SkillResult:
    bills = ctx.confirmed_bills
    res = SkillResult("06", COMPLETED)
    if not bills:
        res.status = NEEDS_DATA
        res.message = "Confirm bills to analyse consumption history."
        return res
    thr = float(ctx.settings.get("anomaly_threshold", DEFAULT_THRESHOLD))
    out = detect(bills, ctx.building.get("operating_changes", []), thr)
    res.outputs = out
    if out["periods_compared"] == 0:
        res.status = NEEDS_DATA
        res.message = "Need at least 13 months of bills to compare each period with the prior year."
        res.missing_inputs.append({"field": "bills", "action": "Add bills from the previous year."})
        return res
    res.assumptions.append({"id": "anomaly.threshold", "text": f"Changes of {thr * 100:.0f}% or more are flagged.",
                            "data_label": "assumption"})
    res.warnings.append("Comparisons are not weather-normalised; a cold winter alone can raise heating use.")
    res.message = f"{len(out['anomalies'])} unusual period(s) found in {out['periods_compared']} compared."
    for a in out["anomalies"]:
        res.evidence.append(Evidence(f"anomaly.{a['bill_id']}", a["explanation"], "user_provided", value=a["change_pct"]))
    return res

"""03 Check Data Quality: gaps, overlaps, duplicates, units, implausible values, totals."""

from __future__ import annotations

from statistics import median

from ..billing import as_date, bill_days, by_meter, charges, latest_window, safe_canonical
from ..units import FUEL_UNITS
from .base import COMPLETED, NEEDS_DATA, Evidence, SkillContext, SkillResult


def _issue(code, severity, message, action, bill_ids=(), fuel=None):
    return {"code": code, "severity": severity, "message": message, "correction_action": action,
            "bill_ids": list(bill_ids), "fuel": fuel}


def check(bills: list[dict]) -> list[dict]:
    issues = []
    pending = [b for b in bills if b.get("status") != "confirmed"]
    if pending:
        issues.append(_issue("pending_confirmation", "warning",
                             f"{len(pending)} bill(s) are not confirmed and are excluded from analysis.",
                             "Review the extracted values and confirm or correct each bill.",
                             [b["id"] for b in pending]))
    confirmed = [b for b in bills if b.get("status") == "confirmed"]
    for b in confirmed:
        if b["unit"] not in FUEL_UNITS.get(b["fuel"], set()):
            issues.append(_issue("unit_mismatch", "error",
                                 f"Bill {b['id']}: unit '{b['unit']}' is not valid for {b['fuel']}.",
                                 "Correct the unit or the fuel type on this bill.", [b["id"]], b["fuel"]))
        days = bill_days(b)
        if days <= 0:
            issues.append(_issue("invalid_period", "error", f"Bill {b['id']}: period end is not after start.",
                                 "Correct the billing period dates.", [b["id"]], b["fuel"]))
        elif days < 20 or days > 40:
            issues.append(_issue("unusual_period_length", "info",
                                 f"Bill {b['id']}: {days}-day billing period (typical is 28-33).",
                                 "Confirm the dates; Benji normalises by days, so this is allowed.", [b["id"]], b["fuel"]))
        if float(b["quantity"]) < 0:
            issues.append(_issue("negative_quantity", "error", f"Bill {b['id']}: negative consumption.",
                                 "Correct the quantity (net-metering credits are not supported yet).", [b["id"]], b["fuel"]))
        items = b.get("line_items") or []
        if b.get("total_usd") is None:
            issues.append(_issue("missing_total", "warning", f"Bill {b['id']}: no total amount.",
                                 "Enter the bill total so costs can be calculated.", [b["id"]], b["fuel"]))
        elif items:
            s = sum(float(li["amount_usd"]) for li in items)
            if abs(s - float(b["total_usd"])) > max(1.0, 0.01 * abs(float(b["total_usd"]))):
                issues.append(_issue("line_items_mismatch", "warning",
                                     f"Bill {b['id']}: line items sum to ${s:,.2f} but total is ${float(b['total_usd']):,.2f}.",
                                     "Correct a line item or the total; cost splits use line items.", [b["id"]], b["fuel"]))
        else:
            issues.append(_issue("no_charge_breakdown", "info",
                                 f"Bill {b['id']}: no fixed/usage charge breakdown.",
                                 "Add the customer (fixed) charge so savings exclude charges that will not change.",
                                 [b["id"]], b["fuel"]))

    for (fuel, account), fb in by_meter(confirmed).items():
        # duplicates & overlaps (sorted by start)
        seen = {}
        for b in fb:
            key = (b.get("account"), str(b["period_start"]), str(b["period_end"]))
            if key in seen:
                issues.append(_issue("duplicate", "error",
                                     f"{fuel}: bills {seen[key]} and {b['id']} cover the same period.",
                                     "Delete the duplicate bill.", [seen[key], b["id"]], fuel))
            else:
                seen[key] = b["id"]
        for prev, cur in zip(fb, fb[1:]):
            if (prev.get("account"), str(prev["period_start"]), str(prev["period_end"])) == \
                    (cur.get("account"), str(cur["period_start"]), str(cur["period_end"])):
                continue
            gap = (as_date(cur["period_start"]) - as_date(prev["period_end"])).days
            if gap > 3:
                issues.append(_issue("missing_period", "warning",
                                     f"{fuel}: {gap}-day gap between {prev['period_end']} and {cur['period_start']}.",
                                     "Import or enter the missing bill.", [prev["id"], cur["id"]], fuel))
            elif gap < -1 and prev.get("account") == cur.get("account"):
                issues.append(_issue("overlap", "error",
                                     f"{fuel}: bills {prev['id']} and {cur['id']} overlap by {-gap} days.",
                                     "Correct the dates or remove one bill; overlapping usage would be double-counted.",
                                     [prev["id"], cur["id"]], fuel))
        # implausible daily usage vs this building's own median
        daily = [(b, q / d) for b in fb if (q := safe_canonical(b)) is not None and (d := bill_days(b)) > 0]
        if len(daily) >= 4:
            med = median(v for _, v in daily)
            for b, v in daily:
                if med > 0 and (v > 5 * med or (v == 0 and med > 0)):
                    issues.append(_issue("implausible_value", "warning",
                                         f"Bill {b['id']}: daily {fuel} use {v:,.1f} vs. typical {med:,.1f}.",
                                         "Check the quantity for a typo or estimated read.", [b["id"]], fuel))
        _, cov = latest_window(fb)
        if not cov["complete"]:
            issues.append(_issue("incomplete_year", "warning",
                                 f"{fuel} meter {account}: only {cov['covered_days']} of the last 365 days are covered.",
                                 "Add bills to cover 12 months; annual totals and benchmarking need a full year.",
                                 [], fuel))
    return issues


def run(ctx: SkillContext) -> SkillResult:
    issues = check(ctx.bills)
    res = SkillResult("03", COMPLETED)
    res.outputs = {
        "issues": issues,
        "counts": {s: sum(1 for i in issues if i["severity"] == s) for s in ("error", "warning", "info")},
        "blocking": any(i["severity"] == "error" for i in issues),
    }
    if not ctx.confirmed_bills:
        res.status = NEEDS_DATA
        res.message = "No confirmed bills to check."
        return res
    errs = res.outputs["counts"]["error"]
    res.message = (f"{errs} error(s) must be fixed before results are reliable." if errs
                   else f"No blocking issues. {len(issues)} note(s).")
    res.evidence.append(Evidence("quality.summary", res.message, "user_provided", value=res.outputs["counts"]))
    return res

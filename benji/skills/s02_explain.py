"""02 Explain Energy Bills: charge categories and bill-to-bill changes.

Change decomposition for usage-based charges between bill A and B
(p = usage-based charges / quantity):
    consumption effect = (qB - qA) * pA
    price effect       = (pB - pA) * qB
    fixed change       = fixedB - fixedA
These sum exactly to the change in (usage-based + fixed) charges.
"""

from __future__ import annotations

from ..billing import bill_cost, bill_days, by_meter, canonical_quantity, canonical_unit, charges
from .base import COMPLETED, NEEDS_DATA, Evidence, SkillContext, SkillResult


def explain_bill(b: dict) -> dict:
    c = charges(b)
    q = canonical_quantity(b)
    usage_based = c["variable"] if b.get("line_items") else None
    return {
        "bill_id": b["id"], "fuel": b["fuel"], "period": [str(b["period_start"]), str(b["period_end"])],
        "days": bill_days(b), "quantity": round(q, 2), "unit": canonical_unit(b["fuel"]),
        "total_usd": b.get("total_usd"), "charges": {k: round(v, 2) for k, v in c.items()},
        "usage_based_rate": round(usage_based / q, 5) if usage_based and q else None,
        "average_all_in_rate": round(float(b["total_usd"]) / q, 5) if b.get("total_usd") and q else None,
        "classification_complete": bool(b.get("line_items")),
    }


def compare(a: dict, b: dict) -> dict:
    ea, eb = explain_bill(a), explain_bill(b)
    ca, cb = bill_cost(a), bill_cost(b)
    out = {"from_bill": a["id"], "to_bill": b["id"], "fuel": a["fuel"], "account": a.get("account"),
           "total_change_usd": round(cb - ca, 2) if ca is not None and cb is not None else None,
           "quantity_change": round(eb["quantity"] - ea["quantity"], 2),
           "days_change": eb["days"] - ea["days"]}
    if ea["usage_based_rate"] is not None and eb["usage_based_rate"] is not None:
        qa, qb, pa, pb = ea["quantity"], eb["quantity"], ea["usage_based_rate"], eb["usage_based_rate"]
        out["consumption_effect_usd"] = round((qb - qa) * pa, 2)
        out["price_effect_usd"] = round((pb - pa) * qb, 2)
        out["fixed_change_usd"] = round(eb["charges"]["fixed"] - ea["charges"]["fixed"], 2)
        out["demand_change_usd"] = round(eb["charges"]["demand"] - ea["charges"]["demand"], 2)
        out["other_change_usd"] = round(eb["charges"]["tax_other"] - ea["charges"]["tax_other"], 2)
        out["method"] = "Usage-based charges split into consumption and price effects."
        parts = []
        if abs(out["consumption_effect_usd"]) >= 1:
            parts.append(f"{'more' if out['consumption_effect_usd'] > 0 else 'less'} usage "
                         f"({out['consumption_effect_usd']:+,.2f} USD)")
        if abs(out["price_effect_usd"]) >= 1:
            parts.append(f"{'higher' if out['price_effect_usd'] > 0 else 'lower'} usage-based rate "
                         f"({out['price_effect_usd']:+,.2f} USD)")
        if abs(out["fixed_change_usd"]) >= 1:
            parts.append(f"fixed charges {out['fixed_change_usd']:+,.2f} USD")
        out["summary"] = "Change driven by " + (", ".join(parts) if parts else "no material change") + "."
        if out["days_change"]:
            out["summary"] += f" The later bill has {out['days_change']:+d} billing day(s)."
    else:
        out["method"] = "Charge breakdown missing; consumption and price effects cannot be separated."
        out["summary"] = ("Add fixed and usage-based charges to both bills to separate a price change "
                          "from a consumption change.")
    return out


def run(ctx: SkillContext) -> SkillResult:
    bills = ctx.confirmed_bills
    res = SkillResult("02", COMPLETED)
    if not bills:
        res.status = NEEDS_DATA
        res.message = "Confirm at least one bill to explain charges."
        return res
    explained, changes = [], []
    for _meter, fb in by_meter(bills).items():  # never compare bills from different meters
        explained += [explain_bill(b) for b in fb]
        changes += [compare(a, b) for a, b in zip(fb, fb[1:])]
    res.outputs = {"bills": explained, "changes": changes}
    unclassified = [e["bill_id"] for e in explained if not e["classification_complete"]]
    if unclassified:
        res.warnings.append(f"{len(unclassified)} bill(s) lack a charge breakdown; price vs. usage effects unavailable.")
    res.message = f"Explained {len(explained)} bill(s) and {len(changes)} bill-to-bill change(s)."
    res.evidence.append(Evidence("bills.explained", res.message, "user_provided"))
    return res

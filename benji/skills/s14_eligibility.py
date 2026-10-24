"""14 Check Program Eligibility against explicitly represented criteria.

Statuses: "Potentially eligible", "Known condition not met", "More information needed".
Final approval always remains with the program operator.
"""

from __future__ import annotations

from .base import COMPLETED, NEEDS_DATA, Evidence, SkillContext, SkillResult
from .s13_incentives import catalog

POTENTIAL = "Potentially eligible"
NOT_MET = "Known condition not met"
MORE_INFO = "More information needed"
BUILDING_FIELDS = {"category", "dwelling_units", "state", "electric_utility", "gas_utility", "heating_fuel",
                   "owner_occupied_primary_residence", "income_eligible", "occupant_role"}


def _resolve(value):
    if isinstance(value, str) and value.startswith("$mass_save_"):
        return catalog()["mass_save_sponsors"][value.removeprefix("$mass_save_")]
    return value


def _get(building: dict, field: str):
    if field in BUILDING_FIELDS:
        return building.get(field)
    return (building.get("eligibility_answers") or {}).get(field)


def evaluate_condition(building: dict, cond: dict) -> dict:
    actual, target, op = _get(building, cond["field"]), _resolve(cond["value"]), cond["op"]
    if actual is None:
        state = "unknown"
    elif op == "eq":
        state = "met" if (str(actual).upper() == str(target).upper() if isinstance(target, str) else actual == target) else "not_met"
    elif op == "in":
        state = "met" if actual in target else "not_met"
    elif op == "gte":
        state = "met" if float(actual) >= float(target) else "not_met"
    elif op == "lte":
        state = "met" if float(actual) <= float(target) else "not_met"
    else:
        state = "unknown"
    return {"field": cond["field"], "description": cond["description"], "state": state, "actual": actual}


def evaluate(building: dict, record: dict) -> dict:
    checks = [evaluate_condition(building, c) for c in record["conditions"]]
    if building.get("category") not in record["sectors"]:
        checks.append({"field": "category", "description": f"Program serves {', '.join(record['sectors'])}",
                       "state": "not_met", "actual": building.get("category")})
    if any(c["state"] == "not_met" for c in checks):
        status = NOT_MET
    elif any(c["state"] == "unknown" for c in checks):
        status = MORE_INFO
    else:
        status = POTENTIAL
    return {
        "incentive_id": record["id"], "name": record["name"], "status": status, "checks": checks,
        "questions": [c["description"] for c in checks if c["state"] == "unknown"],
        "verification_status": record["verification_status"], "verified_on": record["verified_on"],
        "source_url": record["source_url"], "incentive_type": record["incentive_type"], "timing": record["timing"],
        "preapproval_required": record["preapproval_required"], "stacking_group": record["stacking_group"],
        "amount": record["amount"], "measures": record["measures"],
        "disclaimer": "Final eligibility and amounts are determined by the program operator.",
    }


def run(ctx: SkillContext) -> SkillResult:
    res = SkillResult("14", COMPLETED)
    found = ctx.result("13")
    if not found:
        res.status = NEEDS_DATA
        res.message = "Run 'Find Energy Incentives' (13) first."
        return res
    results = []
    for m in found.outputs["matches"]:
        ev = evaluate(ctx.building, m["record"])
        ev["benji_measures"] = m["benji_measures"]
        results.append(ev)
    res.outputs = {"results": results,
                   "counts": {s: sum(1 for r in results if r["status"] == s) for s in (POTENTIAL, NOT_MET, MORE_INFO)}}
    for r in results:
        res.evidence.append(Evidence(f"eligibility.{r['incentive_id']}", f"{r['name']}: {r['status']}",
                                     "assumption" if r["verification_status"] != "verified" else "public_historical",
                                     r["source_url"]))
        if r["preapproval_required"]:
            res.warnings.append(f"{r['name']}: pre-approval is required before purchasing equipment.")
    res.message = ", ".join(f"{v} {k.lower()}" for k, v in res.outputs["counts"].items())
    return res

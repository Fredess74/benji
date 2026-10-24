"""08 Room Heating & Cooling Scenario (bounded replacement for 'Investigate Heat Loss').

Runs every saved room scenario for the building through the single-zone model in benji/thermal.py.
It does NOT infer heat loss from monthly bills or from floor area. When a scenario has no price, the
usage-based rate from skill 09 (validated bills) is used if available and labelled as such.
"""

from __future__ import annotations

from pydantic import ValidationError

from .. import thermal
from .base import COMPLETED, NEEDS_DATA, Evidence, SkillContext, SkillResult


def run(ctx: SkillContext) -> SkillResult:
    res = SkillResult("08", COMPLETED)
    if not ctx.thermal_scenarios:
        res.status = NEEDS_DATA
        res.message = ("No room scenario saved. Add a room with temperatures, heat-loss coefficient (or surfaces), "
                       "thermal capacity and the system's thermal output to estimate warm-up / cool-down.")
        res.missing_inputs.append({"field": "thermal_scenarios", "action": "Create a room scenario."})
        return res
    costs = ctx.result("09")
    prices = {}
    for carrier, s in (costs.outputs["fuels"] if costs else {}).items():
        if s.get("usage_based_rate") is not None:
            prices[carrier] = {"rate": s["usage_based_rate"],
                               "source": f"usage-based {carrier} rate from confirmed bills (skill 09)"}
    rows = []
    for sc in ctx.thermal_scenarios:
        base = dict(sc["inputs"])
        price_note = None
        carrier = (base.get("hvac") or {}).get("carrier")
        if base.get("energy_price_usd_per_unit") is None and carrier in prices:
            base["energy_price_usd_per_unit"] = prices[carrier]["rate"]
            base["energy_price_source"] = prices[carrier]["source"]
            price_note = base["energy_price_source"]
        try:
            out = thermal.compare(base, sc.get("alternatives", []), prices)
        except (ValidationError, ValueError) as exc:
            rows.append({"id": sc["id"], "name": sc.get("name"), "status": "invalid_input", "message": str(exc)[:500]})
            continue
        rows.append({"id": sc["id"], "name": sc.get("name"), "add_to_plan": sc.get("add_to_plan", False),
                     "selected_alternative": sc.get("selected_alternative"), "price_note": price_note,
                     "data_label": ctx.building.get("data_label", "user_provided"), **out})
        cur = out["scenarios"][0]
        res.evidence.append(Evidence(f"thermal.{sc['id']}", f"{sc.get('name')}: {cur.get('message')}",
                                     "modelled_estimate"))
        for m in cur.get("missing", []):
            res.missing_inputs.append({"field": f"{sc['id']}.{m['field']}", "action": m["message"]})
    res.outputs = {"scenarios": rows, "limitations": thermal.LIMITATIONS, "model": "single_zone_rc_v1"}
    ok = sum(1 for r in rows if r.get("scenarios") and r["scenarios"][0]["status"] not in ("needs_data",))
    res.message = f"{ok} of {len(rows)} room scenario(s) calculated."
    if ok == 0:
        res.status = NEEDS_DATA
    return res

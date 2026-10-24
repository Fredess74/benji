"""10 Estimate Savings & Payback for the supported measure catalog.

* Each measure is evaluated stand-alone and inside scenarios.
* Scenarios apply measures in a fixed physical order on a shared state (remaining heating gas,
  electricity), so overlapping measures never double-count savings.
* Consumption, operating cost and emissions are reported separately; a scenario may cut
  emissions while raising operating cost and that increase is shown, not hidden.
* Two financial views: "confirmed" (only incentives the user confirmed with the program) and
  "hypothetical" (adds potentially eligible incentives with user-entered amounts).
"""

from __future__ import annotations

from .. import berdo, readiness
from ..catalog.measures import ASSUMPTIONS, MEASURES
from ..finance import project_financials
from .base import COMPLETED, NEEDS_DATA, Evidence, SkillContext, SkillResult
from ..validation import validate_measure_params
from .s14_eligibility import NOT_MET

PRESET_SCENARIOS = {
    "low_cost_first": ["operations_schedule_review", "thermostat_setback", "led_lighting"],
    "envelope_then_electrification": ["weatherization", "thermostat_setback", "heat_pump_heating"],
}
# "applied" is deliberately absent: a submitted application is pending, not money.
CONFIRMED_DECISIONS = {"approved", "disbursed"}
APPROVAL_EVIDENCE = ("reported_by", "reported_on", "reference")


def _heating_efficiency(building: dict):
    for e in building.get("equipment", []):
        if e.get("kind") in ("boiler", "furnace") and e.get("efficiency") and e.get("efficiency_unit") in (
                "AFUE", "thermal_efficiency"):
            return float(e["efficiency"]) / 100  # validated as percent (50-100) by the model
    return None


def applicability(measure_id: str, building: dict, costs: dict) -> tuple[bool, list[str]]:
    m = MEASURES[measure_id]
    reasons = []
    if building.get("category") not in m["categories"]:
        return False, [f"Not supported for {building.get('category')}"]
    if measure_id == "led_lighting" and (building.get("lighting") or {}).get("technology") == "led":
        return False, ["Lighting is already LED."]
    if measure_id == "thermostat_setback" and (building.get("schedule") or {}).get("heating_setback_in_place"):
        return False, ["A heating set-back is already in place."]
    fuel = building.get("heating_fuel")
    if measure_id == "heat_pump_heating" and fuel == "heat_pump":
        return False, ["Heating is already a heat pump."]
    if measure_id in ("heat_pump_heating", "thermostat_setback") and fuel != "natural_gas":
        return False, [f"Savings calculation supports gas-heated buildings only in this version (heating fuel: "
                       f"{fuel or 'unknown'}). Use an energy assessment instead."]
    return True, reasons


def _new_state(costs: dict) -> dict:
    gas = costs["fuels"].get("natural_gas", {})
    split = gas.get("heating_split") or {}
    return {"heating_therms": split.get("heating"), "annual_gas_therms": gas.get("annual_quantity"),
            "annual_kwh": costs["fuels"].get("electricity", {}).get("annual_quantity")}


def _apply(measure_id: str, building: dict, costs: dict, params: dict, state: dict) -> dict:
    """Apply one measure to `state` (mutated). Returns energy deltas (negative = reduction)."""
    m = MEASURES[measure_id]
    out = {"measure_id": measure_id, "kind": m["kind"], "delta": {"electricity_kwh": 0.0, "natural_gas_therms": 0.0},
           "missing": [], "assumptions": [], "notes": []}
    params, errors = validate_measure_params(measure_id, params)
    if errors:
        out["status"] = "invalid_input"
        out["input_errors"] = errors
        out["missing"] = [f"{e['field']}: {e['message']}" for e in errors]
        return out
    if m["kind"] == "assessment":
        out["status"] = "assessment_only"
        out["notes"].append("No savings are estimated until the assessment is done.")
        return out
    if measure_id == "thermostat_setback":
        if state["heating_therms"] is None:
            out["missing"].append("12 months of gas bills (to separate heating from baseload)")
        a = ASSUMPTIONS["thermostat_setback_fraction"]
        frac = params.get("savings_fraction", a["value"])
        if out["missing"]:
            out["status"] = "needs_data"
            return out
        saved = state["heating_therms"] * frac
        state["heating_therms"] -= saved
        out["delta"]["natural_gas_therms"] = -saved
        out["assumptions"].append({"id": "thermostat_setback_fraction", "value": frac, "data_label": "assumption",
                                   "text": f"ASSUMPTION: {frac:.0%} of heating gas saved. {a['basis']}",
                                   "source_url": a["source_url"], "verification_status": a["verification_status"]})
    elif measure_id == "led_lighting":
        L = building.get("lighting") or {}
        n, w, hrs = L.get("fixture_count"), L.get("existing_watts_per_fixture"), L.get("annual_operating_hours")
        pw = params.get("proposed_watts_per_fixture")
        for label, v in [("fixture count", n), ("existing watts per fixture", w), ("annual operating hours", hrs),
                         ("proposed LED watts per fixture (from quote/spec)", pw)]:
            if v is None:
                out["missing"].append(label)
        if out["missing"]:
            out["status"] = "needs_data"
            return out
        if pw >= w:
            out["status"] = "no_savings"
            out["notes"].append("Proposed fixtures do not use less power.")
            return out
        kwh = n * (w - pw) * hrs / 1000
        if state["annual_kwh"] is not None and kwh > state["annual_kwh"]:
            out["status"] = "needs_data"
            out["missing"].append(f"Lighting inputs imply {kwh:,.0f} kWh saved, more than the building's annual "
                                  f"{state['annual_kwh']:,.0f} kWh. Check fixture count, wattage and hours.")
            return out
        out["delta"]["electricity_kwh"] = -kwh
        out["notes"].append("Lower lighting heat slightly increases winter heating load; not modelled.")
        out["assumptions"].append({"id": "led.hours", "value": hrs, "data_label": building.get("data_label", "user_provided"),
                                   "text": f"{n} fixtures x ({w:g} W - {pw:g} W) x {hrs:,.0f} h/yr / 1000."})
    elif measure_id == "heat_pump_heating":
        eff = (params["existing_efficiency_pct"] / 100 if "existing_efficiency_pct" in params
               else _heating_efficiency(building))
        cop = params.get("seasonal_cop")
        cov = params.get("coverage_fraction", 1.0)
        if state["heating_therms"] is None:
            out["missing"].append("12 months of gas bills (to separate heating from baseload)")
        if not eff:
            out["missing"].append("existing boiler/furnace efficiency (AFUE)")
        if cop is None:
            out["missing"].append("heat-pump seasonal COP from a contractor proposal or equipment specification")
        if out["missing"]:
            out["status"] = "needs_data"
            return out
        displaced = state["heating_therms"] * cov
        delivered_kbtu = displaced * 100 * eff
        kwh = delivered_kbtu / (cop * 3.412)
        state["heating_therms"] -= displaced
        out["delta"]["natural_gas_therms"] = -displaced
        out["delta"]["electricity_kwh"] = kwh
        out["assumptions"].append({"id": "heat_pump.cop", "value": cop, "data_label": building.get("data_label", "user_provided"), "source": params.get("cop_source"),
                                   "text": f"Seasonal COP {cop:g}, existing efficiency {eff:.0%}, {cov:.0%} of heating "
                                           f"displaced. Delivered heat {delivered_kbtu:,.0f} kBtu / (COP x 3.412)."})
        out["notes"].append("Gas fixed charges remain while gas service stays connected (e.g. for hot water).")
        out["notes"].append("Uses a SEASONAL COP for annual energy; cold-weather capacity and backup heat need the "
                            "room scenario (skill 08) and a contractor sizing calculation.")
        out["electrification_readiness"] = readiness.checklist(building)
    out["status"] = "estimated"
    return out


def _price(delta: dict, costs: dict, ef: dict) -> dict:
    fuels = costs["fuels"]
    missing, cost = [], 0.0
    for fuel, key in (("electricity", "electricity_kwh"), ("natural_gas", "natural_gas_therms")):
        if abs(delta[key]) < 1e-9:
            continue
        rate = fuels.get(fuel, {}).get("usage_based_rate")
        if rate is None:
            missing.append(f"usage-based {fuel} rate")
        else:
            cost += delta[key] * rate
    emissions = delta["electricity_kwh"] * ef["electricity_kg_per_kwh"] + delta["natural_gas_therms"] * ef["natural_gas_kg_per_therm"]
    return {
        "annual_operating_cost_change_usd": None if missing else round(cost, 2),
        "annual_operating_savings_usd": None if missing else round(-cost, 2),
        "annual_emissions_change_kgco2e": round(emissions, 1),
        "missing_rates": missing,
    }


def _incentives_for(measure_id: str, eligibility: list[dict], decisions: dict) -> dict:
    inc_measure = MEASURES[measure_id]["incentive_measure"]
    confirmed, hypothetical, listed = [], [], []
    for r in eligibility:
        if inc_measure not in r["measures"]:
            continue
        d = decisions.get(r["incentive_id"], {}) or {}
        status = d.get("status", "not_reviewed")
        status = "approved" if status == "confirmed_by_program" else status
        evidence_missing = [f for f in APPROVAL_EVIDENCE if not d.get(f)] if status in CONFIRMED_DECISIONS else []
        entry = {"id": r["incentive_id"], "name": r["name"], "incentive_type": r["incentive_type"],
                 "timing": r["timing"], "stacking_group": r["stacking_group"], "amount_usd": d.get("amount_usd"),
                 "eligibility_status": r["status"], "decision_status": status,
                 "approval_evidence": {f: d.get(f) for f in APPROVAL_EVIDENCE},
                 "approval_reported_by_user": status in CONFIRMED_DECISIONS,
                 "evidence_missing": evidence_missing,
                 "verification_status": r["verification_status"], "source_url": r["source_url"],
                 "preapproval_required": r["preapproval_required"]}
        if status == "applied":
            entry["note"] = "Application submitted: pending, not counted as confirmed money."
        elif evidence_missing:
            entry["note"] = "Approval reported without " + ", ".join(evidence_missing) + "; kept hypothetical."
        listed.append(entry)
        if r["status"] == NOT_MET or status == "rejected" or entry["amount_usd"] is None:
            continue
        if status in CONFIRMED_DECISIONS and not evidence_missing:
            confirmed.append(entry)
        hypothetical.append(entry)
    return {"listed": listed, "confirmed": confirmed, "hypothetical": hypothetical}


def _finance_block(gross, inc: dict, savings, budget, cash) -> dict:
    return {"confirmed": {**project_financials(gross, inc["confirmed"], savings, budget, cash),
                          "label": "confirmed - only incentives with user-reported approval evidence"},
            "hypothetical": {**project_financials(gross, inc["hypothetical"], savings, budget, cash),
                             "label": "hypothetical - includes incentives not yet approved by the program"}}


def evaluate_scenario(name: str, measure_ids: list[str], building: dict, costs: dict, inputs: dict,
                      eligibility: list[dict], ef: dict) -> dict:
    ids = sorted(dict.fromkeys(measure_ids), key=lambda m: MEASURES[m]["order"])
    state = _new_state(costs)
    steps, total = [], {"electricity_kwh": 0.0, "natural_gas_therms": 0.0}
    for m in ids:
        r = _apply(m, building, costs, (inputs.get(m) or {}).get("params", {}), state)
        steps.append(r)
        for k in total:
            total[k] += r["delta"][k]
    standalone = {"electricity_kwh": 0.0, "natural_gas_therms": 0.0}
    for m in ids:
        r = _apply(m, building, costs, (inputs.get(m) or {}).get("params", {}), _new_state(costs))
        for k in standalone:
            standalone[k] += r["delta"][k]
    price = _price(total, costs, ef)
    if all(s["status"] in ("assessment_only", "needs_data", "invalid_input") for s in steps):
        # Nothing was estimated: report unknown savings rather than zero savings.
        price.update({"annual_operating_cost_change_usd": None, "annual_operating_savings_usd": None,
                      "annual_emissions_change_kgco2e": None})
    priced = [m for m in ids if (inputs.get(m) or {}).get("quoted_cost_usd") is not None]
    unpriced_calc = [m for m in ids if m not in priced and MEASURES[m]["kind"] != "assessment"]
    unpriced_assess = [m for m in ids if m not in priced and MEASURES[m]["kind"] == "assessment"]
    # Unknown cost stays unknown: never show $0 for something nobody has priced.
    gross = None if (unpriced_calc or not priced) else sum(float(inputs[m]["quoted_cost_usd"]) for m in priced)
    inc = {"confirmed": [], "hypothetical": []}
    for m in ids:
        mi = _incentives_for(m, eligibility, (inputs.get(m) or {}).get("incentive_status", {}))
        inc["confirmed"] += mi["confirmed"]
        inc["hypothetical"] += mi["hypothetical"]
    return {
        "scenario": name, "measures": ids, "steps": steps,
        "annual_energy_change": {k: round(v, 1) for k, v in total.items()},
        "sum_of_standalone_changes": {k: round(v, 1) for k, v in standalone.items()},
        "interaction_note": "Measures are applied in sequence on the remaining heating load, so combined savings "
                            "can be smaller than the sum of stand-alone savings.",
        **price,
        "operating_cost_increases": price["annual_operating_cost_change_usd"] is not None and price["annual_operating_cost_change_usd"] > 0,
        "unpriced_measures": unpriced_calc, "unpriced_assessments": unpriced_assess,
        "cost_complete": not unpriced_calc and not unpriced_assess,
        "financials": _finance_block(gross, inc, price["annual_operating_savings_usd"], building.get("budget_usd"),
                                     building.get("upfront_cash_available_usd")),
        "incomplete": any(s["status"] in ("needs_data", "invalid_input") for s in steps),
    }


def run(ctx: SkillContext) -> SkillResult:
    res = SkillResult("10", COMPLETED)
    costs = ctx.result("09")
    if not costs:
        res.status = NEEDS_DATA
        res.message = "Energy costs (skill 09) are required before estimating savings."
        return res
    b = ctx.building
    ef = berdo.emission_factors()
    elig_res = ctx.result("14")
    eligibility = elig_res.outputs["results"] if elig_res else []
    if not elig_res:
        res.warnings.append("Eligibility (skill 14) not run: financial views exclude all incentives.")
    measures = []
    for m in sorted(MEASURES, key=lambda k: MEASURES[k]["order"]):
        ok, reasons = applicability(m, b, costs.outputs)
        if not ok:
            measures.append({"measure_id": m, "name": MEASURES[m]["name"], "applicable": False, "reasons": reasons})
            continue
        sc = evaluate_scenario(m, [m], b, costs.outputs, ctx.measure_inputs, eligibility, ef)
        step = sc["steps"][0]
        if MEASURES[m]["kind"] == "assessment":
            for view in sc["financials"].values():
                view["payback"] = {"years": None, "reason": "Assessment: no savings are estimated until it is done."}
        inp = ctx.measure_inputs.get(m) or {}
        measures.append({
            "measure_id": m, "name": MEASURES[m]["name"], "applicable": True, "kind": MEASURES[m]["kind"],
            "status": step["status"], "missing": step["missing"], "input_errors": step.get("input_errors", []),
            "assumptions": step["assumptions"], "notes": step["notes"],
            "electrification_readiness": step.get("electrification_readiness"),
            "method": MEASURES[m]["method"], "uncertainty": MEASURES[m]["uncertainty"],
            "dependencies": MEASURES[m]["dependencies"], "disruption": MEASURES[m]["disruption"],
            "annual_energy_change": sc["annual_energy_change"],
            "annual_operating_savings_usd": sc["annual_operating_savings_usd"],
            "annual_operating_cost_change_usd": sc["annual_operating_cost_change_usd"],
            "annual_emissions_change_kgco2e": sc["annual_emissions_change_kgco2e"],
            "operating_cost_increases": sc["operating_cost_increases"],
            "quoted_cost_usd": inp.get("quoted_cost_usd"), "cost_source": inp.get("cost_source"),
            "incentives": _incentives_for(m, eligibility, inp.get("incentive_status", {}))["listed"],
            "financials": sc["financials"],
        })
    applicable = [x["measure_id"] for x in measures if x["applicable"]]
    scen_defs = {k: [m for m in v if m in applicable] for k, v in PRESET_SCENARIOS.items()}
    scen_defs["all_applicable"] = applicable
    if ctx.settings.get("custom_scenario"):
        scen_defs["custom"] = [m for m in ctx.settings["custom_scenario"] if m in applicable]
    scenarios = [evaluate_scenario(k, v, b, costs.outputs, ctx.measure_inputs, eligibility, ef)
                 for k, v in scen_defs.items() if v]
    res.outputs = {"measures": measures, "scenarios": scenarios, "emission_factors": ef,
                   "payback_note": "Simple payback ignores financing, inflation, maintenance and equipment life."}
    res.assumptions.append({"id": "emission_factors", "data_label": "public_historical",
                            "text": f"Emissions use {ef['electricity_kg_per_kwh']} kgCO2e/kWh and "
                                    f"{ef['natural_gas_kg_per_therm']} kgCO2e/therm ({ef['accounting']} {ef['source']})."})
    for x in measures:
        for a in x.get("assumptions", []):
            res.assumptions.append({**a, "measure_id": x["measure_id"]})
        if x.get("operating_cost_increases"):
            res.warnings.append(f"{x['name']}: estimated operating cost INCREASES by "
                                f"${x['annual_operating_cost_change_usd']:,.0f}/yr while emissions change by "
                                f"{x['annual_emissions_change_kgco2e']:,.0f} kgCO2e/yr.")
        if x.get("applicable") and x["status"] == "estimated":
            res.evidence.append(Evidence(f"measure.{x['measure_id']}", f"{x['name']}: energy change "
                                         f"{x['annual_energy_change']}", "modelled_estimate"))
    est = sum(1 for x in measures if x.get("status") == "estimated")
    res.message = f"{est} measure(s) estimated, {len(applicable) - est} need data or an assessment."
    return res

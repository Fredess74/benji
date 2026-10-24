"""17 Create Energy Action Plans: ordered, evidence-linked recommendations and tasks.

Ordering is rule-based and explained (no hidden score):
  0  fix blocking data problems
  1  low-cost investigation (schedule review / professional assessment) when evidence warrants it
  2  estimated measures that reduce operating cost, ordered by confirmed simple payback, within budget first
  3  envelope assessment (prerequisite for heat-pump sizing)
  4  measures with trade-offs (operating-cost increase, high disruption) - evaluate, do not assume
  5  longer-term assessments (solar)
"""

from __future__ import annotations

from datetime import date, timedelta

from ..catalog.measures import MEASURES
from .base import COMPLETED, NEEDS_DATA, SkillContext, SkillResult

TIER_REASON = {
    0: "Data problems must be fixed first; later results depend on them.",
    1: "Low-cost investigation comes before spending on equipment.",
    2: "Estimated to lower operating cost using this building's own bills.",
    3: "Envelope work reduces the heating load and is needed to size heat pumps correctly.",
    4: "Has a trade-off (cost increase or major disruption) that needs evaluation before a decision.",
    5: "Longer-term opportunity that requires a separate site assessment.",
}


TENANT_ROLES = ("renter", "business_tenant")
OPS_STEP = {
    "commercial_office": "Walk the building after hours and export the thermostat/BMS schedules for review.",
    "multifamily": "Check boiler/thermostat schedules and common-area lighting timers; note anything running 24/7.",
    "small_business": "One evening after closing, note what is still on (display lights, ovens, coolers' doors, "
                      "space heaters, HVAC) and set the thermostat schedule to your opening hours.",
    "home": "Set a lower heating temperature at night and when away (if you control the thermostat), and turn off "
            "space heaters and electronics you are not using.",
}
LANDLORD_MEASURES = ("heat_pump_heating", "weatherization", "solar_assessment")
ROLE_DEFAULTS = {  # (who pays bills, who authorizes building changes) when the user has not said
    "renter": ("you (renter)", "your landlord"),
    "business_tenant": ("your business", "your landlord (check the lease)"),
    "owner_occupant": ("you (owner)", "you (owner)"),
    "business_owner_owns_space": ("your business", "you (owner)"),
    "landlord": ("tenants or you - check who holds each meter", "you (landlord)"),
}


OCCUPANT_MEASURES = {  # steps a tenant normally controls inside their own space
    "operations_schedule_review": "you",
    "energy_assessment": "you (the program may ask for the landlord's consent)",
    "thermostat_setback": "you, if you control the thermostat (check the lease)",
    "led_lighting": "you for bulbs/lamps; your landlord for fixed fixtures (check the lease)",
}


def _roles(b: dict, measure_id: str | None = None) -> dict:
    role = b.get("occupant_role")
    if role in TENANT_ROLES and measure_id in OCCUPANT_MEASURES:
        who = OCCUPANT_MEASURES[measure_id]
        payer = b.get("bill_payer") or ROLE_DEFAULTS[role][0]
        return {"pays_upfront": who, "receives_operating_savings": payer, "authorizes": who,
                "note": ("You do not control the building: equipment or envelope work needs the landlord's approval. "
                         "Start with no-cost operational steps you control, then share this plan with the landlord.")}
    d_payer, d_dm = ROLE_DEFAULTS.get(role, ("unknown", "unknown"))
    payer = b.get("bill_payer") or d_payer
    dm = b.get("decision_maker") or d_dm
    roles = {"pays_upfront": dm, "receives_operating_savings": payer, "authorizes": dm, "note": None}
    if role in ("renter", "business_tenant"):
        roles["note"] = ("You do not control the building: equipment or envelope work needs the landlord's approval. "
                         "Start with no-cost operational steps you control, then share this plan with the landlord.")
    elif payer not in ("unknown", dm) and any(w in payer.lower() for w in ("tenant", "resident")):
        roles["note"] = ("Split incentive: the decision-maker pays for the work while bill savings go to the bill "
                         "payer. Consider lease terms or cost-sharing.")
    return roles


def _money(x):
    return None if x is None else round(x, 2)


def _measure_rec(x: dict, b: dict, evidence_ids: list[str]) -> tuple[int, dict]:
    fin = x.get("financials", {}).get("confirmed", {})
    hyp = x.get("financials", {}).get("hypothetical", {})
    mid = x["measure_id"]
    if mid in ("operations_schedule_review", "energy_assessment"):
        tier = 1
    elif mid == "weatherization":
        tier = 3
    elif mid == "solar_assessment":
        tier = 5
    elif x.get("operating_cost_increases") or MEASURES[mid]["disruption"] == "high":
        tier = 4
    else:
        tier = 2
    unknowns = list(x.get("missing", []))
    if x.get("quoted_cost_usd") is None and x["kind"] != "assessment":
        unknowns.append("Installed cost (no quote entered)")
    if x["kind"] == "assessment":
        next_step = ("Schedule the assessment; ask the utility whether a no-cost program assessment applies."
                     if mid != "operations_schedule_review" else
                     OPS_STEP.get(b.get("category"), OPS_STEP["commercial_office"]))
        action = MEASURES[mid]["name"]
    elif x["status"] == "needs_data":
        next_step = "Provide: " + "; ".join(x["missing"])
        action = f"Collect information to evaluate: {MEASURES[mid]['name']}"
    elif x.get("quoted_cost_usd") is None and mid == "thermostat_setback":
        next_step = ("If your thermostat is programmable, set a lower temperature for nights / closed hours yourself "
                     "(no cost). Otherwise get a price for a programmable or smart thermostat.")
        action = MEASURES[mid]["name"]
    elif x.get("quoted_cost_usd") is None:
        next_step = "Request at least two contractor quotes (installed cost and equipment specifications)."
        action = MEASURES[mid]["name"]
    else:
        pre = [i for i in x.get("incentives", [])
               if i.get("preapproval_required") and i.get("eligibility_status") != "Known condition not met"
               and i.get("incentive_type") != "loan"]
        next_step = "Confirm incentive amounts with the program, then authorise the work."
        if pre:
            next_step = ("Confirm incentives with the program before ordering equipment ("
                         + ", ".join(i["name"] for i in pre) + " requires pre-approval), then authorise the work.")
        action = MEASURES[mid]["name"]
    if mid == "heat_pump_heating":
        unknowns.append("Distribution system compatibility, design heating load and electrical service capacity")
        next_step = "Complete the envelope assessment, then request a heat-pump sizing proposal with seasonal COP."
    if mid == "heat_pump_heating" and any(e.get("kind") in ("boiler", "furnace") and e.get("condition") == "working"
                                          for e in b.get("equipment", [])):
        unknowns.append("Existing heating equipment is working; age alone is not a reason to replace it. "
                        "Plan the change around end of life or a coordinated retrofit.")
    rank_reason = TIER_REASON[tier]
    if tier == 2 and x.get("status") != "estimated":
        rank_reason = "Could lower operating cost; Benji needs the facts listed to estimate it."
    if b.get("occupant_role") in TENANT_ROLES and mid in LANDLORD_MEASURES:
        tier = max(tier, 4)
        rank_reason = ("Needs the landlord: you do not control this part of the building. Benji lists it so you can "
                       "share the evidence with them.")
        next_step = "Share this plan with your landlord and ask them to consider it. " + next_step
    rec = {
        "id": f"rec_{mid}", "measure_id": mid, "title": MEASURES[mid]["name"], "tier": tier,
        "rank_reason": rank_reason,
        "issue": None, "evidence": evidence_ids, "unknowns": unknowns, "action": action,
        "costs_benefits": {
            "gross_cost_usd": x.get("quoted_cost_usd"), "cost_source": x.get("cost_source"),
            "net_cost_confirmed_usd": fin.get("net_cost_usd"), "upfront_cash_confirmed_usd": fin.get("upfront_cash_required_usd"),
            "net_cost_hypothetical_usd": hyp.get("net_cost_usd"),
            "annual_operating_savings_usd": _money(x.get("annual_operating_savings_usd")),
            "annual_energy_change": x.get("annual_energy_change"),
            "annual_emissions_change_kgco2e": x.get("annual_emissions_change_kgco2e"),
            "simple_payback_confirmed": fin.get("payback"), "within_total_budget": fin.get("within_total_budget"),
            "upfront_cash_feasible": fin.get("upfront_cash_feasible"), "funding_gap_usd": fin.get("funding_gap_usd"),
            "data_label": "modelled_estimate" if x["kind"] != "assessment" else None,
        },
        "assumptions": x.get("assumptions", []),
        "method": x.get("method"), "uncertainty": x.get("uncertainty"),
        "incentives": [{k: i[k] for k in ("id", "name", "incentive_type", "timing", "eligibility_status",
                                          "decision_status", "verification_status", "source_url", "preapproval_required",
                                          "amount_usd")} for i in x.get("incentives", [])],
        "roles": _roles(b, mid), "next_step": next_step, "status": x.get("status"),
    }
    return tier, rec


def build_plan(ctx: SkillContext, today: date | None = None) -> dict:
    b = ctx.building
    today = today or date.today()
    recs: list[tuple[int, float, dict]] = []
    q = ctx.result("03")
    if q and q.outputs["blocking"]:
        errs = [i for i in q.outputs["issues"] if i["severity"] == "error"]
        recs.append((0, 0, {"id": "rec_fix_data", "measure_id": None, "title": "Fix bill data problems", "tier": 0,
                            "rank_reason": TIER_REASON[0], "issue": f"{len(errs)} data error(s)",
                            "evidence": [f"quality.{i['code']}" for i in errs], "unknowns": [],
                            "action": "; ".join(i["correction_action"] for i in errs),
                            "costs_benefits": {}, "assumptions": [], "incentives": [], "roles": _roles(b),
                            "next_step": errs[0]["correction_action"], "status": "needs_data"}))
    anomalies = (ctx.result("06").outputs["anomalies"] if ctx.result("06") else [])
    bench = ctx.result("07")
    high_eui = bool(bench and bench.outputs.get("result") == "compared" and bench.outputs.get("position") == "above_upper_quartile")
    issue_text = []
    if anomalies:
        issue_text.append(f"{len(anomalies)} billing period(s) with unusual use versus the prior year")
    if high_eui:
        issue_text.append(f"site EUI above {bench.outputs['percentile']:.0f}% of {bench.outputs['sample_size']} BERDO peers")
    sav = ctx.result("10")
    measures = sav.outputs["measures"] if sav else []
    for x in measures:
        if not x.get("applicable"):
            continue
        mid = x["measure_id"]
        if mid == "operations_schedule_review" and not (anomalies or high_eui) \
                and b.get("category") not in ("home", "small_business"):
            continue
        if mid == "energy_assessment" and not (high_eui or anomalies or all(
                m.get("status") != "estimated" for m in measures if m.get("applicable"))):
            continue
        ev = [f"measure.{mid}"]
        if mid in ("operations_schedule_review", "energy_assessment"):
            ev = [f"anomaly.{a['bill_id']}" for a in anomalies] + (["benchmark.position"] if high_eui else [])
        tier, rec = _measure_rec(x, b, ev)
        rec["issue"] = "; ".join(issue_text) if mid in ("operations_schedule_review", "energy_assessment") and issue_text \
            else ("Opportunity identified from building data" if x["status"] == "estimated" else "Potential opportunity; evidence incomplete")
        pb = (rec["costs_benefits"].get("simple_payback_confirmed") or {}).get("years")
        cb = rec["costs_benefits"]
        within, cash_ok = cb.get("within_total_budget"), cb.get("upfront_cash_feasible")
        sort_key = (0 if within is not False and cash_ok is not False else 1) * 1000 + (pb if pb is not None else 500)
        if within is False:
            rec["rank_reason"] += " Net cost exceeds the stated total budget."
        if cash_ok is False:
            rec["rank_reason"] += (f" Funding gap: ${cb['funding_gap_usd']:,.0f} more cash is needed upfront than is "
                                   "available; a rebate paid later does not close it (consider financing or phasing).")
        elif cash_ok is None and cb.get("upfront_cash_confirmed_usd"):
            rec["unknowns"].append("Cash available upfront is unknown; enter it to check affordability.")
        recs.append((tier, sort_key, rec))
    th = ctx.result("08")
    for row in (th.outputs["scenarios"] if th else []):
        if not row.get("add_to_plan") or not row.get("scenarios"):
            continue
        cur = row["scenarios"][0]
        alts = row["scenarios"][1:]
        chosen = next((a for a in alts if a["name"] == row.get("selected_alternative")), None)
        if cur["status"] == "needs_data":
            nxt = "Provide: " + "; ".join(m["message"].split(".")[0] for m in cur["missing"])
        elif chosen:
            nxt = (f"Ask a contractor to verify the inputs behind '{chosen['name']}' (time to target "
                   f"{cur.get('time_to_target_h')} h -> {chosen.get('time_to_target_h')} h, modelled) and quote it.")
        else:
            nxt = "Verify the heat-loss and capacity inputs with an assessor before choosing equipment."
        shortfall = cur.get("capacity_shortfall")
        recs.append((1 if shortfall else 3, 0, {
            "id": f"rec_thermal_{row['id']}", "measure_id": None, "title": f"Room comfort: {row.get('name')}",
            "tier": 1 if shortfall else 3,
            "rank_reason": ("Modelled capacity shortfall: the room cannot hold the target temperature."
                            if shortfall else "Room scenario saved by the user for comparison."),
            "issue": cur.get("message"), "evidence": [f"thermal.{row['id']}"],
            "unknowns": [m["message"] for m in cur.get("missing", [])] + cur.get("main_uncertainty_drivers", []),
            "action": "Compare room heating/cooling options", "assumptions": cur.get("assumptions", []),
            "costs_benefits": {"time_to_target_h": cur.get("time_to_target_h"),
                               "variable_energy_cost_usd_per_event": cur.get("variable_energy_cost_usd"),
                               "data_label": "modelled_estimate"},
            "incentives": [], "roles": _roles(b), "next_step": nxt, "status": cur["status"],
            "limitations": row.get("limitations"),
        }))
    prof = ctx.results.get("04")
    if prof and prof.status != COMPLETED:
        blocking = [m["label"] for m in prof.missing_inputs if m.get("blocking")]
        recs.append((0, 0, {
            "id": "rec_complete_profile", "measure_id": None, "title": "Tell Benji a few basics about the property",
            "tier": 0, "rank_reason": "Programs and comparisons depend on these facts.",
            "issue": "Profile incomplete", "evidence": [], "unknowns": blocking,
            "action": "Complete: " + "; ".join(blocking), "costs_benefits": {}, "assumptions": [], "incentives": [],
            "roles": _roles(b), "next_step": "Add: " + "; ".join(blocking), "status": "needs_data"}))
    if not measures:
        # Too little data for measure estimates: the useful plan is "get the missing facts" + a no-cost assessment.
        c = ctx.results.get("09")
        miss = [m.get("action") or m.get("label") for r in ctx.results.values() if r.status != "not_selected"
                for m in r.missing_inputs if (m.get("action") or m.get("label"))][:6]
        recs.append((0, 1, {
            "id": "rec_collect_data", "measure_id": None, "title": "Collect the information Benji needs",
            "tier": 0, "rank_reason": "Estimates need your own bills; Benji does not guess.",
            "issue": (c.message if c else "No confirmed bills yet."), "evidence": [], "unknowns": miss,
            "action": "Add 12 months of electricity and gas bills (amounts, usage and dates), then re-run.",
            "costs_benefits": {}, "assumptions": [], "incentives": [], "roles": _roles(b),
            "next_step": "Download the last 12 months of bills from your utility account (or photograph them) and "
                         "enter usage and amounts.", "status": "needs_data"}))
        recs.append((1, 0, {
            "id": "rec_energy_assessment", "measure_id": "energy_assessment", "title": MEASURES["energy_assessment"]["name"],
            "tier": 1, "rank_reason": TIER_REASON[1], "issue": "Cause of high bills not yet known",
            "evidence": [], "unknowns": [], "action": MEASURES["energy_assessment"]["name"], "costs_benefits": {},
            "assumptions": [], "incentives": [], "roles": _roles(b),
            "next_step": "Ask your utility / Mass Save whether a no-cost assessment applies to you.",
            "status": "assessment_only"}))
    recs.sort(key=lambda r: (r[0], r[1]))
    ordered = [r[2] for r in recs]
    for i, r in enumerate(ordered, start=1):
        r["priority"] = i

    # tasks: keep user-edited statuses from the previous plan
    prev = {t["id"]: t for t in (ctx.settings.get("previous_plan") or {}).get("tasks", [])}
    tasks, rec_task = [], {}
    for r in ordered:
        tid = f"task_{r['id'].removeprefix('rec_')}"
        deps = MEASURES.get(r["measure_id"] or "", {}).get("dependencies", [])
        prereq = [f"task_{d}" for d in deps if f"rec_{d}" in {o['id'] for o in ordered}]
        if r["tier"] > 0 and any(o["tier"] == 0 for o in ordered):
            prereq.insert(0, "task_fix_data")
        t = {"id": tid, "title": f"{r['title']}: {r['next_step']}", "recommendation_id": r["id"],
             "owner": r["roles"]["authorizes"] if r["tier"] else (b.get("bill_payer") or b.get("decision_maker")),
             "prerequisites": prereq, "due_date": (today + timedelta(weeks=2 * r["priority"])).isoformat(),
             "status": "not_started", "next_step": r["next_step"]}
        if tid in prev:
            for k in ("status", "owner", "due_date"):
                t[k] = prev[tid].get(k, t[k])
        tasks.append(t)
        rec_task[r["id"]] = tid
    first_open = next((t for t in tasks if t["status"] not in ("done", "skipped")), None)
    blocked = [sid for sid in ("09", "10") if (ctx.results.get(sid) and ctx.results[sid].status == "blocked_by_data_quality")]
    return {"created_on": today.isoformat(), "building_id": b.get("id"), "recommendations": ordered,
            "decision_ready": not (q and q.outputs["blocking"]) and not blocked,
            "suppressed_skills": blocked,
            "tasks": tasks, "next_action": first_open["title"] if first_open else None,
            "budget_usd": b.get("budget_usd"), "data_label": b.get("data_label", "user_provided"),
            "ordering_rules": TIER_REASON,
            "disclaimer": "Recommendations identify opportunities. Savings are estimates until work is completed and "
                          "measured."}


def run(ctx: SkillContext) -> SkillResult:
    res = SkillResult("17", COMPLETED)
    if not ctx.result("04"):
        res.warnings.append("Profile incomplete: the plan starts with completing it.")
    if not ctx.result("10"):
        res.warnings.append("Savings skill (10) not available; plan contains only data and investigation steps.")
    plan = build_plan(ctx)
    res.outputs = {"plan": plan}
    res.message = f"{len(plan['recommendations'])} recommendation(s); next action: {plan['next_action']}"
    return res

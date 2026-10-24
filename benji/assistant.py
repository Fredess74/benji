"""Assistant facade: the simple input -> process -> output contract shared by every channel.

Channels (dashboard "Quick start", Claude via MCP, ChatGPT via HTTP actions, OpenClaw via its skill) call
these functions. They only orchestrate the validated skills; they never calculate on their own, and the
plain-language summary is built deterministically from skill outputs (no model involved).
"""

from __future__ import annotations

import calendar
import os
from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from . import engine, readiness, thermal
from .models import Bill, Building
from .skills import registry
from .store import Store

PUBLIC_URL = os.environ.get("BENJI_PUBLIC_URL", "http://127.0.0.1:8000")

PROPERTY_TYPES = {
    "home": "Home or 1-4 unit residence (owner, renter or small landlord)",
    "small_business": "Small business space: store, grocery, cafe/restaurant or small office",
    "commercial_office": "Office building",
    "multifamily": "Apartment building with 5+ units",
}


class AssistantError(ValueError):
    def __init__(self, errors: list[dict]):
        super().__init__("; ".join(f"{e['field']}: {e['message']}" for e in errors))
        self.errors = errors


def _pyd_errors(exc: ValidationError, prefix: str = "") -> list[dict]:
    return [{"field": prefix + ".".join(str(p) for p in e["loc"]), "message": e["msg"]} for e in exc.errors()]


class PropertyIn(BaseModel):
    """Plain-language property intake. Every field except type and name is optional."""

    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")
    property_type: Literal["home", "small_business", "commercial_office", "multifamily"]
    name: str = Field(min_length=1, max_length=120)
    zip: Optional[str] = Field(None, pattern=r"^\d{5}$")
    city: Optional[str] = None
    occupant_role: Optional[Literal["owner_occupant", "renter", "landlord", "business_owner_owns_space",
                                    "business_tenant", "property_manager"]] = None
    business_type: Optional[Literal["retail_store", "grocery", "food_service", "small_office", "other"]] = None
    heating_fuel: Optional[Literal["natural_gas", "oil", "propane", "electric_resistance", "district_steam",
                                   "heat_pump"]] = None
    electric_utility: Optional[str] = None
    gas_utility: Optional[str] = None
    floor_area_sqft: Optional[float] = Field(None, gt=0, le=1e8)
    dwelling_units: Optional[int] = Field(None, ge=1, le=100000)
    budget_usd: Optional[float] = Field(None, ge=0, le=1e10)
    cash_available_usd: Optional[float] = Field(None, ge=0, le=1e10)
    bills_cover_whole_building: Optional[bool] = None
    bill_payer: Optional[str] = None
    decision_maker: Optional[str] = None
    opening_hours: Optional[str] = None  # e.g. "Mon-Sat 07:00-19:00"


class MonthlyBillIn(BaseModel):
    """One bill as a person reads it: month (or exact dates), usage, unit and amount."""

    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")
    fuel: Literal["electricity", "natural_gas"]
    month: Optional[str] = Field(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")  # YYYY-MM, used if dates missing
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    quantity: float = Field(ge=0, le=1e10)
    unit: Literal["kWh", "MWh", "therms", "ccf"]
    total_usd: Optional[float] = Field(None, ge=-1e8, le=1e8)
    fixed_charge_usd: Optional[float] = Field(None, ge=0, le=1e8)
    account: Optional[str] = None
    utility: Optional[str] = None


def create_property(store: Store, data: dict, channel: str = "assistant_api") -> dict:
    try:
        p = PropertyIn(**data)
    except ValidationError as exc:
        raise AssistantError(_pyd_errors(exc))
    sources = ["electricity"] + (["natural_gas"] if p.heating_fuel == "natural_gas" or p.gas_utility else [])
    b = {"name": p.name, "category": p.property_type, "zip": p.zip, "city": p.city, "state": "MA",
         "occupant_role": p.occupant_role, "business_type": p.business_type, "heating_fuel": p.heating_fuel,
         "electric_utility": p.electric_utility, "gas_utility": p.gas_utility,
         "gross_floor_area_sqft": p.floor_area_sqft,
         "dwelling_units": p.dwelling_units or (1 if p.property_type == "home" else None),
         "budget_usd": p.budget_usd, "upfront_cash_available_usd": p.cash_available_usd,
         "bills_cover_whole_building": p.bills_cover_whole_building, "bill_payer": p.bill_payer,
         "decision_maker": p.decision_maker, "energy_sources": sources,
         "schedule": {"weekday_occupied_hours": p.opening_hours}}
    try:
        building = Building(**b).model_dump(mode="json")
    except ValidationError as exc:
        raise AssistantError(_pyd_errors(exc))
    saved = store.save_building(building)
    store.log_event(saved["id"], channel, "created property", {"type": p.property_type, "name": p.name})
    prof = engine.run_skills(saved, [], {}, ["04"])["04"]
    return {"property_id": saved["id"], "property": saved, "missing_information": prof.missing_inputs,
            "next_step": "Add 12 months of bills with add_bills (usage, unit, amount and month).",
            "dashboard_url": f"{PUBLIC_URL}/app/#place={saved['id']}"}


def update_property(store: Store, property_id: str, changes: dict, channel: str = "assistant_api") -> dict:
    b = store.get_building(property_id)
    if not b:
        raise KeyError(property_id)
    allowed = set(Building.model_fields) - {"id", "data_label"}
    # One-way switch: a user may mark their own entries as example/synthetic data, never the reverse.
    if changes.get("data_label") == "synthetic_demo":
        allowed = allowed | {"data_label"}
    bad = [k for k in changes if k not in allowed]
    if bad:
        raise AssistantError([{"field": k, "message": "unknown or read-only field"} for k in bad])
    try:
        nb = Building(**{**b, **changes}).model_dump(mode="json")
    except ValidationError as exc:
        raise AssistantError(_pyd_errors(exc))
    nb["id"] = property_id
    nb["data_label"] = "synthetic_demo" if "synthetic_demo" in (changes.get("data_label"), b.get("data_label")) \
        else b.get("data_label", "user_provided")
    store.save_building(nb)
    store.log_event(property_id, channel, "updated profile", {"fields": sorted(changes)})
    return {"property_id": property_id, "updated_fields": sorted(changes), "note": "Re-run analyze to refresh results."}


def add_bills(store: Store, property_id: str, bills: list[dict], confirmed: bool,
              channel: str = "assistant_api") -> dict:
    """Add bills typed by the user. `confirmed=True` only after the user has checked the values read back to them."""
    b = store.get_building(property_id)
    if not b:
        raise KeyError(property_id)
    saved, errors = [], []
    for i, raw in enumerate(bills):
        try:
            m = MonthlyBillIn(**raw)
            start, end = m.period_start, m.period_end
            if not (start and end):
                if not m.month:
                    raise AssistantError([{"field": "month", "message": "give month (YYYY-MM) or period_start/end"}])
                y, mo = map(int, m.month.split("-"))
                start = date(y, mo, 1)
                end = date(y + (mo == 12), mo % 12 + 1, 1)
            items = []
            if m.fixed_charge_usd is not None and m.total_usd is not None:
                items = [{"description": "Fixed / customer charge", "category": "fixed", "amount_usd": m.fixed_charge_usd},
                         {"description": "Usage-based charges", "category": "energy",
                          "amount_usd": round(m.total_usd - m.fixed_charge_usd, 2)}]
            bill = Bill(fuel=m.fuel, utility=m.utility or (b.get("electric_utility") if m.fuel == "electricity" else b.get("gas_utility")),
                        account=m.account, period_start=start, period_end=end, quantity=m.quantity, unit=m.unit,
                        total_usd=m.total_usd, line_items=items,
                        source={"kind": "manual", "raw_excerpt": f"entered via {channel}"},
                        status="confirmed" if confirmed else "pending_confirmation",
                        data_label=b.get("data_label", "user_provided"))
            saved.append(store.save_bill({**bill.model_dump(mode="json"), "building_id": property_id}))
        except AssistantError as exc:
            errors += [{**e, "field": f"bills.{i}.{e['field']}"} for e in exc.errors]
        except ValidationError as exc:
            errors += _pyd_errors(exc, f"bills.{i}.")
    if saved:
        store.log_event(property_id, channel, "added bills", {"count": len(saved), "confirmed": confirmed})
    return {"saved": len(saved), "status": "confirmed" if confirmed else "pending_confirmation", "errors": errors,
            "bill_ids": [x["id"] for x in saved],
            "next_step": "Run analyze." if confirmed else "Read the values back to the user, then call confirm_bills."}


def confirm_bills(store: Store, property_id: str, bill_ids: list[str] | None = None,
                  channel: str = "assistant_api") -> dict:
    n = 0
    for bill in store.list_bills(property_id):
        if bill["status"] != "confirmed" and (bill_ids is None or bill["id"] in bill_ids):
            bill["status"] = "confirmed"
            store.save_bill(bill)
            n += 1
    if n:
        store.log_event(property_id, channel, "confirmed bills", {"count": n})
    return {"confirmed": n}


def _fuel_line(f: str, s: dict) -> str:
    cov = s["coverage"]
    cost = (f"${s['recorded_cost_usd']:,.0f}" if s["recorded_cost_usd"] is not None else "cost partly unknown")
    return (f"{f.replace('_', ' ')}: {s['recorded_quantity']:,.0f} {s['unit']} and {cost} over {cov['covered_days']} days "
            f"({cov['window_start']} to {cov['window_end']}).")


def summarize(building: dict, analysis: dict, plan: Optional[dict]) -> dict:
    """Deterministic plain-language summary of validated results, with data labels and limits."""
    R = analysis["results"]
    synthetic = building.get("data_label") == "synthetic_demo"
    out: dict[str, Any] = {"property": building.get("name"), "property_type": building.get("category"),
                           "synthetic_demo_data": synthetic, "analysis_ran_at": analysis.get("ran_at"),
                           "decision_ready": analysis.get("decision_ready"), "stale": analysis.get("stale", False)}
    lines = []
    if synthetic:
        lines.append("NOTE: this is synthetic demonstration data, not a real property.")
    if analysis.get("stale"):
        lines.append("Results are out of date because inputs changed: " + analysis.get("stale_message", ""))
    q = R.get("03", {})
    errors = [i for i in q.get("outputs", {}).get("issues", []) if i["severity"] == "error"]
    if errors:
        lines.append(f"Bill data has {len(errors)} error(s) to fix before money or comparison results are shown: "
                     + "; ".join(i["message"] + " Fix: " + i["correction_action"] for i in errors[:3]))
    imp = R.get("01", {}).get("outputs", {})
    if imp.get("pending_count"):
        lines.append(f"{imp['pending_count']} bill(s) are waiting for your confirmation and are not used yet.")
    c = R.get("09", {})
    if c.get("status") == "completed":
        lines += [_fuel_line(f, s) for f, s in c["outputs"]["fuels"].items()]
    an = R.get("06", {})
    if an.get("status") == "completed" and an["outputs"]["anomalies"]:
        a0 = an["outputs"]["anomalies"][0]
        lines.append(f"{len(an['outputs']['anomalies'])} billing period(s) changed a lot versus last year, e.g. "
                     f"{a0['period'][0]}: {a0['change_pct']:+.0f}% daily {a0['fuel'].replace('_', ' ')} use. "
                     + (a0["context_questions"][0] if a0["context_questions"] else ""))
    bm = R.get("07", {})
    if bm.get("outputs", {}).get("result") == "compared":
        o = bm["outputs"]
        pos = ("more energy per square foot than most of them" if o["position"] == "above_upper_quartile" else
               "less energy per square foot than most of them" if o["position"] == "below_lower_quartile" else
               "about as much energy per square foot as the middle half of them")
        lines.append(f"Compared with {o['sample_size']} similar Boston buildings (BERDO {o['source']['reporting_year']}), "
                     f"this property uses {pos} ({o['building_site_eui']} vs median {o['peer_median']} kBtu/sq ft; "
                     f"higher than {o['percentile']:.0f}%). That shows where to look, not a guaranteed saving.")
    elif bm.get("status") in ("completed", "needs_data") and bm.get("message"):
        lines.append(bm["message"])
    out["what_we_found"] = lines
    actions = []
    sav = {m["measure_id"]: m for m in R.get("10", {}).get("outputs", {}).get("measures", [])}
    for r in (plan or {}).get("recommendations", [])[:4]:
        m = sav.get(r.get("measure_id") or "", {})
        fin = (m.get("financials") or {}).get("confirmed", {})
        item = {"priority": r["priority"], "action": r["title"], "why_first": r["rank_reason"], "next_step": r["next_step"],
                "who_authorizes": r["roles"]["authorizes"]}
        if r.get("measure_id") in ("heat_pump_heating", "weatherization", "solar_assessment") and r["roles"].get("note"):
            item["role_note"] = "Needs the landlord's approval."
        if m.get("status") == "estimated":
            item["estimated_annual_energy_change"] = m.get("annual_energy_change")
            ch = m.get("annual_operating_cost_change_usd")
            item["estimated_annual_operating_cost_change_usd"] = ch
            item["estimate_label"] = "modelled estimate, not a measured saving"
            if ch is not None and ch > 0:
                item["warning"] = f"Operating cost would INCREASE by about ${ch:,.0f}/yr (emissions change " \
                                  f"{m['annual_emissions_change_kgco2e']:,.0f} kgCO2e/yr)."
            item["upfront_cash_needed_usd"] = fin.get("upfront_cash_required_usd")
            item["net_cost_after_confirmed_incentives_usd"] = fin.get("net_cost_usd")
            item["funding_gap_usd"] = fin.get("funding_gap_usd")
            item["simple_payback_years"] = (fin.get("payback") or {}).get("years")
        if r.get("unknowns"):
            item["still_unknown"] = r["unknowns"][:3]
        actions.append(item)
    out["what_to_do_first"] = actions
    recs = (plan or {}).get("recommendations", [])
    out["who_decides"] = recs[0]["roles"] if recs else None
    progs = []
    for e in R.get("14", {}).get("outputs", {}).get("results", []):
        if e["status"] != "Known condition not met":
            progs.append({"program": e["name"], "type": e["incentive_type"], "paid": e["timing"],
                          "status": e["status"], "questions": e["questions"],
                          "source": e["source_url"], "source_verified": e["verification_status"]})
    out["programs_to_check"] = progs
    out["program_note"] = ("Program leads are unverified until checked with the program. Applying is not approval; "
                           "rebates paid after installation do not reduce the cash needed upfront.")
    missing = []
    for sid in ("04", "01", "09", "07", "10"):
        for m in R.get(sid, {}).get("missing_inputs", []):
            t = m.get("label") or m.get("action")
            if t and "floor area" in t.lower() and any("floor area" in x.lower() for x in missing):
                continue
            if t and t not in missing:
                missing.append(t)
    out["information_that_would_help"] = missing[:8]
    out["next_action"] = (plan or {}).get("next_action")
    out["limits"] = ["Estimates come from your bills and stated inputs; they are not measured savings.",
                     "Benji does not weather-normalise, inspect equipment, or approve program eligibility."]
    out["dashboard_url"] = f"{PUBLIC_URL}/app/#place={building.get('id')}"
    return out


def analyze(store: Store, property_id: str, skills: Optional[list[str]] = None,
            channel: str = "assistant_api") -> dict:
    b = store.get_building(property_id)
    if not b:
        raise KeyError(property_id)
    a = engine.analyze(store, property_id, skills)
    store.log_event(property_id, channel, "ran analysis", {"decision_ready": a["decision_ready"]})
    return summarize(b, a, engine.get_plan(store, property_id))


def get_summary(store: Store, property_id: str) -> dict:
    b = store.get_building(property_id)
    a = engine.with_staleness(store, store.get_analysis(property_id))
    if not b or not a:
        raise KeyError(property_id)
    return summarize(b, a, engine.get_plan(store, property_id))


def get_plan(store: Store, property_id: str) -> dict:
    p = engine.get_plan(store, property_id)
    if not p:
        raise KeyError(property_id)
    return {"next_action": p["next_action"], "stale": p.get("stale"), "decision_ready": p.get("decision_ready"),
            "tasks": [{k: t[k] for k in ("id", "title", "owner", "due_date", "status", "prerequisites")} for t in p["tasks"]],
            "recommendations": [{k: r.get(k) for k in ("priority", "title", "rank_reason", "next_step", "unknowns",
                                                       "costs_benefits", "roles")} for r in p["recommendations"]]}


def demo_mode() -> bool:
    return os.environ.get("BENJI_DEMO_MODE") == "1"


def visible_buildings(store: Store) -> list[dict]:
    """Synthetic demo properties are hidden unless BENJI_DEMO_MODE=1 (developer/testing only)."""
    return [b for b in store.list_buildings() if demo_mode() or b.get("data_label") != "synthetic_demo"]


def list_properties(store: Store) -> list[dict]:
    return [{"property_id": b["id"], "name": b["name"], "property_type": b["category"],
             "synthetic_demo_data": b.get("data_label") == "synthetic_demo"} for b in visible_buildings(store)]


def list_skills() -> list[dict]:
    return [{"id": s["id"], "name": s["name"], "status": s["implementation_status"], "purpose": s["purpose"],
             "needs": s["data_prerequisites"]} for s in registry.list_skills()]


def room_scenario(inputs: dict, alternatives: list[dict] | None = None) -> dict:
    try:
        thermal.ScenarioInputs(**inputs)
        return thermal.compare(inputs, alternatives or [])
    except ValidationError as exc:
        raise AssistantError(_pyd_errors(exc, "inputs."))


def electrification_checklist(store: Store, property_id: str) -> dict:
    b = store.get_building(property_id)
    if not b:
        raise KeyError(property_id)
    return readiness.checklist(b, store.list_children("documents", property_id))


def month_days(month: str) -> int:
    y, m = map(int, month.split("-"))
    return calendar.monthrange(y, m)[1]

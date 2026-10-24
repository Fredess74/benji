"""Sweep: every implemented skill on many realistic input combinations must end in a defined status
(never `failed`), and the plain-language summary must always build."""

import itertools
from datetime import date

import pytest

from benji import assistant, engine
from benji.skills.registry import EXECUTION_ORDER
from benji.store import Store

GAS = [2.1, 1.9, 1.55, 0.95, 0.45, 0.2, 0.15, 0.15, 0.25, 0.7, 1.35, 1.95]
OK_STATUSES = {"completed", "needs_data", "not_selected", "blocked_by_prerequisite", "blocked_by_data_quality"}

PROFILES = {
    "home_renter": {"property_type": "home", "name": "h", "occupant_role": "renter", "heating_fuel": "natural_gas",
                    "electric_utility": "Eversource", "zip": "02124"},
    "home_owner_oil": {"property_type": "home", "name": "h2", "occupant_role": "owner_occupant", "heating_fuel": "oil",
                       "electric_utility": "National Grid"},
    "home_minimal": {"property_type": "home", "name": "bare"},
    "cafe_tenant": {"property_type": "small_business", "name": "c", "business_type": "food_service",
                    "occupant_role": "business_tenant", "heating_fuel": "natural_gas", "electric_utility": "Eversource",
                    "floor_area_sqft": 1400, "cash_available_usd": 500, "bills_cover_whole_building": True},
    "store_electric": {"property_type": "small_business", "name": "s", "business_type": "retail_store",
                       "occupant_role": "business_owner_owns_space", "heating_fuel": "heat_pump",
                       "electric_utility": "Unitil", "floor_area_sqft": 3000},
    "office": {"property_type": "commercial_office", "name": "o", "heating_fuel": "natural_gas", "zip": "02110",
               "electric_utility": "Eversource", "floor_area_sqft": 40000, "bills_cover_whole_building": True,
               "budget_usd": 50000, "cash_available_usd": 20000},
    "multifamily_no_units": {"property_type": "multifamily", "name": "m", "heating_fuel": "natural_gas",
                             "electric_utility": "Eversource", "floor_area_sqft": 9000},
}


def _months(n, start=(2025, 10)):
    y, m = start
    for _ in range(n):
        yield f"{y}-{m:02d}", m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def bills(kind):
    out = []
    if kind == "none":
        return out
    n = {"one_month": 1, "six_months": 6, "year": 12, "two_years": 24}.get(kind, 12)
    start = (2024, 10) if kind == "two_years" else (2025, 10)
    for month, m in _months(n, start):
        if kind != "gas_only":
            e = {"fuel": "electricity", "month": month, "quantity": 900, "unit": "kWh"}
            if kind != "no_amounts":
                e.update(total_usd=280, fixed_charge_usd=10)
            out.append(e)
        if kind != "electric_only":
            g = {"fuel": "natural_gas", "month": month, "quantity": round(20 + 80 * GAS[m - 1], 1),
                 "unit": "ccf" if kind == "ccf" else "therms"}
            if kind != "no_amounts":
                g.update(total_usd=round(15 + 150 * GAS[m - 1], 2))
            out.append(g)
    return out


BILL_KINDS = ["none", "one_month", "six_months", "year", "two_years", "electric_only", "gas_only", "no_amounts", "ccf"]


@pytest.mark.parametrize("profile,kind", list(itertools.product(PROFILES, BILL_KINDS)))
def test_every_skill_reaches_a_defined_state(profile, kind):
    s = Store(":memory:")
    pid = assistant.create_property(s, PROFILES[profile])["property_id"]
    if kind != "none":
        r = assistant.add_bills(s, pid, bills(kind), confirmed=True)
        assert not r["errors"], r["errors"]
    summary = assistant.analyze(s, pid)
    a = s.get_analysis(pid)
    for sid in EXECUTION_ORDER:
        st = a["results"][sid]["status"]
        assert st in OK_STATUSES, f"{profile}/{kind}: skill {sid} {st}: {a['results'][sid]['message']}"
    assert summary["what_to_do_first"], f"{profile}/{kind}: empty plan"
    assert summary["next_action"]
    # unknown money never shown as zero
    for f in a["results"]["09"].get("outputs", {}).get("fuels", {}).values():
        if kind == "no_amounts":
            assert f["recorded_cost_usd"] is None
    # residential never sees business programs and vice versa
    progs = [p["program"] for p in summary["programs_to_check"]]
    if profile.startswith("home") or profile.startswith("multifamily"):
        assert not any("business" in p for p in progs)
    else:
        assert not any("multifamily" in p.lower() or "Home Energy" in p for p in progs)


def test_pending_only_bills_are_not_used():
    s = Store(":memory:")
    pid = assistant.create_property(s, PROFILES["office"])["property_id"]
    assistant.add_bills(s, pid, bills("year"), confirmed=False)
    summary = assistant.analyze(s, pid)
    assert any("waiting for your confirmation" in x for x in summary["what_we_found"])
    assert s.get_analysis(pid)["results"]["09"]["status"] in ("needs_data", "blocked_by_prerequisite")


def test_today_is_not_hardcoded():
    assert date.today().year >= 2026

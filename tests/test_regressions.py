"""Regression tests for the independently reproduced audit findings (Priority 0)."""

import copy
from datetime import date, timedelta

import pytest

from benji import demo, engine
from benji.skills.registry import EXECUTION_ORDER
from benji.skills.s09_costs import fuel_summary
from benji.store import Store


def run(b=None, bs=None, mi=None, selected=EXECUTION_ORDER, settings=None):
    b = b or demo.office_building()
    bs = demo.office_bills() if bs is None else bs
    mi = mi if mi is not None else {x["measure_id"]: x for x in demo.office_measure_inputs()}
    return engine.run_skills(copy.deepcopy(b), copy.deepcopy(bs), copy.deepcopy(mi), selected, settings or {})


def measure(res, mid):
    return next(x for x in res["10"].outputs["measures"] if x["measure_id"] == mid)


# 1 -------------------------------------------------------------------------------------
def test_missing_declared_fuel_blocks_benchmark():
    r = run(bs=[x for x in demo.office_bills() if x["fuel"] == "electricity"])
    assert r["07"].outputs["result"] == "insufficient_comparable_data"
    assert "natural_gas" in r["07"].message
    assert "building_site_eui" not in r["07"].outputs


def test_heat_pump_building_needs_only_electricity():
    b = demo.office_building()
    b.update(heating_fuel="heat_pump", energy_sources=["electricity"],
             equipment=[{"id": "hp", "kind": "heat_pump", "fuel": "electricity", "condition": "working"}])
    r = run(b=b, bs=[x for x in demo.office_bills() if x["fuel"] == "electricity"])
    assert r["07"].outputs["result"] == "compared"


def test_unknown_whole_building_scope_requests_confirmation():
    b = demo.office_building()
    b["bills_cover_whole_building"] = None
    r = run(b=b)
    assert r["07"].status == "needs_data"
    assert r["07"].outputs["result"] == "needs_scope_confirmation"


def test_each_meter_needs_full_coverage():
    bills = demo.office_bills()
    # a second electricity meter with only 3 months must not be hidden by the first meter's coverage
    extra = [demo._bill(f"m2_{i}", "electricity", date(2026, 7 + i, 1), date(2026, 8 + i, 1), 1000, "kWh",
                        demo.ELEC, "Eversource", "E-9999") for i in range(3)]
    r = run(bs=bills + extra)
    elec = r["09"].outputs["fuels"]["electricity"]
    assert elec["coverage"]["complete"] is False
    assert {m["account"] for m in elec["meters"]} == {"E-1001", "E-9999"}
    assert r["07"].outputs["result"] == "insufficient_comparable_data"


def test_fuels_must_share_analysis_period():
    bills = [b for b in demo.office_bills()
             if b["fuel"] == "electricity" or date.fromisoformat(b["period_end"]) <= date(2026, 4, 1)]
    r = run(bs=bills)
    assert r["07"].outputs["result"] == "insufficient_comparable_data"


# 2 -------------------------------------------------------------------------------------
def test_blocking_quality_errors_suppress_dependent_conclusions():
    bills = demo.office_bills()
    dup = copy.deepcopy(bills[-1])
    dup["id"] = "dup"
    r = run(bs=bills + [dup])
    assert r["03"].outputs["blocking"] is True
    for sid in ("09", "06", "07", "10"):
        assert r[sid].status == "blocked_by_data_quality", sid
    assert r["17"].status == "completed"
    assert r["17"].outputs["plan"]["recommendations"][0]["id"] == "rec_fix_data"
    assert r["17"].outputs["plan"]["decision_ready"] is False
    assert r["20"].outputs["decision_ready"] is False


def test_quality_check_runs_even_when_not_selected():
    bills = demo.office_bills()
    dup = copy.deepcopy(bills[-1])
    dup["id"] = "dup"
    r = run(bs=bills + [dup], selected=["04", "01", "09", "10"])
    assert r["03"].status == "completed" and r["03"].outputs["blocking"]
    assert r["10"].status in ("blocked_by_data_quality", "blocked_by_prerequisite")


# 3 -------------------------------------------------------------------------------------
@pytest.mark.parametrize("params", [
    {"seasonal_cop": 2.6, "existing_efficiency_pct": -0.8},
    {"seasonal_cop": 2.6, "existing_efficiency_pct": 0.8},       # fraction given where percent is required
    {"seasonal_cop": float("nan")},
    {"seasonal_cop": float("inf")},
    {"seasonal_cop": "fast"},
    {"seasonal_cop": 2.6, "existing_efficiency": 80},              # unknown key
])
def test_invalid_heat_pump_params_are_rejected_not_calculated(params):
    mi = {x["measure_id"]: x for x in demo.office_measure_inputs()}
    mi["heat_pump_heating"]["params"] = params
    r = run(mi=mi)
    assert r["10"].status == "completed"
    hp = measure(r, "heat_pump_heating")
    assert hp["status"] == "invalid_input"
    assert hp["annual_operating_savings_usd"] is None
    assert hp["input_errors"] and all("field" in e for e in hp["input_errors"])


def test_api_rejects_invalid_values_with_field_messages(client):
    b = client.post("/api/buildings", json={"name": "x", "category": "commercial_office",
                                            "gross_floor_area_sqft": -5}).json()
    assert "detail" in b
    r = client.post("/api/demo/reset")
    r = client.put("/api/buildings/demo_office/measure-inputs/heat_pump_heating",
                   json={"measure_id": "heat_pump_heating", "params": {"seasonal_cop": 9}})
    assert r.status_code == 422 and r.json()["detail"][0]["field"] == "params.seasonal_cop"
    r = client.put("/api/buildings/demo_office/measure-inputs/led_lighting",
                   content=b'{"measure_id":"led_lighting","quoted_cost_usd":NaN}',
                   headers={"content-type": "application/json"})
    assert r.status_code == 422
    eq = demo.office_building()
    eq["equipment"][0]["efficiency"] = 0.8  # AFUE must be percent
    eq.pop("id")
    assert client.post("/api/buildings", json=eq).status_code == 422
    r = client.post("/api/buildings/demo_office/analysis",
                    json={"settings": {"tariff_overrides": {"electricity": {"usage_rate": -1}}}})
    assert r.status_code == 422


def test_bill_credit_kept_separate_from_negative_consumption(client):
    client.post("/api/demo/reset")
    good = {"fuel": "electricity", "period_start": "2026-10-01", "period_end": "2026-11-01", "quantity": 100,
            "unit": "kWh", "total_usd": 10, "line_items": [
                {"description": "fixed", "category": "fixed", "amount_usd": 15},
                {"description": "solar credit", "category": "credit", "amount_usd": -5}]}
    assert client.post("/api/buildings/demo_office/bills", json=good).status_code == 201
    bad = {**good, "quantity": -100}
    assert client.post("/api/buildings/demo_office/bills", json=bad).status_code == 422


# 4 -------------------------------------------------------------------------------------
def test_short_winter_history_gives_no_annual_heating_savings():
    short = []
    for i in range(9):
        s = date(2026, 1, 1) + timedelta(days=7 * i)
        short.append(demo._bill(f"w{i}", "natural_gas", s, s + timedelta(days=7), 100 + 50 * i, "therms",
                                demo.GAS, "National Grid", "weekly"))
    s = fuel_summary("natural_gas", short)
    assert s["heating_split"] is None and s["heating_split_unavailable_reason"]
    r = run(bs=short)
    t = measure(r, "thermostat_setback")
    assert t["status"] == "needs_data" and t["annual_operating_savings_usd"] is None


# 5 -------------------------------------------------------------------------------------
def test_applied_rebate_is_not_confirmed():
    mi = {x["measure_id"]: x for x in demo.office_measure_inputs()}
    mi["thermostat_setback"]["incentive_status"]["ms_business_controls"] = {"status": "applied", "amount_usd": 1500}
    t = measure(run(mi=mi), "thermostat_setback")["financials"]
    assert t["confirmed"]["net_cost_usd"] == 6500
    assert t["hypothetical"]["net_cost_usd"] == 5000


def test_approval_without_evidence_is_not_confirmed():
    mi = {x["measure_id"]: x for x in demo.office_measure_inputs()}
    mi["thermostat_setback"]["incentive_status"]["ms_business_controls"] = {"status": "approved", "amount_usd": 1500}
    t = measure(run(mi=mi), "thermostat_setback")
    assert t["financials"]["confirmed"]["net_cost_usd"] == 6500
    inc = next(i for i in t["incentives"] if i["id"] == "ms_business_controls")
    assert "reported_by" in " ".join(inc["evidence_missing"])


# 6 -------------------------------------------------------------------------------------
def test_partial_rerun_does_not_revive_stale_plan():
    store = Store(":memory:")
    demo.reset(store)
    engine.analyze(store, "demo_office")
    bill = store.get_bill("demo_off_e23")
    bill["quantity"] *= 2
    store.save_bill(bill)
    assert engine.get_plan(store, "demo_office")["stale"] is True
    engine.analyze(store, "demo_office", selected=["04"])
    assert engine.get_plan(store, "demo_office")["stale"] is True
    meta = store.get_plan("demo_office")["provenance"]
    assert meta["versions"]["incentive_catalog"] and meta["versions"]["berdo_sha256"]


# 7 -------------------------------------------------------------------------------------
def test_upfront_cash_separate_from_total_budget():
    b = demo.office_building()
    b["upfront_cash_available_usd"] = 100
    f = measure(run(b=b), "led_lighting")["financials"]["confirmed"]
    assert f["within_total_budget"] is True
    assert f["upfront_cash_feasible"] is False
    assert f["funding_gap_usd"] == 52000 - 100
    b["upfront_cash_available_usd"] = None
    f = measure(run(b=b), "led_lighting")["financials"]["confirmed"]
    assert f["upfront_cash_feasible"] is None and f["funding_gap_usd"] is None


# 8 -------------------------------------------------------------------------------------
def test_missing_bill_amounts_are_unknown_not_zero():
    bills = demo.office_bills()
    for x in bills:
        x["total_usd"] = None
        x["line_items"] = []
    fuels = run(bs=bills)["09"].outputs["fuels"]
    for s in fuels.values():
        assert s["recorded_cost_usd"] is None and s["annual_cost_usd"] is None
        assert s["cost_coverage"]["bills_with_cost"] == 0


def test_partially_missing_amounts_show_known_subtotal():
    bills = demo.office_bills()
    bills[-2]["total_usd"] = None   # latest electricity bill
    bills[-2]["line_items"] = []
    e = run(bs=bills)["09"].outputs["fuels"]["electricity"]
    assert e["recorded_cost_usd"] is None and e["known_cost_subtotal_usd"] > 0
    assert e["cost_coverage"]["bills_with_cost"] == e["cost_coverage"]["bills_total"] - 1


# investigation targets ----------------------------------------------------------------------
def test_bill_comparisons_grouped_by_meter():
    bills = demo.office_bills() + [demo._bill("m2_0", "electricity", date(2026, 9, 1), date(2026, 10, 1), 10, "kWh",
                                              demo.ELEC, "Eversource", "E-9999")]
    r = run(bs=bills)
    for c in r["02"].outputs["changes"]:
        assert c["account"] in ("E-1001", "G-2001")


def test_task_edits_survive_regeneration_and_export(client):
    client.post("/api/demo/reset")
    client.post("/api/buildings/demo_office/analysis", json={})
    plan = client.get("/api/buildings/demo_office/plan").json()
    tid = plan["tasks"][0]["id"]
    client.patch(f"/api/buildings/demo_office/plan/tasks/{tid}", json={"status": "done", "owner": "Facilities lead"})
    rep = client.post("/api/buildings/demo_office/reports?fmt=md").json()
    text = client.get(f"/api/reports/{rep['id']}").text
    assert "Facilities lead" in text and "| done |" in text
    client.post("/api/buildings/demo_office/analysis", json={})
    t = next(x for x in client.get("/api/buildings/demo_office/plan").json()["tasks"] if x["id"] == tid)
    assert (t["status"], t["owner"]) == ("done", "Facilities lead")

"""MVP acceptance checks (brief section 14), exercised through the HTTP API."""

from datetime import date

from benji.store import Store

GAS_SHAPE = [2.1, 1.9, 1.55, 0.95, 0.45, 0.2, 0.15, 0.15, 0.25, 0.7, 1.35, 1.95]


def _csv(months=13, start=date(2025, 9, 1)):
    rows = ["fuel,utility,account,period_start,period_end,quantity,unit,total_usd,fixed_charges_usd,energy_charges_usd"]
    y, m = start.year, start.month
    for _ in range(months):
        s = date(y, m, 1)
        y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        e = date(y2, m2, 1)
        kwh, therms = 40000, 1500 * GAS_SHAPE[m - 1]
        rows.append(f"electricity,Eversource,E1,{s},{e},{kwh},kWh,{100 + kwh * 0.2:.2f},100,{kwh * 0.2:.2f}")
        rows.append(f"gas,National Grid,G1,{s},{e},{therms:.1f},therms,{50 + therms * 1.5:.2f},50,{therms * 1.5:.2f}")
        y, m = y2, m2
    return "\n".join(rows).encode()


NEW_OFFICE = {
    "name": "Test Office", "category": "commercial_office", "state": "MA", "zip": "02108",
    "gross_floor_area_sqft": 30000, "heating_fuel": "natural_gas", "energy_sources": ["electricity", "natural_gas"],
    "electric_utility": "Eversource", "gas_utility": "National Grid", "budget_usd": 20000,
    "bill_payer": "owner", "decision_maker": "owner", "bills_cover_whole_building": True,
    "equipment": [{"id": "b1", "kind": "boiler", "fuel": "natural_gas", "efficiency": 82, "efficiency_unit": "AFUE",
                   "condition": "working"}],
    "lighting": {"fixture_count": 300, "existing_watts_per_fixture": 64, "technology": "fluorescent_t8",
                 "annual_operating_hours": 3000},
    "schedule": {"heating_setback_in_place": False},
}


def _new_user_with_bills(client):
    b = client.post("/api/buildings", json=NEW_OFFICE).json()
    r = client.post(f"/api/buildings/{b['id']}/bills/import", files={"file": ("bills.csv", _csv(), "text/csv")}).json()
    assert not r["errors"] and len(r["saved_pending"]) == 26
    assert all(x["status"] == "pending_confirmation" for x in r["saved_pending"])
    for bill in r["saved_pending"]:
        assert client.post(f"/api/bills/{bill['id']}/confirm").status_code == 200
    return b, r["saved_pending"]


def test_1_primary_journey_and_2_plan_survives_refresh(client):
    b, _ = _new_user_with_bills(client)
    client.put(f"/api/buildings/{b['id']}/measure-inputs/led_lighting",
               json={"measure_id": "led_lighting", "quoted_cost_usd": 15000, "params": {"proposed_watts_per_fixture": 30}})
    a = client.post(f"/api/buildings/{b['id']}/analysis", json={}).json()
    assert all(a["results"][s]["status"] in ("completed", "needs_data") for s in a["selected_skills"])
    led = next(m for m in a["results"]["10"]["outputs"]["measures"] if m["measure_id"] == "led_lighting")
    # 300 x (64-30) x 3000 / 1000 = 30,600 kWh at the bill-derived usage rate $0.20 = $6,120
    assert led["annual_energy_change"]["electricity_kwh"] == -30600
    assert led["annual_operating_savings_usd"] == 6120
    assert led["financials"]["confirmed"]["payback"]["years"] == round(15000 / 6120, 1)
    plan = client.get(f"/api/buildings/{b['id']}/plan").json()
    assert plan["recommendations"] and plan["next_action"]
    rep = client.post(f"/api/buildings/{b['id']}/reports").json()
    assert client.get(f"/api/reports/{rep['id']}").status_code == 200
    # "refresh": a brand-new store on the same database file sees the same plan
    from benji import api
    fresh = Store(api.store.path)
    assert fresh.get_plan(b["id"])["recommendations"] == plan["recommendations"]
    # task edits persist
    tid = plan["tasks"][0]["id"]
    client.patch(f"/api/buildings/{b['id']}/plan/tasks/{tid}", json={"status": "in_progress"})
    assert Store(api.store.path).get_plan(b["id"])["tasks"][0]["status"] == "in_progress"


def test_3_correcting_a_bill_invalidates_results(client):
    b, bills = _new_user_with_bills(client)
    a1 = client.post(f"/api/buildings/{b['id']}/analysis", json={}).json()
    first = client.post(f"/api/buildings/{b['id']}/reports").json()
    elec = [x for x in bills if x["fuel"] == "electricity"][-1]  # most recent bill, inside the 12-month window
    corrected = next(x for x in client.get(f"/api/buildings/{b['id']}/bills").json() if x["id"] == elec["id"])
    corrected["quantity"] = 80000
    client.put(f"/api/bills/{elec['id']}", json=corrected)
    a = client.get(f"/api/buildings/{b['id']}/analysis").json()
    assert a["stale"] and "bills" in a["changed_inputs"] and "09" in a["stale_skills"]
    assert client.get(f"/api/buildings/{b['id']}/plan").json()["stale"] is True
    assert client.post(f"/api/buildings/{b['id']}/reports").status_code == 409  # no export of stale results
    a2 = client.post(f"/api/buildings/{b['id']}/analysis", json={}).json()
    assert not a2["stale"]
    q1 = a1["results"]["09"]["outputs"]["fuels"]["electricity"]["recorded_quantity"]
    q2 = a2["results"]["09"]["outputs"]["fuels"]["electricity"]["recorded_quantity"]
    assert q2 == q1 + 40000
    # earlier export is preserved as a dated snapshot
    assert first["id"] in [r["id"] for r in client.get(f"/api/buildings/{b['id']}/reports").json()]
    hist = next(x for x in client.get(f"/api/buildings/{b['id']}/bills").json() if x["id"] == elec["id"])
    assert hist["corrections"][0]["fields"] == ["quantity"] and hist["source"]["kind"] == "csv"


def test_4_conflicting_data_gives_actionable_explanation(client):
    b, bills = _new_user_with_bills(client)
    dup = {k: v for k, v in bills[0].items() if k not in ("id",)}
    dup["period_start"], dup["period_end"], dup["status"] = "2025-09-15", "2025-10-15", "confirmed"
    client.post(f"/api/buildings/{b['id']}/bills", json=dup)
    a = client.post(f"/api/buildings/{b['id']}/analysis", json={}).json()
    issues = a["results"]["03"]["outputs"]["issues"]
    overlap = [i for i in issues if i["code"] == "overlap"]
    assert overlap and "double-counted" in overlap[0]["correction_action"]
    plan = client.get(f"/api/buildings/{b['id']}/plan").json()
    assert plan["recommendations"][0]["id"] == "rec_fix_data"
    # missing profile data is explained, not guessed
    b2 = client.post("/api/buildings", json={"name": "Bare", "category": "multifamily"}).json()
    a2 = client.post(f"/api/buildings/{b2['id']}/analysis", json={}).json()
    assert a2["results"]["04"]["status"] == "needs_data"
    labels = [m["field"] for m in a2["results"]["04"]["missing_inputs"]]
    assert "gross_floor_area_sqft" in labels and "dwelling_units" in labels
    plan2 = a2["results"]["17"]["outputs"]["plan"]
    assert plan2["recommendations"][0]["id"] == "rec_complete_profile"


def test_5_unsuitable_peer_group_gives_no_confident_comparison(demo):
    a = demo.post("/api/buildings/demo_residential/analysis", json={}).json()
    bm = a["results"]["07"]
    assert bm["outputs"]["result"] == "insufficient_comparable_data" and "percentile" not in bm["outputs"]
    # too-small sample: demand 10,000 peers
    a = demo.post("/api/buildings/demo_office/analysis",
                  json={"settings": {"peer_filters": {"min_sample": 10000}}}).json()
    assert a["results"]["07"]["outputs"]["result"] == "insufficient_comparable_data"
    assert "Insufficient comparable data" in a["results"]["07"]["message"]


def test_6_residential_never_gets_commercial_incentives(demo):
    a = demo.post("/api/buildings/demo_residential/analysis", json={}).json()
    ids = [r["incentive_id"] for r in a["results"]["14"]["outputs"]["results"]]
    assert ids and not any(i.startswith("ms_business") for i in ids)
    heat_loan = next(r for r in a["results"]["14"]["outputs"]["results"] if r["incentive_id"] == "ms_heat_loan")
    assert heat_loan["status"] == "Known condition not met"  # 8 units > 4
    a = demo.post("/api/buildings/demo_office/analysis", json={}).json()
    assert not any(r["incentive_id"].startswith("ms_multifamily") for r in a["results"]["14"]["outputs"]["results"])


def _measure(a, mid):
    return next(m for m in a["results"]["10"]["outputs"]["measures"] if m["measure_id"] == mid)


def test_7_unverified_incentive_excluded_from_confirmed_scenario(demo):
    a = demo.post("/api/buildings/demo_office/analysis", json={}).json()
    led = _measure(a, "led_lighting")
    assert led["financials"]["confirmed"]["net_cost_usd"] == 52000       # $12k estimate not counted
    assert led["financials"]["hypothetical"]["net_cost_usd"] == 40000    # shown only as hypothetical


def test_8_later_reimbursement_not_treated_as_upfront_cash(demo):
    a = demo.post("/api/buildings/demo_office/analysis", json={}).json()
    t = _measure(a, "thermostat_setback")["financials"]["confirmed"]
    assert t["net_cost_usd"] == 5000 and t["upfront_cash_required_usd"] == 6500


def test_9_overlapping_measures_not_double_counted(demo):
    a = demo.post("/api/buildings/demo_office/analysis", json={}).json()
    sc = next(s for s in a["results"]["10"]["outputs"]["scenarios"] if s["scenario"] == "envelope_then_electrification")
    heating = a["results"]["09"]["outputs"]["fuels"]["natural_gas"]["heating_split"]["heating"]
    combined = -sc["annual_energy_change"]["natural_gas_therms"]
    standalone = -sc["sum_of_standalone_changes"]["natural_gas_therms"]
    assert combined <= heating + 0.5 < standalone


def test_10_operating_cost_increase_is_shown(demo):
    a = demo.post("/api/buildings/demo_office/analysis", json={}).json()
    hp = _measure(a, "heat_pump_heating")
    assert hp["operating_cost_increases"] is True
    assert hp["annual_operating_cost_change_usd"] > 0 and hp["annual_emissions_change_kgco2e"] < 0
    assert hp["financials"]["confirmed"]["payback"]["years"] is None
    assert any("INCREASES" in w for w in a["results"]["10"]["warnings"])


def test_11_synthetic_data_labelled_in_results_and_report(demo):
    a = demo.post("/api/buildings/demo_office/analysis", json={}).json()
    assert a["data_label"] == "synthetic_demo"
    rep = demo.post("/api/buildings/demo_office/reports").json()
    html = demo.get(f"/api/reports/{rep['id']}").text
    assert "SYNTHETIC DEMONSTRATION DATA" in html and rep["meta"]["synthetic"] is True
    md = demo.post("/api/buildings/demo_office/reports?fmt=md").json()
    assert demo.get(f"/api/reports/{md['id']}").text.startswith("> **SYNTHETIC DEMONSTRATION DATA.**")


def test_12_workflow_survives_model_failure(demo, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "invalid-test-key")
    monkeypatch.setenv("BENJI_AI_URL", "http://127.0.0.1:9/unreachable")
    a = demo.post("/api/buildings/demo_office/analysis", json={}).json()
    assert a["results"]["17"]["status"] == "completed"
    ex = demo.get("/api/buildings/demo_office/explain/07").json()
    assert ex["mode"] == "deterministic" and "unavailable" in ex["notice"]
    assert "benchmark.position" in ex["evidence_ids"]


def test_skill_checkboxes_change_behaviour(demo):
    full = demo.post("/api/buildings/demo_office/analysis", json={}).json()
    no_elig = demo.post("/api/buildings/demo_office/analysis",
                        json={"skills": ["04", "01", "03", "09", "13", "10", "17", "20"]}).json()
    assert no_elig["results"]["14"]["status"] == "not_selected"
    t_full = _measure(full, "thermostat_setback")["financials"]["confirmed"]["net_cost_usd"]
    t_none = _measure(no_elig, "thermostat_setback")["financials"]["confirmed"]["net_cost_usd"]
    assert (t_full, t_none) == (5000, 6500)
    no_costs = demo.post("/api/buildings/demo_office/analysis", json={"skills": ["04", "01", "10", "07", "17"]}).json()
    assert no_costs["results"]["10"]["status"] == "blocked_by_prerequisite"
    assert no_costs["results"]["07"]["status"] == "blocked_by_prerequisite"
    plan = demo.get("/api/buildings/demo_office/plan").json()
    assert not any(r["measure_id"] == "led_lighting" for r in plan["recommendations"])
    # future skills cannot be run
    r = demo.post("/api/buildings/demo_office/analysis", json={"skills": ["05", "04"]}).json()
    assert r["ignored_skills"]["coming_later"] == ["05"]


def test_registry_has_20_skills_with_13_implemented(client):
    s = client.get("/api/skills").json()["skills"]
    assert len(s) == 20
    impl = sorted(x["id"] for x in s if x["implementation_status"] == "implemented")
    assert impl == ["01", "02", "03", "04", "06", "07", "08", "09", "10", "13", "14", "17", "20"]
    assert {x["id"] for x in s if x["mandatory"]} == {"03", "04"}
    for x in s:
        for k in ("purpose", "inputs", "outputs", "data_prerequisites", "evidence_and_assumptions", "failure_behavior"):
            assert x[k]

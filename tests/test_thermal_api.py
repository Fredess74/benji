"""Room scenario persistence, plan/report integration, readiness checklist and documents through the API."""

import io


def test_demo_room_scenario_in_analysis_plan_and_report(demo):
    a = demo.post("/api/buildings/demo_office/analysis", json={}).json()
    rows = a["results"]["08"]["outputs"]["scenarios"][0]["scenarios"]
    cur, env, hp = rows
    assert cur["status"] == "reachable" and env["time_to_target_h"] < cur["time_to_target_h"]
    # carrier change: heat pump priced at the bill-derived ELECTRICITY rate, never the gas price
    assert hp["consumed_energy"]["unit"] == "kWh"
    assert hp["variable_energy_cost_usd"] == round(hp["consumed_energy"]["quantity"] * 0.24, 2)
    plan = demo.get("/api/buildings/demo_office/plan").json()
    assert any(r["id"] == "rec_thermal_demo_th_suite" for r in plan["recommendations"])
    rep = demo.post("/api/buildings/demo_office/reports?fmt=md").json()
    text = demo.get(f"/api/reports/{rep['id']}").text
    assert "Room heating & cooling scenarios" in text and "sensible-only" in text


def test_editing_scenario_marks_results_stale(demo):
    demo.post("/api/buildings/demo_office/analysis", json={})
    sc = demo.get("/api/buildings/demo_office/thermal-scenarios").json()[0]
    sc["inputs"]["heat_loss_coefficient_w_per_k"] = 500
    body = {k: sc[k] for k in ("name", "inputs", "alternatives", "add_to_plan", "selected_alternative")}
    assert demo.put(f"/api/buildings/demo_office/thermal-scenarios/{sc['id']}", json=body).status_code == 200
    a = demo.get("/api/buildings/demo_office/analysis").json()
    assert a["stale"] and "08" in a["stale_skills"]
    assert demo.get("/api/buildings/demo_office/plan").json()["stale"] is True


def test_area_only_scenario_asks_for_facts(client):
    r = client.post("/api/thermal/simulate", json={"name": "x", "inputs": {
        "room_name": "Living room", "floor_area": 25, "initial_temp": 16, "target_temp": 21, "outdoor_temp": -8,
        "hvac": {"mode": "heating"}}}).json()
    cur = r["scenarios"][0]
    assert cur["status"] == "needs_data" and len(cur["missing"]) >= 3


def test_bad_alternative_rejected_with_field(client):
    r = client.post("/api/thermal/simulate", json={"name": "x", "inputs": {
        "room_name": "r", "initial_temp": 16, "target_temp": 21, "outdoor_temp": -8,
        "heat_loss_coefficient_w_per_k": 100, "effective_capacity_kwh_per_k": 1,
        "hvac": {"mode": "heating", "thermal_output_kw": 3}},
        "alternatives": [{"name": "bad", "overrides": {"heat_loss_coefficient_w_per_k": -1}}]})
    assert r.status_code == 422 and r.json()["detail"][0]["field"].startswith("alternatives.0")


def test_readiness_checklist_never_claims_capacity(demo):
    r = demo.get("/api/buildings/demo_office/electrification-readiness").json()
    assert r["status"] == "evidence_incomplete"
    assert "does not calculate available electrical capacity" in r["disclaimer"]
    assert any(m["item"].startswith("Service size") for m in r["missing"])


def test_document_upload_candidates_and_annotation_link(demo):
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, "PANEL LP-1  200A  208Y/120V")
    c.drawString(72, 700, "RTU-1 15 kW")
    c.save()
    d = demo.post("/api/buildings/demo_office/documents?kind=panel_schedule",
                  files={"file": ("panel.pdf", buf.getvalue(), "application/pdf")}).json()
    assert d["extraction"] == "text_candidates"
    assert all(x["status"] == "unconfirmed_candidate" and len(x["bbox"]) == 4 for x in d["candidates"])
    ann = demo.post("/api/buildings/demo_office/annotations", json={
        "document_id": d["id"], "page": 1, "bbox": [72, 60, 200, 75], "label": "RTU-1 nameplate", "value": 15,
        "unit": "kW", "links": {"equipment_id": "eq_rtu"}}).json()
    b = demo.get("/api/buildings/demo_office").json()
    assert ann["id"] in next(e for e in b["equipment"] if e["id"] == "eq_rtu")["evidence_refs"]
    r = demo.get("/api/buildings/demo_office/electrification-readiness").json()
    assert r["reference_documents"][0]["document_id"] == d["id"]
    bad = demo.post("/api/buildings/demo_office/annotations", json={
        "document_id": d["id"], "page": 1, "label": "x", "links": {"equipment_id": "nope"}})
    assert bad.status_code == 422

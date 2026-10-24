"""Assistant channels: HTTP /assistant (ChatGPT Actions / OpenClaw) and the MCP server (Claude)."""

import asyncio
import json

import pytest

CAFE = {"property_type": "small_business", "name": "Test Cafe", "zip": "02139", "business_type": "food_service",
        "occupant_role": "business_tenant", "heating_fuel": "natural_gas", "electric_utility": "Eversource",
        "gas_utility": "Eversource", "floor_area_sqft": 1400, "budget_usd": 5000, "cash_available_usd": 1000,
        "bills_cover_whole_building": True}


def _bills():
    out = []
    for i in range(12):
        y, m = (2025, 10 + i) if i < 3 else (2026, i - 2)
        out.append({"fuel": "electricity", "month": f"{y}-{m:02d}", "quantity": 4000, "unit": "kWh", "total_usd": 1105,
                    "fixed_charge_usd": 25})
        out.append({"fuel": "natural_gas", "month": f"{y}-{m:02d}", "quantity": 60 + 15 * (m in (12, 1, 2)) * 6,
                    "unit": "therms", "total_usd": 150, "fixed_charge_usd": 20})
    return out


def test_http_journey_for_small_business(client):
    p = client.post("/assistant/properties", json=CAFE).json()
    pid = p["property_id"]
    r = client.post(f"/assistant/properties/{pid}/bills", json={"bills": _bills(), "confirmed": False}).json()
    assert r["saved"] == 24 and r["status"] == "pending_confirmation"
    s = client.post(f"/assistant/properties/{pid}/analyze").json()
    assert any("Confirm" in x or "confirm" in x for x in s["information_that_would_help"] + [s["next_action"] or ""])
    assert client.post(f"/assistant/properties/{pid}/bills/confirm", json={}).json()["confirmed"] == 24
    s = client.post(f"/assistant/properties/{pid}/analyze").json()
    assert s["decision_ready"] is True
    assert any("electricity: 48,000 kWh" in line for line in s["what_we_found"])
    assert s["what_to_do_first"][0]["action"] == "Review operating schedules and controls"
    assert "landlord" in s["who_decides"]["note"]
    assert all(not pr["program"].startswith("Mass Save multifamily") for pr in s["programs_to_check"])
    plan = client.get(f"/assistant/properties/{pid}/plan").json()
    assert plan["tasks"] and plan["next_action"]


def test_minimal_home_without_bills_gets_useful_plan(client):
    p = client.post("/assistant/properties", json={"property_type": "home", "name": "My apartment",
                                                    "occupant_role": "renter"}).json()
    s = client.post(f"/assistant/properties/{p['property_id']}/analyze").json()
    titles = [a["action"] for a in s["what_to_do_first"]]
    assert titles[0] == "Collect the information Benji needs"
    p2 = client.post("/assistant/properties", json={"property_type": "small_business", "name": "x"}).json()
    s2 = client.post(f"/assistant/properties/{p2['property_id']}/analyze").json()
    assert s2["what_to_do_first"][0]["action"] == "Tell Benji a few basics about the property"
    assert "Obtain a professional energy assessment" in titles
    assert s["information_that_would_help"]


def test_http_validation_errors_are_field_level(client):
    r = client.post("/assistant/properties", json={"property_type": "castle", "name": "x"})
    assert r.status_code == 422 and r.json()["detail"][0]["field"] == "property_type"
    pid = client.post("/assistant/properties", json={"property_type": "home", "name": "h"}).json()["property_id"]
    r = client.post(f"/assistant/properties/{pid}/bills",
                    json={"bills": [{"fuel": "electricity", "month": "2026-13", "quantity": -1, "unit": "kWh"}]}).json()
    assert r["saved"] == 0 and {e["field"] for e in r["errors"]} >= {"bills.0.month", "bills.0.quantity"}
    assert client.post("/assistant/properties/nope/analyze").status_code == 404


def test_api_key_enforced_when_set(client, monkeypatch):
    monkeypatch.setenv("BENJI_API_KEY", "s3cret")
    assert client.get("/assistant/properties").status_code == 401
    assert client.get("/assistant/properties", headers={"authorization": "Bearer s3cret"}).status_code == 200

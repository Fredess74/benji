"""Independent physical checks for the single-zone heating/cooling model.

The analytical case is deliberately synthetic (a numerical oracle, not a building default):
C=2 kWh/K, H=0.2 kW/K, outdoor 0 C, initial 10 C, target 20 C, 6 kW heating, no gains.
Equilibrium 30 C; time = 10*ln(2) = 6.931 h; delivered 41.589 kWh; at COP 3 electricity = 13.863 kWh.
"""

import math

import pytest
from pydantic import ValidationError

from benji.thermal import ScenarioInputs, compare, simulate, simulate_numeric, time_to_target


def base(**kw):
    d = {"room_name": "Test room", "initial_temp": 10, "target_temp": 20, "outdoor_temp": 0,
         "heat_loss_coefficient_w_per_k": 200, "heat_loss_source": "synthetic test",
         "effective_capacity_kwh_per_k": 2, "capacity_source": "synthetic test",
         "hvac": {"mode": "heating", "thermal_output_kw": 6, "efficiency_kind": "COP", "efficiency_value": 3,
                  "carrier": "electricity"}, "energy_price_usd_per_unit": 0.20, "energy_price_source": "test"}
    for k, v in kw.items():
        if k == "hvac":
            d["hvac"] = {**d["hvac"], **v}
        else:
            d[k] = v
    return ScenarioInputs(**d)


def test_analytical_oracle():
    r = simulate(base())
    assert r["status"] == "reachable"
    assert r["equilibrium_temp_c"] == pytest.approx(30)
    assert r["time_to_target_h"] == pytest.approx(10 * math.log(2), abs=1e-3)
    assert r["delivered_thermal_kwh"] == pytest.approx(41.589, abs=1e-3)
    assert r["consumed_energy"]["quantity"] == pytest.approx(13.863, abs=1e-3)
    assert r["variable_energy_cost_usd"] == pytest.approx(2.77, abs=0.01)
    assert r["load_to_hold_target_kw"] == pytest.approx(4.0)
    assert r["capacity_headroom_kw"] == pytest.approx(2.0)


@pytest.mark.parametrize("dt", [0.5, 0.1, 0.01])
def test_numeric_solver_agrees_and_is_resolution_stable(dt):
    t = simulate_numeric(2, 0.2, 0, 10, 20, 6, 0, 1, dt, 48)
    assert t == pytest.approx(10 * math.log(2), rel=2e-3)


def test_zero_heat_loss_is_linear():
    t, _ = time_to_target(C=2, H=0, T_ref=0, T0=10, Tt=20, Q=6, G=0, s=1)
    assert t == pytest.approx(10 * 2 / 6)


def test_already_at_target():
    r = simulate(base(initial_temp=20))
    assert r["time_to_target_h"] == 0 and r["delivered_thermal_kwh"] == 0


def test_zero_output_and_insufficient_capacity_terminate_clearly():
    r = simulate(base(hvac={"thermal_output_kw": 0}))
    assert r["status"] == "target_not_reachable" and "equilibrium" in r["reason"]
    r = simulate(base(hvac={"thermal_output_kw": 3}))  # needs 4 kW to hold 20 C
    assert r["status"] == "target_not_reachable" and r["capacity_shortfall"] is True
    assert r["capacity_headroom_kw"] == pytest.approx(-1.0)


def test_exact_equilibrium_at_target_is_not_reachable():
    r = simulate(base(hvac={"thermal_output_kw": 4}))
    assert r["status"] == "target_not_reachable" and "asymptotically" in r["reason"]


def test_cooling_sign():
    r = simulate(base(initial_temp=30, target_temp=24, outdoor_temp=32,
                      hvac={"mode": "cooling", "thermal_output_kw": 5}))
    assert r["status"] == "reachable"
    assert r["equilibrium_temp_c"] == pytest.approx(32 - 5 / 0.2)
    assert r["cooling_model"] == "sensible_only"
    assert r["load_to_hold_target_kw"] == pytest.approx(0.2 * 8)
    # heating mode cannot cool
    r = simulate(base(initial_temp=30, target_temp=24, outdoor_temp=32))
    assert r["status"] == "target_not_reachable"


def test_fahrenheit_and_area_conversions():
    r = simulate(base(temperature_unit="F", initial_temp=50, target_temp=68, outdoor_temp=32))
    assert r["time_to_target_h"] == pytest.approx(10 * math.log(2), abs=1e-3)
    s = ScenarioInputs(**{**base().model_dump(), "floor_area": 1000, "floor_area_unit": "sqft",
                          "ceiling_height": 10, "ceiling_height_unit": "ft"})
    assert s.volume_m3() == pytest.approx(283.168, rel=1e-4)  # 10,000 ft3


def test_monotonic_physics():
    t_lo = simulate(base(heat_loss_coefficient_w_per_k=150))
    t_hi = simulate(base(heat_loss_coefficient_w_per_k=250))
    assert t_hi["delivered_thermal_kwh"] > t_lo["delivered_thermal_kwh"]
    heavy = simulate(base(effective_capacity_kwh_per_k=4))
    assert heavy["time_to_target_h"] > simulate(base())["time_to_target_h"]


def test_missing_inputs_are_requested_not_invented():
    s = ScenarioInputs(room_name="Office 2", floor_area=30, initial_temp=15, target_temp=21, outdoor_temp=-5,
                       hvac={"mode": "heating"})
    r = simulate(s)
    assert r["status"] == "needs_data"
    fields = {m["field"] for m in r["missing"]}
    assert {"heat_loss_coefficient_w_per_k", "effective_capacity_kwh_per_k", "hvac.thermal_output_kw"} <= fields


def test_surface_based_heat_loss_and_air_only_bound():
    s = ScenarioInputs(room_name="r", floor_area=20, ceiling_height=2.5, initial_temp=15, target_temp=21,
                       outdoor_temp=-5, air_changes_per_hour=0.5, capacity_basis="air_only_lower_bound",
                       surfaces=[{"name": "wall", "area": 12, "u_value_w_m2k": 0.5, "boundary": "exterior"},
                                 {"name": "window", "area": 3, "r_value_ip": 2, "boundary": "exterior"},
                                 {"name": "party wall", "area": 10, "boundary": "adjacent_conditioned"}],
                       hvac={"mode": "heating", "thermal_output_kw": 2})
    r = simulate(s)
    ua = 12 * 0.5 + 3 * 5.678263 / 2 + 1.2 * 1.005 / 3.6 * 0.5 * 50
    assert r["heat_loss_coefficient_kw_per_k"] == pytest.approx(ua / 1000, rel=1e-3)
    assert any("LOWER BOUND" in a["text"] for a in r["assumptions"])
    assert r["consumed_energy"] is None  # efficiency not given -> no invented energy


@pytest.mark.parametrize("bad", [
    {"hvac": {"efficiency_kind": "COP", "efficiency_value": 0.3}},
    {"hvac": {"efficiency_kind": "combustion_efficiency_pct", "efficiency_value": 0.82, "carrier": "natural_gas"}},
    {"heat_loss_coefficient_w_per_k": -10},
    {"initial_temp": float("nan")},
    {"target_temp": 500},
])
def test_invalid_inputs_rejected(bad):
    with pytest.raises(ValidationError):
        base(**bad)


def test_gas_carrier_and_alternatives():
    b = base(hvac={"efficiency_kind": "combustion_efficiency_pct", "efficiency_value": 80, "carrier": "natural_gas"},
             energy_price_usd_per_unit=1.6).model_dump()
    out = compare(b, [{"name": "air sealing (H 200->150 W/K, assessor estimate)",
                       "overrides": {"heat_loss_coefficient_w_per_k": 150}},
                      {"name": "heat pump 6 kW COP 2.5",
                       "overrides": {"hvac": {"efficiency_kind": "COP", "efficiency_value": 2.5, "carrier": "electricity"},
                                     "energy_price_usd_per_unit": 0.24}}])
    cur, env, hp = out["scenarios"]
    assert cur["consumed_energy"]["unit"] == "therms"
    assert cur["consumed_energy"]["quantity"] == pytest.approx(41.589 / 0.8 * 3.412 / 100, rel=1e-3)
    assert env["time_to_target_h"] < cur["time_to_target_h"]
    assert hp["consumed_energy"]["unit"] == "kWh"

"""Explicit, resettable demonstration mode.

Everything here is SYNTHETIC: buildings, bills, quotes, rates and contractor values are invented
for demonstration and are labelled ``synthetic_demo`` everywhere they appear. The flat rates are
test values, not Massachusetts market assumptions.
"""

from __future__ import annotations

from datetime import date

from .store import Store

SYN = "synthetic_demo"
# Synthetic flat tariffs (demo values only).
ELEC = {"usage_rate": 0.24, "fixed_monthly": 150.0}
GAS = {"usage_rate": 1.60, "fixed_monthly": 60.0}
RES_ELEC = {"usage_rate": 0.26, "fixed_monthly": 10.0}
RES_GAS = {"usage_rate": 1.70, "fixed_monthly": 15.0}

# Relative monthly shape (Jan..Dec), synthetic.
ELEC_SHAPE = [0.95, 0.92, 0.93, 0.90, 0.97, 1.10, 1.22, 1.20, 1.05, 0.93, 0.92, 0.96]
GAS_SHAPE = [2.10, 1.90, 1.55, 0.95, 0.45, 0.20, 0.15, 0.15, 0.25, 0.70, 1.35, 1.95]


def _months(start: date, n: int):
    y, m = start.year, start.month
    for _ in range(n):
        s = date(y, m, 1)
        y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        yield s, date(y2, m2, 1)
        y, m = y2, m2


def _bill(bid, fuel, s, e, qty, unit, tariff, utility, account):
    fixed = tariff["fixed_monthly"]
    usage = round(qty * tariff["usage_rate"], 2)
    return {
        "id": bid, "fuel": fuel, "utility": utility, "account": account,
        "period_start": s.isoformat(), "period_end": e.isoformat(), "quantity": round(qty, 1), "unit": unit,
        "line_items": [{"description": "Customer charge (synthetic)", "category": "fixed", "amount_usd": fixed},
                       {"description": "Usage-based supply and delivery (synthetic)", "category": "energy", "amount_usd": usage}],
        "total_usd": round(fixed + usage, 2), "source": {"kind": "demo", "filename": None},
        "extraction_confidence": "high", "uncertain_fields": [], "status": "confirmed", "data_label": SYN,
    }


def office_building() -> dict:
    return {
        "id": "demo_office", "name": "Harbor Street Office (SYNTHETIC DEMO)", "category": "commercial_office",
        "city": "Boston", "state": "MA", "zip": "02110", "gross_floor_area_sqft": 52000, "year_built": 1978,
        "heating_fuel": "natural_gas", "energy_sources": ["electricity", "natural_gas"],
        "electric_utility": "Eversource", "gas_utility": "National Grid",
        "schedule": {"weekday_occupied_hours": "07:00-19:00", "weekend_occupied": False,
                     "heating_setback_in_place": False, "notes": "Thermostat schedules not reviewed since 2019 (synthetic)."},
        "equipment": [
            {"id": "eq_boiler", "kind": "boiler", "fuel": "natural_gas", "quantity": 2, "capacity": 2000,
             "capacity_unit": "MBH", "efficiency": 80, "efficiency_unit": "AFUE", "install_year": 2004, "condition": "working"},
            {"id": "eq_rtu", "kind": "rooftop_unit", "fuel": "electricity", "quantity": 4, "install_year": 2011, "condition": "working"},
        ],
        "lighting": {"fixture_count": 620, "existing_watts_per_fixture": 64, "technology": "fluorescent_t8",
                     "annual_operating_hours": 3600},
        "budget_usd": 90000, "upfront_cash_available_usd": 90000,
        "bill_payer": "owner", "decision_maker": "owner (asset manager)", "bills_cover_whole_building": True,
        "eligibility_answers": {"equipment_on_qualified_list": True},
        "operating_changes": [{"date": "2026-03-01", "description": "New tenant on floor 4 with extended evening hours (synthetic)"}],
        "data_label": SYN,
    }


def office_bills() -> list[dict]:
    bills = []
    for i, (s, e) in enumerate(_months(date(2024, 10, 1), 24)):
        kwh = 78000 * ELEC_SHAPE[s.month - 1]
        if s >= date(2026, 3, 1):
            kwh *= 1.30  # tenant change (recorded)
        therms = 2500 * GAS_SHAPE[s.month - 1]
        if s == date(2026, 1, 1):
            therms *= 1.45  # unexplained spike
        bills.append(_bill(f"demo_off_e{i:02d}", "electricity", s, e, kwh, "kWh", ELEC, "Eversource", "E-1001"))
        bills.append(_bill(f"demo_off_g{i:02d}", "natural_gas", s, e, therms, "therms", GAS, "National Grid", "G-2001"))
    return bills


def office_measure_inputs() -> list[dict]:
    return [
        {"measure_id": "led_lighting", "quoted_cost_usd": 52000, "cost_source": "synthetic contractor quote",
         "params": {"proposed_watts_per_fixture": 30},
         "incentive_status": {"ms_business_lighting": {"status": "not_reviewed", "amount_usd": 12000,
                                                       "note": "Distributor estimate, not confirmed (synthetic)"}}},
        {"measure_id": "thermostat_setback", "quoted_cost_usd": 6500, "cost_source": "synthetic contractor quote",
         "params": {}, "incentive_status": {"ms_business_controls": {
             "status": "approved", "amount_usd": 1500, "reported_by": "owner (asset manager)",
             "reported_on": "2026-10-20", "reference": "SYNTHETIC-APPROVAL-0001",
             "note": "User-reported approval letter; paid after installation (synthetic)"}}},
        {"measure_id": "heat_pump_heating", "quoted_cost_usd": 480000, "cost_source": "synthetic contractor budget estimate",
         "params": {"seasonal_cop": 2.6, "coverage_fraction": 1.0, "cop_source": "synthetic contractor proposal"},
         "incentive_status": {"ms_business_heat_pump": {"status": "not_reviewed", "amount_usd": 60000,
                                                        "note": "Illustrative only (synthetic)"}}},
    ]


def residential_building() -> dict:
    return {
        "id": "demo_residential", "name": "Elm Court Apartments, 8 units (SYNTHETIC DEMO)", "category": "multifamily",
        "city": "Somerville", "state": "MA", "zip": "02144", "gross_floor_area_sqft": 7200, "year_built": 1925,
        "dwelling_units": 8, "heating_fuel": "natural_gas", "energy_sources": ["electricity", "natural_gas"],
        "electric_utility": "National Grid", "gas_utility": "National Grid",
        "schedule": {"heating_setback_in_place": False, "notes": "Central boiler, single thermostat (synthetic)."},
        "equipment": [{"id": "eq_boiler", "kind": "boiler", "fuel": "natural_gas", "quantity": 1, "efficiency": 82,
                       "efficiency_unit": "AFUE", "install_year": 2009, "condition": "working"}],
        "lighting": {"technology": "unknown"},
        "budget_usd": 15000, "upfront_cash_available_usd": 15000,
        "bill_payer": "owner (house meter and central heat); tenants pay unit electricity",
        "bills_cover_whole_building": False,
        "decision_maker": "owner",
        "data_label": SYN,
    }


def residential_bills() -> list[dict]:
    bills = []
    for i, (s, e) in enumerate(_months(date(2025, 10, 1), 12)):
        bills.append(_bill(f"demo_res_e{i:02d}", "electricity", s, e, 900 * ELEC_SHAPE[s.month - 1], "kWh", RES_ELEC,
                           "National Grid", "R-3001"))
        bills.append(_bill(f"demo_res_g{i:02d}", "natural_gas", s, e, 520 * GAS_SHAPE[s.month - 1], "therms", RES_GAS,
                           "National Grid", "R-4001"))
    return bills


def office_thermal_scenarios() -> list[dict]:
    """Synthetic room scenario: Monday-morning warm-up of a corner office suite after a weekend set-back."""
    return [{
        "id": "demo_th_suite", "name": "Floor 3 corner suite, Monday warm-up (SYNTHETIC)", "add_to_plan": True,
        "selected_alternative": "Air sealing + window film (H 420 -> 300 W/K, assessor estimate)",
        "inputs": {
            "room_name": "Floor 3 corner suite", "floor_area": 1800, "floor_area_unit": "sqft",
            "ceiling_height": 9, "ceiling_height_unit": "ft", "temperature_unit": "F",
            "initial_temp": 58, "target_temp": 70, "outdoor_temp": 20,
            "heat_loss_coefficient_w_per_k": 420, "heat_loss_source": "SYNTHETIC assessor estimate",
            "effective_capacity_kwh_per_k": 3.5, "capacity_source": "SYNTHETIC estimate (air + furniture + slab)",
            "internal_gains_w": 600, "gains_source": "SYNTHETIC: lighting and equipment at arrival",
            "hvac": {"mode": "heating", "thermal_output_kw": 18, "output_source": "SYNTHETIC hydronic zone rating",
                     "efficiency_kind": "combustion_efficiency_pct", "efficiency_value": 80, "carrier": "natural_gas"},
            "occupied_by_hours": 3, "horizon_hours": 12, "uncertainty_pct": {"H": 30, "C": 50},
        },
        "alternatives": [
            {"name": "Air sealing + window film (H 420 -> 300 W/K, assessor estimate)",
             "overrides": {"heat_loss_coefficient_w_per_k": 300}},
            {"name": "Cold-climate heat pump 12 kW at 20 F, COP 2.3 (SYNTHETIC spec)",
             "overrides": {"hvac": {"thermal_output_kw": 12, "efficiency_kind": "COP", "efficiency_value": 2.3,
                                    "carrier": "electricity", "output_source": "SYNTHETIC spec at 20 F"}}},
        ],
    }]


def cafe_building() -> dict:
    return {
        "id": "demo_cafe", "name": "Corner Bean Coffee, leased storefront (SYNTHETIC DEMO)", "category": "small_business",
        "business_type": "food_service", "occupant_role": "business_tenant", "city": "Cambridge", "state": "MA",
        "zip": "02139", "gross_floor_area_sqft": 1400, "heating_fuel": "natural_gas",
        "energy_sources": ["electricity", "natural_gas"], "electric_utility": "Eversource", "gas_utility": "Eversource",
        "schedule": {"weekday_occupied_hours": "06:30-18:00", "weekend_occupied": True, "heating_setback_in_place": False},
        "equipment": [{"id": "eq_furnace", "kind": "furnace", "fuel": "natural_gas", "efficiency": 80,
                       "efficiency_unit": "AFUE", "install_year": 2008, "condition": "working"}],
        "lighting": {"fixture_count": 40, "existing_watts_per_fixture": 32, "technology": "fluorescent_t8",
                     "annual_operating_hours": 4200},
        "budget_usd": 8000, "upfront_cash_available_usd": 3000, "bill_payer": "the cafe (tenant)",
        "decision_maker": "landlord for building systems; cafe owner for lighting and controls inside the unit",
        "bills_cover_whole_building": True, "data_label": SYN,
    }


def cafe_bills() -> list[dict]:
    bills = []
    for i, (s, e) in enumerate(_months(date(2025, 10, 1), 12)):
        bills.append(_bill(f"demo_cafe_e{i:02d}", "electricity", s, e, 3900 * ELEC_SHAPE[s.month - 1], "kWh",
                           {"usage_rate": 0.27, "fixed_monthly": 25.0}, "Eversource", "C-5001"))
        bills.append(_bill(f"demo_cafe_g{i:02d}", "natural_gas", s, e, 60 + 90 * GAS_SHAPE[s.month - 1], "therms",
                           {"usage_rate": 1.75, "fixed_monthly": 20.0}, "Eversource", "C-6001"))
    return bills


def cafe_measure_inputs() -> list[dict]:
    return [{"measure_id": "led_lighting", "quoted_cost_usd": 2400, "cost_source": "synthetic electrician quote",
             "params": {"proposed_watts_per_fixture": 15}, "incentive_status": {}},
            {"measure_id": "thermostat_setback", "quoted_cost_usd": 350, "cost_source": "synthetic quote",
             "params": {}, "incentive_status": {}}]


def home_building() -> dict:
    return {
        "id": "demo_home", "name": "Renter, 2-family house unit (SYNTHETIC DEMO)", "category": "home",
        "occupant_role": "renter", "city": "Dorchester", "state": "MA", "zip": "02124", "dwelling_units": 2,
        "heating_fuel": "natural_gas", "energy_sources": ["electricity", "natural_gas"],
        "electric_utility": "Eversource", "gas_utility": "National Grid",
        "schedule": {"heating_setback_in_place": False},
        "equipment": [{"id": "eq_boiler", "kind": "boiler", "fuel": "natural_gas", "efficiency": 82, "efficiency_unit": "AFUE",
                       "condition": "working"}],
        "budget_usd": 300, "upfront_cash_available_usd": 300, "bill_payer": "you (renter)", "decision_maker": "landlord",
        "bills_cover_whole_building": False, "data_label": SYN,
    }


def home_bills() -> list[dict]:
    bills = []
    for i, (s, e) in enumerate(_months(date(2025, 10, 1), 12)):
        bills.append(_bill(f"demo_home_e{i:02d}", "electricity", s, e, 420 * ELEC_SHAPE[s.month - 1], "kWh",
                           {"usage_rate": 0.30, "fixed_monthly": 8.0}, "Eversource", "H-7001"))
        bills.append(_bill(f"demo_home_g{i:02d}", "natural_gas", s, e, 12 + 70 * GAS_SHAPE[s.month - 1], "therms",
                           {"usage_rate": 1.85, "fixed_monthly": 12.0}, "National Grid", "H-8001"))
    return bills


def home_measure_inputs() -> list[dict]:
    return [{"measure_id": "thermostat_setback", "quoted_cost_usd": 120, "cost_source": "synthetic store price",
             "params": {}, "incentive_status": {}}]


def residential_measure_inputs() -> list[dict]:
    return [{"measure_id": "thermostat_setback", "quoted_cost_usd": 2800, "cost_source": "synthetic contractor quote",
             "params": {}, "incentive_status": {}}]


def reset(store: Store) -> list[str]:
    """Delete only demo buildings and recreate them. User buildings are untouched."""
    for b in store.list_buildings():
        if b.get("data_label") == SYN:
            store.delete_building(b["id"])
    ids = []
    for bld, bills, inputs, rooms in ((office_building(), office_bills(), office_measure_inputs(), office_thermal_scenarios()),
                                      (residential_building(), residential_bills(), residential_measure_inputs(), []),
                                      (cafe_building(), cafe_bills(), cafe_measure_inputs(), []),
                                      (home_building(), home_bills(), home_measure_inputs(), [])):
        store.save_building(bld)
        for b in bills:
            store.save_bill({**b, "building_id": bld["id"]})
        for mi in inputs:
            store.save_measure_inputs(bld["id"], mi)
        for th in rooms:
            store.save_child("thermal_scenarios", bld["id"], th, "th")
        ids.append(bld["id"])
    return ids

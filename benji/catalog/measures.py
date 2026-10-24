"""Supported improvement measures. Small on purpose: each one states what it needs,
how it is calculated, where assumptions come from, and what it cannot tell you."""

from __future__ import annotations

CATALOG_VERSION = "2026-10-24.2"

MEASURES: dict[str, dict] = {
    "operations_schedule_review": {
        "name": "Review operating schedules and controls",
        "kind": "assessment",
        "categories": ["home", "small_business", "commercial_office", "multifamily"],
        "required_inputs": [],
        "method": "No savings are calculated. Recommended when bill history shows unexplained increases or the "
                  "building uses more energy than most peers, and always for homes and small businesses because these "
                  "are steps the occupant controls: thermostat schedules and set-points, equipment left on after "
                  "hours (e.g. ovens, display lighting, space heaters), and opening/closing routines.",
        "dependencies": [],
        "exclusions": [],
        "uncertainty": "Savings unknown until schedules are inspected.",
        "incentive_measure": "energy_assessment",
        "disruption": "low",
        "order": 10,
    },
    "energy_assessment": {
        "name": "Obtain a professional energy assessment",
        "kind": "assessment",
        "categories": ["home", "small_business", "commercial_office", "multifamily"],
        "required_inputs": [],
        "method": "No savings are calculated. An on-site assessment identifies building-specific measures and is "
                  "the right first step when the cause of high use is unknown.",
        "dependencies": [],
        "exclusions": [],
        "uncertainty": "Outcome depends on findings.",
        "incentive_measure": "energy_assessment",
        "disruption": "low",
        "order": 5,
    },
    "thermostat_setback": {
        "name": "Heating set-back schedule / programmable or smart thermostats",
        "kind": "percentage_assumption",
        "categories": ["home", "small_business", "commercial_office", "multifamily"],
        "required_inputs": ["heating_split (from gas bills)", "schedule.heating_setback_in_place = false"],
        "method": "Heating-attributed gas (bills minus baseload) x set-back savings fraction. The fraction is an "
                  "ASSUMPTION, not building-specific engineering analysis.",
        "params": {"savings_fraction": {"type": "number", "assumption_id": "thermostat_setback_fraction",
                                        "min": 0.0, "max": 0.10, "unit": "fraction of heating gas"}},
        "dependencies": [],
        "exclusions": ["Excluded if a heating set-back is already in place."],
        "uncertainty": "High: depends on current set-points, occupancy and building heat-up behaviour.",
        "incentive_measure": "thermostat_controls",
        "affects": "heating",
        "disruption": "low",
        "order": 20,
    },
    "led_lighting": {
        "name": "LED lighting retrofit",
        "kind": "calculated",
        "categories": ["home", "small_business", "commercial_office", "multifamily"],
        "required_inputs": ["lighting.fixture_count", "lighting.existing_watts_per_fixture",
                            "lighting.annual_operating_hours", "params.proposed_watts_per_fixture"],
        "method": "kWh saved = fixtures x (existing W - proposed W) x annual hours / 1000. Priced at the usage-based "
                  "electricity rate from bills; demand charges are not assumed to fall.",
        "params": {"proposed_watts_per_fixture": {"type": "number", "min": 1, "max": 1000, "unit": "W"}},
        "dependencies": [],
        "exclusions": ["Excluded if existing lighting is already LED."],
        "uncertainty": "Medium: operating hours are usually estimated. Lower lighting heat slightly raises heating "
                       "load (not modelled).",
        "incentive_measure": "led_lighting",
        "affects": "electricity",
        "disruption": "low",
        "order": 30,
    },
    "weatherization": {
        "name": "Weatherization / envelope assessment (air sealing, insulation)",
        "kind": "assessment",
        "categories": ["home", "small_business", "commercial_office", "multifamily"],
        "required_inputs": [],
        "method": "No savings are calculated without an envelope assessment. Recommended before sizing heat pumps "
                  "because a tighter envelope reduces the required heating capacity.",
        "dependencies": [],
        "exclusions": [],
        "uncertainty": "Savings depend on existing insulation and air leakage, which bills cannot reveal.",
        "incentive_measure": "weatherization",
        "disruption": "medium",
        "order": 40,
    },
    "heat_pump_heating": {
        "name": "Air-source heat pump heating (electrification screening)",
        "kind": "calculated",
        "categories": ["home", "small_business", "commercial_office", "multifamily"],
        "required_inputs": ["heating_split (from gas bills)", "existing heating efficiency (equipment AFUE)",
                            "params.seasonal_cop (from contractor / equipment spec)"],
        "method": "Delivered heat = heating gas (therms) x 100 kBtu x existing efficiency x coverage. "
                  "Heat-pump kWh = delivered heat / (seasonal COP x 3.412). Operating cost change uses usage-based "
                  "rates for both fuels; gas fixed charges remain while gas service stays connected.",
        "params": {
            # Seasonal (annual-average) COP from a contractor proposal / spec. Not an instantaneous rating,
            # and not HSPF/SEER (different units).
            "seasonal_cop": {"type": "number", "min": 1.0, "max": 5.0, "unit": "seasonal COP (dimensionless)"},
            "coverage_fraction": {"type": "number", "min": 0.0, "max": 1.0, "unit": "fraction of heating displaced"},
            # Overrides the boiler/furnace record. PERCENT only (80 = 80%).
            "existing_efficiency_pct": {"type": "number", "min": 50.0, "max": 100.0, "unit": "percent (AFUE)"},
            "cop_source": {"type": "str"},
        },
        "dependencies": ["weatherization"],
        "exclusions": ["Not applicable if heating is already a heat pump."],
        "uncertainty": "High: seasonal COP, design temperature and distribution system compatibility require a "
                       "contractor assessment. Screening only.",
        "incentive_measure": "heat_pump_heating",
        "affects": "heating",
        "disruption": "high",
        "order": 50,
    },
    "solar_assessment": {
        "name": "Solar PV site assessment",
        "kind": "assessment",
        "categories": ["home", "small_business", "commercial_office", "multifamily"],
        "required_inputs": [],
        "method": "Assessment only. Benji does not size systems or estimate production in this version.",
        "dependencies": [],
        "exclusions": [],
        "uncertainty": "Roof condition, shading, ownership and interconnection unknown.",
        "incentive_measure": "solar_assessment",
        "disruption": "medium",
        "order": 60,
    },
}

# Assumption register for measure parameters. Values are labelled assumptions.
ASSUMPTIONS: dict[str, dict] = {
    "thermostat_setback_fraction": {
        "description": "Heating energy saved by a nightly set-back",
        "value": 0.05, "low": 0.0, "high": 0.10, "unit": "fraction of heating energy",
        "basis": "U.S. DOE Energy Saver guidance states savings of up to about 10% a year from setting the "
                 "thermostat back 7-10 deg F for 8 hours a day. Benji uses the midpoint of 0-10% because 'up to' "
                 "is a ceiling, not a typical value. Guidance is residential-oriented.",
        "source_title": "U.S. DOE Energy Saver - Programmable Thermostats",
        "source_url": "https://www.energy.gov/energysaver/programmable-thermostats",
        "verified_on": None,
        "verification_status": "unverified",
        "data_label": "assumption",
    },
}

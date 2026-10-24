"""Data models shared by skills, storage and the API.

All models reject NaN/Infinity and enforce supported physical ranges. Efficiency values carry an
explicit unit: combustion efficiencies (AFUE, thermal_efficiency) are entered as PERCENT (e.g. 80),
never as a fraction, so 0.8 is rejected instead of being guessed.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .units import FUEL_UNITS


class DataLabel(str, Enum):
    """Provenance label carried by every value Benji shows."""

    user_provided = "user_provided"
    public_historical = "public_historical"
    assumption = "assumption"
    modelled_estimate = "modelled_estimate"
    synthetic_demo = "synthetic_demo"
    measured_post_action = "measured_post_action"


class Strict(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)


# home = 1-4 unit residential (owner, renter or small landlord); small_business = store, cafe, restaurant, small office
BuildingCategory = Literal["home", "small_business", "commercial_office", "multifamily"]
BusinessType = Literal["retail_store", "grocery", "food_service", "small_office", "other"]
OccupantRole = Literal["owner_occupant", "renter", "landlord", "business_owner_owns_space", "business_tenant",
                       "property_manager"]
Fuel = Literal["electricity", "natural_gas"]
HeatingFuel = Literal["natural_gas", "oil", "propane", "electric_resistance", "district_steam", "heat_pump"]

# Supported ranges per efficiency unit (inclusive). Percent units must be entered as percent.
EFFICIENCY_RANGES = {
    "AFUE": (50.0, 100.0, "percent"),
    "thermal_efficiency": (50.0, 100.0, "percent"),
    "COP": (1.0, 8.0, "dimensionless"),
    "HSPF2": (3.0, 15.0, "Btu/Wh (seasonal)"),
    "SEER2": (8.0, 40.0, "Btu/Wh (seasonal)"),
    "UEF": (0.3, 5.0, "dimensionless"),
}
# fuels for equipment, mapped onto the bill fuels they consume
EQUIPMENT_FUELS = Literal["electricity", "natural_gas", "oil", "propane", "district_steam"]


class Equipment(Strict):
    id: str
    kind: Literal["boiler", "furnace", "heat_pump", "electric_resistance", "rooftop_unit", "chiller",
                  "split_ac", "water_heater", "lighting", "thermostat", "other"]
    fuel: Optional[EQUIPMENT_FUELS] = None
    quantity: int = Field(1, ge=1, le=10000)
    capacity: Optional[float] = Field(None, gt=0, le=1e6)
    capacity_unit: Optional[Literal["kW", "MBH", "Btu/h", "tons"]] = None
    efficiency: Optional[float] = None
    efficiency_unit: Optional[Literal["AFUE", "thermal_efficiency", "COP", "HSPF2", "SEER2", "UEF"]] = None
    install_year: Optional[int] = Field(None, ge=1850, le=2100)
    condition: Optional[Literal["working", "degraded", "failed", "unknown"]] = "unknown"
    electrical_input_kw: Optional[float] = Field(None, gt=0, le=10000)  # nameplate electrical input, if known
    circuit_ref: Optional[str] = None  # panel/circuit identifier from a schedule, if supplied
    evidence_refs: list[str] = Field(default_factory=list)  # document annotation ids
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _check_efficiency(self):
        if (self.capacity is None) != (self.capacity_unit is None):
            raise ValueError("capacity and capacity_unit must be given together")
        if self.efficiency is None:
            return self
        if self.efficiency_unit is None:
            raise ValueError("efficiency_unit is required when efficiency is given")
        lo, hi, unit = EFFICIENCY_RANGES[self.efficiency_unit]
        if not (lo <= self.efficiency <= hi):
            hint = " Enter percent, e.g. 80 for 80%." if unit == "percent" else ""
            raise ValueError(f"{self.efficiency_unit} must be between {lo:g} and {hi:g} ({unit}).{hint}")
        return self


class Lighting(Strict):
    fixture_count: Optional[int] = Field(None, ge=0, le=1_000_000)
    existing_watts_per_fixture: Optional[float] = Field(None, gt=0, le=2000)
    technology: Optional[Literal["fluorescent_t8", "fluorescent_t12", "halogen", "incandescent", "led", "mixed", "unknown"]] = "unknown"
    annual_operating_hours: Optional[float] = Field(None, ge=0, le=8760)


class Schedule(Strict):
    weekday_occupied_hours: Optional[str] = None  # e.g. "07:00-19:00"
    weekend_occupied: Optional[bool] = None
    heating_setback_in_place: Optional[bool] = None
    notes: Optional[str] = None


class OperatingChange(Strict):
    date: date
    description: str


class ElectricalService(Strict):
    """Electrification-readiness evidence. Benji records facts; it never certifies capacity or safety."""

    service_amps: Optional[float] = Field(None, gt=0, le=10000)
    service_voltage: Optional[float] = Field(None, gt=0, le=35000)
    phases: Optional[Literal[1, 3]] = None
    main_panel_id: Optional[str] = None
    main_breaker_amps: Optional[float] = Field(None, gt=0, le=10000)
    spare_breaker_spaces: Optional[int] = Field(None, ge=0, le=500)
    source: Optional[str] = None  # e.g. "panel label photo", "electrician letter 2026-05-01"
    evidence_refs: list[str] = Field(default_factory=list)


class Building(Strict):
    id: Optional[str] = None
    name: str = Field(min_length=1)
    category: BuildingCategory
    business_type: Optional[BusinessType] = None  # small_business only
    occupant_role: Optional[OccupantRole] = None  # who is using Benji; drives who-pays / who-authorizes
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: str = "MA"
    zip: Optional[str] = None
    gross_floor_area_sqft: Optional[float] = Field(None, gt=0, le=1e8)
    year_built: Optional[int] = Field(None, ge=1600, le=2100)
    dwelling_units: Optional[int] = Field(None, ge=1, le=100000)
    heating_fuel: Optional[HeatingFuel] = None
    energy_sources: list[str] = Field(default_factory=list)
    electric_utility: Optional[str] = None
    gas_utility: Optional[str] = None
    schedule: Schedule = Field(default_factory=Schedule)
    equipment: list[Equipment] = Field(default_factory=list)
    lighting: Lighting = Field(default_factory=Lighting)
    electrical_service: ElectricalService = Field(default_factory=ElectricalService)
    budget_usd: Optional[float] = Field(None, ge=0, le=1e10)
    upfront_cash_available_usd: Optional[float] = Field(None, ge=0, le=1e10)
    bill_payer: Optional[str] = None  # e.g. "owner", "tenant", "split"
    decision_maker: Optional[str] = None
    owner_occupied_primary_residence: Optional[bool] = None
    income_eligible: Optional[bool] = None
    # answers to program questions, e.g. {"uses_participating_contractor": true}
    eligibility_answers: dict[str, Any] = Field(default_factory=dict)
    # False when bills miss part of the building's energy (e.g. tenant-metered electricity); None = not confirmed
    bills_cover_whole_building: Optional[bool] = None
    operating_changes: list[OperatingChange] = Field(default_factory=list)
    data_label: DataLabel = DataLabel.user_provided


class LineItem(Strict):
    description: str
    # "credit" holds legitimate bill credits (negative amounts); it is never treated as consumption.
    category: Literal["fixed", "energy", "delivery_variable", "demand", "tax_other", "credit"]
    amount_usd: float = Field(ge=-1e8, le=1e8)

    @model_validator(mode="after")
    def _credit_sign(self):
        if self.category == "credit" and self.amount_usd > 0:
            raise ValueError("credit line items must be zero or negative")
        if self.category != "credit" and self.amount_usd < 0:
            raise ValueError("negative amounts must use the 'credit' category")
        return self


class BillSource(Strict):
    kind: Literal["csv", "pdf_text", "manual", "demo"]
    filename: Optional[str] = None
    sha256: Optional[str] = None
    stored_path: Optional[str] = None
    raw_excerpt: Optional[str] = None


class Bill(Strict):
    id: Optional[str] = None
    building_id: Optional[str] = None
    fuel: Fuel
    utility: Optional[str] = None
    account: Optional[str] = None
    period_start: date
    period_end: date
    # Negative consumption (net export) is not supported; use a 'credit' line item for bill credits.
    quantity: float = Field(ge=0, le=1e10)
    unit: str
    therms_per_ccf: Optional[float] = Field(None, gt=0.8, le=1.3)
    demand_kw: Optional[float] = Field(None, ge=0, le=1e6)
    line_items: list[LineItem] = Field(default_factory=list)
    line_items_complete: bool = True  # partial components must not substitute for a missing bill total
    total_usd: Optional[float] = Field(None, ge=-1e8, le=1e8)
    source: BillSource = Field(default_factory=lambda: BillSource(kind="manual"))
    extraction_confidence: Optional[Literal["high", "medium", "low"]] = None
    uncertain_fields: list[str] = Field(default_factory=list)
    status: Literal["pending_confirmation", "confirmed"] = "pending_confirmation"
    data_label: DataLabel = DataLabel.user_provided

    @model_validator(mode="after")
    def _check(self):
        if self.period_end <= self.period_start:
            raise ValueError("period_end must be after period_start")
        if self.unit not in FUEL_UNITS[self.fuel]:
            raise ValueError(f"unit '{self.unit}' is not valid for {self.fuel} "
                             f"(allowed: {', '.join(sorted(FUEL_UNITS[self.fuel]))})")
        return self

    @property
    def days(self) -> int:
        return max((self.period_end - self.period_start).days, 0)


class IncentiveDecision(Strict):
    """User-reported program status. Benji does not verify approvals itself.

    applied   = submitted, pending: never counted as confirmed money.
    approved  = user reports written approval; counted as confirmed only with reported_by,
                reported_on and reference (approval number / letter).
    disbursed = user reports payment received (same evidence fields).
    """

    status: Literal["not_reviewed", "applied", "approved", "disbursed", "rejected",
                    "confirmed_by_program"] = "not_reviewed"  # confirmed_by_program: legacy alias of approved
    amount_usd: Optional[float] = Field(None, ge=0, le=1e9)  # amount stated by program for this project
    reported_by: Optional[str] = None
    reported_on: Optional[date] = None
    reference: Optional[str] = None
    note: Optional[str] = None


class MeasureInputs(Strict):
    """User-editable inputs for one candidate measure (the 'delight' controls)."""

    measure_id: str
    quoted_cost_usd: Optional[float] = Field(None, ge=0, le=1e10)
    cost_source: Optional[str] = None  # "contractor_quote", "user_estimate"
    params: dict[str, Any] = Field(default_factory=dict)
    incentive_status: dict[str, IncentiveDecision] = Field(default_factory=dict)


class Task(Strict):
    id: str
    title: str
    recommendation_id: Optional[str] = None
    owner: Optional[str] = None
    prerequisites: list[str] = Field(default_factory=list)
    due_date: Optional[date] = None
    status: Literal["not_started", "in_progress", "blocked", "done", "skipped"] = "not_started"
    next_step: Optional[str] = None

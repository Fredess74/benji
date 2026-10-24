"""Single-zone room heating / cooling scenario (deterministic, transparent).

Heat balance (lumped, one zone, constant inputs):

    C_eff * dT/dt = s * Q_hvac + G - H * (T - T_ref)

C_eff  effective thermal capacity [kWh/K]   (air + furnishings + participating structure)
H      heat-loss coefficient       [kW/K]   (transmission through boundaries + ventilation)
T_ref  H-weighted boundary temperature [C]  (outdoor for exterior surfaces, adjacent temp for unconditioned)
Q_hvac THERMAL output at modelled conditions [kW]; s = +1 heating, -1 cooling
G      internal + solar gains [kW] (user-entered constants, labelled)

Exact solution with constant inputs:  T(t) = T_eq + (T0 - T_eq) * exp(-t / tau),
tau = C/H, T_eq = T_ref + (s*Q + G)/H. For H = 0 the response is linear: T0 + (s*Q + G)/C * t.

Limitations (reported with every result): single well-mixed zone; constant outdoor temperature and
equipment output; no weather year, no part-load curves, no defrost; cooling is SENSIBLE ONLY (no latent /
dehumidification load); not an equipment sizing calculation (e.g. ACCA Manual J/N); not live control.
Missing heat-loss or thermal-mass values are never filled with "typical" defaults.
"""

from __future__ import annotations

import math
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

M2_PER_SQFT = 0.09290304
M_PER_FT = 0.3048
AIR_RHO_CP_KWH_PER_M3K = 1.2 * 1.005 / 3600  # kg/m3 * kJ/kgK -> kWh/(m3 K), air at ~20 C
U_SI_PER_IP = 5.678263  # W/m2K per Btu/(h ft2 F)
LIMITATIONS = [
    "Single well-mixed zone with constant outdoor temperature, gains and equipment output.",
    "Cooling is sensible-only: humidity / latent load and dehumidification are not modelled.",
    "Not an equipment sizing calculation (e.g. ACCA Manual J/N) and not a code-compliance check.",
    "One warm-up / cool-down event; annual energy needs a schedule and weather model (not implemented).",
    "Advisory only: Benji does not control equipment. Keep ventilation and freeze protection as designed.",
]


class Strict(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")


class Quantity(Strict):
    value: float = Field(gt=0, le=1e7)
    unit: str


class Surface(Strict):
    name: str
    area: float = Field(gt=0, le=1e6)
    area_unit: Literal["m2", "sqft"] = "m2"
    u_value_w_m2k: Optional[float] = Field(None, gt=0, le=20)
    r_value_ip: Optional[float] = Field(None, gt=0, le=200)  # ft2*F*h/Btu
    boundary: Literal["exterior", "adjacent_unconditioned", "adjacent_conditioned"]
    adjacent_temp: Optional[float] = Field(None, ge=-60, le=60)  # in the scenario temperature unit
    source: Optional[str] = None

    @model_validator(mode="after")
    def _u(self):
        if (self.u_value_w_m2k is None) == (self.r_value_ip is None) and self.boundary != "adjacent_conditioned":
            raise ValueError("give exactly one of u_value_w_m2k or r_value_ip")
        if self.boundary == "adjacent_unconditioned" and self.adjacent_temp is None:
            raise ValueError("adjacent_temp is required for an adjacent_unconditioned boundary")
        return self

    def area_m2(self) -> float:
        return self.area * (M2_PER_SQFT if self.area_unit == "sqft" else 1.0)

    def u(self) -> float:
        return self.u_value_w_m2k if self.u_value_w_m2k is not None else U_SI_PER_IP / self.r_value_ip


class HVAC(Strict):
    mode: Literal["heating", "cooling"]
    thermal_output_kw: Optional[float] = Field(None, ge=0, le=10000)  # thermal, at modelled conditions
    output_source: Optional[str] = None  # e.g. "manufacturer table at 5 F", "contractor proposal"
    # Instantaneous efficiency at the modelled condition. COP is dimensionless (heat out / energy in).
    # Seasonal ratings (HSPF2, SEER2) are NOT accepted here: they are not interchangeable with COP.
    efficiency_kind: Optional[Literal["COP", "combustion_efficiency_pct"]] = None
    efficiency_value: Optional[float] = Field(None, gt=0, le=100)
    carrier: Optional[Literal["electricity", "natural_gas"]] = None
    backup_thermal_kw: float = Field(0.0, ge=0, le=10000)  # electric resistance backup (COP 1), heating only
    efficiency_source: Optional[str] = None

    @model_validator(mode="after")
    def _eff(self):
        k, v = self.efficiency_kind, self.efficiency_value
        if (k is None) != (v is None):
            raise ValueError("efficiency_kind and efficiency_value must be given together")
        if k == "COP" and not (0.5 <= v <= 8):
            raise ValueError("COP must be between 0.5 and 8")
        if k == "combustion_efficiency_pct" and not (50 <= v <= 100):
            raise ValueError("combustion efficiency must be entered in percent, 50-100 (e.g. 82, not 0.82)")
        if k == "combustion_efficiency_pct" and self.carrier == "electricity":
            raise ValueError("combustion efficiency requires a fuel carrier")
        if self.mode == "cooling" and self.backup_thermal_kw:
            raise ValueError("backup_thermal_kw applies to heating only")
        return self


class ScenarioInputs(Strict):
    room_name: str = Field(min_length=1)
    floor_area: Optional[float] = Field(None, gt=0, le=1e6)
    floor_area_unit: Literal["m2", "sqft"] = "m2"
    ceiling_height: Optional[float] = Field(None, gt=0, le=100)
    ceiling_height_unit: Literal["m", "ft"] = "m"
    temperature_unit: Literal["C", "F"] = "C"
    initial_temp: float = Field(ge=-60, le=60 * 2)
    target_temp: float = Field(ge=-60, le=60 * 2)
    outdoor_temp: float = Field(ge=-60, le=60 * 2)
    # Heat loss: either a known H, or surfaces (+ ventilation). Never a default.
    heat_loss_coefficient_w_per_k: Optional[float] = Field(None, ge=0, le=1e7)
    heat_loss_source: Optional[str] = None
    surfaces: list[Surface] = Field(default_factory=list)
    air_changes_per_hour: Optional[float] = Field(None, ge=0, le=50)
    ventilation_source: Optional[str] = None
    # Thermal mass: a known effective capacity, or an explicit air-only LOWER BOUND.
    effective_capacity_kwh_per_k: Optional[float] = Field(None, gt=0, le=1e6)
    capacity_source: Optional[str] = None
    capacity_basis: Literal["user_value", "air_only_lower_bound"] = "user_value"
    internal_gains_w: float = Field(0.0, ge=0, le=1e7)
    solar_gains_w: float = Field(0.0, ge=0, le=1e7)
    gains_source: Optional[str] = None
    hvac: HVAC
    energy_price_usd_per_unit: Optional[float] = Field(None, gt=0, le=50)  # USD per kWh or per therm
    energy_price_source: Optional[str] = None
    occupied_by_hours: Optional[float] = Field(None, gt=0, le=168)  # comfort deadline from now
    horizon_hours: float = Field(24.0, gt=0, le=168)
    uncertainty_pct: dict[Literal["H", "C", "Q"], float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _temps(self):
        for name in ("initial_temp", "target_temp", "outdoor_temp"):
            c = self.to_c(getattr(self, name))
            if not (-50 <= c <= 60):
                raise ValueError(f"{name} must be between -50 and 60 C (-58 to 140 F)")
        return self

    def to_c(self, t: float) -> float:
        return (t - 32) * 5 / 9 if self.temperature_unit == "F" else t

    def volume_m3(self) -> Optional[float]:
        if self.floor_area is None or self.ceiling_height is None:
            return None
        a = self.floor_area * (M2_PER_SQFT if self.floor_area_unit == "sqft" else 1)
        h = self.ceiling_height * (M_PER_FT if self.ceiling_height_unit == "ft" else 1)
        return a * h


def resolve(inp: ScenarioInputs) -> tuple[dict, list[dict], list[dict]]:
    """Turn user inputs into model parameters. Returns (params, missing, assumptions)."""
    missing, assumptions = [], []
    t_out = inp.to_c(inp.outdoor_temp)
    vol = inp.volume_m3()
    # --- heat loss
    H_w, H_ref = None, None
    if inp.heat_loss_coefficient_w_per_k is not None:
        H_w, H_ref = inp.heat_loss_coefficient_w_per_k, t_out
        assumptions.append({"id": "H", "text": f"Heat-loss coefficient {H_w:g} W/K "
                            f"({inp.heat_loss_source or 'source not stated'}).",
                            "data_label": "user_provided" if inp.heat_loss_source else "assumption"})
    elif inp.surfaces:
        terms = []
        for s in inp.surfaces:
            if s.boundary == "adjacent_conditioned":
                continue  # no heat flow to a space held at the same temperature (assumption, stated)
            ua = s.u() * s.area_m2()
            tb = t_out if s.boundary == "exterior" else inp.to_c(s.adjacent_temp)
            terms.append((ua, tb))
        if inp.air_changes_per_hour is None:
            missing.append({"field": "air_changes_per_hour", "message": "Ventilation/infiltration rate (air changes "
                            "per hour) is needed with surface-based heat loss; enter 0 only if verified airtight."})
        elif vol is None:
            missing.append({"field": "ceiling_height", "message": "Floor area and ceiling height are needed to turn "
                            "air changes per hour into a ventilation heat loss."})
        else:
            terms.append((AIR_RHO_CP_KWH_PER_M3K * 1000 * inp.air_changes_per_hour * vol, t_out))
        if not missing:
            H_w = sum(ua for ua, _ in terms)
            H_ref = (sum(ua * tb for ua, tb in terms) / H_w) if H_w > 0 else t_out
            assumptions.append({"id": "H", "text": f"Heat-loss coefficient {H_w:,.1f} W/K from "
                                f"{len(inp.surfaces)} surface(s) (U x A) plus ventilation "
                                f"{inp.air_changes_per_hour:g} ACH x {vol:,.1f} m3 x 0.335 W/(m3 K h).",
                                "data_label": "user_provided"})
            if any(s.boundary == "adjacent_conditioned" for s in inp.surfaces):
                assumptions.append({"id": "adjacent", "data_label": "assumption",
                                    "text": "Surfaces to conditioned spaces are assumed to carry no heat."})
    else:
        missing.append({"field": "heat_loss_coefficient_w_per_k", "message": "Add a heat-loss coefficient (W/K) from "
                        "an energy assessment, or the room's exterior surfaces with U- or R-values and an air-change "
                        "rate. Floor area alone cannot predict heat loss."})
    # --- thermal capacity
    C = None
    if inp.capacity_basis == "user_value":
        if inp.effective_capacity_kwh_per_k is None:
            missing.append({"field": "effective_capacity_kwh_per_k", "message": "Add the room's effective thermal "
                            "capacity (kWh/K, air + furnishings + participating structure), or choose "
                            "capacity_basis 'air_only_lower_bound' for an explicitly optimistic warm-up time."})
        else:
            C = inp.effective_capacity_kwh_per_k
            assumptions.append({"id": "C", "text": f"Effective thermal capacity {C:g} kWh/K "
                                f"({inp.capacity_source or 'source not stated'}).",
                                "data_label": "user_provided" if inp.capacity_source else "assumption"})
    else:
        if vol is None:
            missing.append({"field": "ceiling_height", "message": "Floor area and ceiling height are needed for the "
                            "air-only capacity bound."})
        else:
            C = AIR_RHO_CP_KWH_PER_M3K * vol
            assumptions.append({"id": "C", "data_label": "assumption",
                                "text": f"AIR-ONLY LOWER BOUND: capacity {C:.3f} kWh/K from {vol:,.1f} m3 of air. Real "
                                        "rooms store far more heat in furnishings and structure, so the real warm-up "
                                        "will be SLOWER than shown."})
    # --- equipment
    hv = inp.hvac
    if hv.thermal_output_kw is None:
        missing.append({"field": "hvac.thermal_output_kw", "message": f"Add the {hv.mode} system's THERMAL output (kW) "
                        "at these conditions (manufacturer table or contractor proposal), not its electrical input."})
    if hv.efficiency_kind is None:
        missing.append({"field": "hvac.efficiency_value", "message": "Add COP at these conditions (electric) or "
                        "combustion efficiency in percent (fuel) to estimate energy use; time-to-target can still be "
                        "calculated."})
    gains_kw = (inp.internal_gains_w + inp.solar_gains_w) / 1000
    if gains_kw:
        assumptions.append({"id": "gains", "data_label": "user_provided" if inp.gains_source else "assumption",
                            "text": f"Constant gains {gains_kw * 1000:,.0f} W ({inp.gains_source or 'source not stated'})."})
    params = {"C": C, "H": None if H_w is None else H_w / 1000, "T_ref": H_ref if H_ref is not None else t_out,
              "T0": inp.to_c(inp.initial_temp), "Tt": inp.to_c(inp.target_temp), "G": gains_kw,
              "Q": None if hv.thermal_output_kw is None else hv.thermal_output_kw + hv.backup_thermal_kw,
              "Q_primary": hv.thermal_output_kw, "Q_backup": hv.backup_thermal_kw,
              "s": 1 if hv.mode == "heating" else -1, "volume_m3": vol}
    return params, missing, assumptions


def time_to_target(C: float, H: float, T_ref: float, T0: float, Tt: float, Q: float, G: float, s: int):
    """Exact time [h] to move from T0 to Tt, or (None, reason)."""
    if math.isclose(T0, Tt, abs_tol=1e-9):
        return 0.0, "already_at_target"
    direction = 1 if Tt > T0 else -1
    if direction != s and not math.isclose(Q, 0):
        return None, f"target requires {'heating' if direction > 0 else 'cooling'}, but the system is in {'heating' if s > 0 else 'cooling'} mode"
    net = s * Q + G
    if H == 0:
        rate = net / C  # K/h
        if rate * direction <= 0:
            return None, "no net heat flow toward the target"
        return (Tt - T0) / rate, "reachable"
    T_eq = T_ref + net / H
    if math.isclose(T_eq, Tt, abs_tol=1e-9):
        return None, f"equilibrium {T_eq:.2f} C equals the target: approached only asymptotically, never reached"
    if (T_eq - Tt) * direction < 0:
        return None, (f"equilibrium temperature {T_eq:.2f} C is short of the target: the system cannot overcome "
                      f"heat {'loss' if direction > 0 else 'gain'} at the target")
    ratio = (Tt - T_eq) / (T0 - T_eq)
    return -(C / H) * math.log(ratio), "reachable"


def temperature_at(t: float, C, H, T_ref, T0, Q, G, s) -> float:
    net = s * Q + G
    if H == 0:
        return T0 + net / C * t
    T_eq = T_ref + net / H
    return T_eq + (T0 - T_eq) * math.exp(-t * H / C)


def simulate_numeric(C, H, T_ref, T0, Tt, Q, G, s, dt_h: float, horizon_h: float):
    """RK4 integration used as an independent cross-check of the analytical solution."""
    f = lambda T: (s * Q + G - H * (T - T_ref)) / C
    T, t = T0, 0.0
    direction = 1 if Tt > T0 else -1
    while t < horizon_h:
        k1 = f(T); k2 = f(T + dt_h * k1 / 2); k3 = f(T + dt_h * k2 / 2); k4 = f(T + dt_h * k3)
        Tn = T + dt_h * (k1 + 2 * k2 + 2 * k3 + k4) / 6
        if (Tn - Tt) * direction >= 0:
            return t + dt_h * (Tt - T) / (Tn - T)  # linear interpolation inside the step
        T, t = Tn, t + dt_h
    return None


def simulate(inp: ScenarioInputs) -> dict:
    p, missing, assumptions = resolve(inp)
    hv = inp.hvac
    out = {"room_name": inp.room_name, "mode": hv.mode, "status": None, "missing": missing,
           "assumptions": assumptions, "limitations": LIMITATIONS, "model": "single_zone_rc_v1",
           "units": {"temperature": "C", "energy": "kWh", "power": "kW", "time": "h"},
           "cooling_model": "sensible_only" if hv.mode == "cooling" else None,
           "data_label": "modelled_estimate"}
    if p["H"] is None or p["C"] is None or p["Q"] is None:
        out["status"] = "needs_data"
        out["message"] = "Add " + "; ".join(m["message"].split(".")[0].lower() for m in missing) + "."
        return out
    C, H, Tr, T0, Tt, Q, G, s = p["C"], p["H"], p["T_ref"], p["T0"], p["Tt"], p["Q"], p["G"], p["s"]
    t, reason = time_to_target(C, H, Tr, T0, Tt, Q, G, s)
    load_at_target = H * (Tt - Tr) - G if s > 0 else H * (Tr - Tt) + G  # kW the system must supply to HOLD target
    out.update({
        "heat_loss_coefficient_kw_per_k": round(H, 5), "effective_capacity_kwh_per_k": round(C, 4),
        "time_constant_h": round(C / H, 3) if H else None,
        "boundary_reference_temp_c": round(Tr, 2),
        "equilibrium_temp_c": round(Tr + (s * Q + G) / H, 2) if H else None,
        "load_to_hold_target_kw": round(load_at_target, 3),
        "capacity_headroom_kw": round(Q - load_at_target, 3),
        "capacity_shortfall": Q < load_at_target - 1e-9,
    })
    # temperature series (hourly-ish, plus the arrival point)
    horizon = inp.horizon_hours
    n = 48
    series = []
    for i in range(n + 1):
        ti = horizon * i / n
        if t is not None and ti >= t:
            Ti = Tt  # thermostat holds the target once reached
        else:
            Ti = temperature_at(ti, C, H, Tr, T0, Q, G, s)
        series.append({"t_h": round(ti, 3), "temp_c": round(Ti, 3)})
    out["series"] = series
    if t is None:
        out.update({"status": "target_not_reachable", "time_to_target_h": None, "reason": reason,
                    "message": f"Target not reachable: {reason}. Temperature after {horizon:g} h: "
                               f"{temperature_at(horizon, C, H, Tr, T0, Q, G, s):.1f} C."})
        return out
    if t > horizon:
        out.update({"status": "target_beyond_horizon", "time_to_target_h": round(t, 3),
                    "message": f"Reaches target after {t:.1f} h, beyond the {horizon:g} h horizon."})
    else:
        out.update({"status": "reachable" if reason == "reachable" else reason, "time_to_target_h": round(t, 3),
                    "message": f"Reaches {Tt:.1f} C in about {t:.2f} h (modelled estimate)."})
    delivered = Q * t
    out["delivered_thermal_kwh"] = round(delivered, 3)
    primary = (p["Q_primary"] or 0) * t
    backup = p["Q_backup"] * t
    energy = None
    if hv.efficiency_kind == "COP":
        energy = {"carrier": hv.carrier or "electricity", "unit": "kWh", "quantity": round(primary / hv.efficiency_value + backup, 3)}
    elif hv.efficiency_kind == "combustion_efficiency_pct":
        therms = primary / (hv.efficiency_value / 100) * 3.412 / 100
        energy = {"carrier": hv.carrier or "natural_gas", "unit": "therms", "quantity": round(therms, 4)}
        if backup:
            energy["backup_electricity_kwh"] = round(backup, 3)
    out["consumed_energy"] = energy
    if energy and inp.energy_price_usd_per_unit is not None:
        cost = energy["quantity"] * inp.energy_price_usd_per_unit
        out["variable_energy_cost_usd"] = round(cost, 2)
        out["cost_note"] = ("Marginal usage-based energy cost for this one event at "
                            f"${inp.energy_price_usd_per_unit:g}/{energy['unit']} "
                            f"({inp.energy_price_source or 'source not stated'}); not a bill forecast; "
                            "fixed and demand charges are excluded.")
        if energy.get("backup_electricity_kwh"):
            out["cost_note"] += " Backup electricity is not priced in a gas-carrier scenario."
    else:
        out["variable_energy_cost_usd"] = None
    if inp.occupied_by_hours is not None:
        lead = inp.occupied_by_hours - t
        out["preheat_advice"] = (f"Start about {t:.1f} h before occupancy" + (
            "; the target can be met by the occupied time." if lead >= 0 else
            f"; at the stated occupied time ({inp.occupied_by_hours:g} h) the room would be "
            f"{temperature_at(inp.occupied_by_hours, C, H, Tr, T0, Q, G, s):.1f} C.")) + \
            " Advisory only; Benji does not control equipment."
    # uncertainty: corner cases for user-stated ranges only
    rng = {}
    for key, pct in inp.uncertainty_pct.items():
        if not (0 < pct < 100):
            continue
        vals = []
        for sign in (-1, 1):
            f = 1 + sign * pct / 100
            args = dict(C=C, H=H, Q=Q)
            args[key] *= f
            tt, _ = time_to_target(args["C"], args["H"], Tr, T0, Tt, args["Q"], G, s)
            vals.append(tt)
        rng[key] = {"pct": pct, "time_to_target_h": [None if v is None else round(v, 2) for v in vals]}
    out["sensitivity"] = rng
    out["main_uncertainty_drivers"] = [a["text"] for a in assumptions if a["data_label"] == "assumption"] or \
        ["Heat-loss coefficient and effective thermal capacity dominate the result."]
    return out


def apply_overrides(base: dict, overrides: dict, prices: dict | None = None) -> ScenarioInputs:
    """Merge an alternative's overrides. If the energy carrier changes and no price is given for the new carrier,
    the inherited price is dropped (or replaced from `prices` by carrier) - a gas price is never applied to kWh."""
    merged = {**base}
    for k, v in (overrides or {}).items():
        if k == "hvac" and isinstance(v, dict):
            merged["hvac"] = {**base.get("hvac", {}), **v}
        else:
            merged[k] = v
    old_c, new_c = (base.get("hvac") or {}).get("carrier"), (merged.get("hvac") or {}).get("carrier")
    if new_c != old_c and "energy_price_usd_per_unit" not in (overrides or {}):
        p = (prices or {}).get(new_c)
        merged["energy_price_usd_per_unit"] = p["rate"] if p else None
        merged["energy_price_source"] = p["source"] if p else None
    return ScenarioInputs(**merged)


def compare(base: dict, alternatives: list[dict], prices: dict | None = None) -> dict:
    """Run the current setup and named alternatives (envelope or HVAC changes) side by side.

    prices: optional {carrier: {"rate": float, "source": str}} from the validated tariff layer.
    """
    rows = [{"name": "current", **simulate(ScenarioInputs(**base))}]
    for alt in alternatives:
        try:
            rows.append({"name": alt["name"], "overrides": alt.get("overrides", {}),
                         **simulate(apply_overrides(base, alt.get("overrides", {}), prices))})
        except ValueError as exc:
            rows.append({"name": alt.get("name", "?"), "status": "invalid_input", "message": str(exc)})
    return {"scenarios": rows}

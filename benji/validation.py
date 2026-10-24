"""Boundary validation for free-form parameters (measure params, analysis settings).

Bad values are rejected with field-level messages. They are never clamped into a plausible answer.
"""

from __future__ import annotations

import math
from typing import Any


class InputError(ValueError):
    def __init__(self, errors: list[dict]):
        super().__init__("; ".join(f"{e['field']}: {e['message']}" for e in errors))
        self.errors = errors


def _number(field: str, v: Any, lo: float | None, hi: float | None, errors: list, integer=False):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        errors.append({"field": field, "message": f"must be a number, got {type(v).__name__}"})
        return None
    v = float(v)
    if not math.isfinite(v):
        errors.append({"field": field, "message": "must be a finite number"})
        return None
    if integer and v != int(v):
        errors.append({"field": field, "message": "must be a whole number"})
        return None
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        errors.append({"field": field, "message": f"must be between {lo:g} and {hi:g}, got {v:g}"})
        return None
    return int(v) if integer else v


def validate_spec(values: dict | None, spec: dict[str, dict], prefix: str) -> tuple[dict, list[dict]]:
    """spec: name -> {"type": "number"|"int"|"str", "min", "max", "unit", "required"}"""
    values = values or {}
    errors: list[dict] = []
    clean: dict = {}
    if not isinstance(values, dict):
        return {}, [{"field": prefix.rstrip("."), "message": "must be an object"}]
    for k in values:
        if k not in spec:
            errors.append({"field": f"{prefix}{k}", "message": f"unknown parameter (supported: {', '.join(sorted(spec)) or 'none'})"})
    for k, s in spec.items():
        if k not in values or values[k] is None:
            continue
        v = values[k]
        if s["type"] == "str":
            if not isinstance(v, str):
                errors.append({"field": f"{prefix}{k}", "message": "must be text"})
            else:
                clean[k] = v
            continue
        n = _number(f"{prefix}{k}", v, s.get("min"), s.get("max"), errors, integer=s["type"] == "int")
        if n is not None:
            clean[k] = n
    return clean, errors


def validate_measure_params(measure_id: str, params: dict | None) -> tuple[dict, list[dict]]:
    from .catalog.measures import MEASURES

    if measure_id not in MEASURES:
        return {}, [{"field": "measure_id", "message": "unknown measure"}]
    return validate_spec(params, MEASURES[measure_id].get("params", {}), "params.")


TARIFF_SPEC = {
    "electricity": {"usage_rate": {"type": "number", "min": 0.001, "max": 2.0, "unit": "USD/kWh"}},
    "natural_gas": {"usage_rate": {"type": "number", "min": 0.01, "max": 20.0, "unit": "USD/therm"}},
}
SETTINGS_SPEC = {
    "anomaly_threshold": {"type": "number", "min": 0.05, "max": 5.0},
    "custom_scenario": {"type": "list"},
    "peer_filters": {"type": "dict"},
    "tariff_overrides": {"type": "dict"},
}
PEER_SPEC = {"min_sample": {"type": "int", "min": 5, "max": 100000},
             "exclude_district_steam": {"type": "bool"}, "gfa_band": {"type": "list"}}


def validate_settings(settings: dict | None) -> dict:
    """Validate analysis settings; raises InputError with field-level messages."""
    settings = dict(settings or {})
    errors: list[dict] = []
    for k in settings:
        if k not in SETTINGS_SPEC:
            errors.append({"field": f"settings.{k}", "message": f"unknown setting (supported: {', '.join(SETTINGS_SPEC)})"})
    if "anomaly_threshold" in settings:
        _number("settings.anomaly_threshold", settings["anomaly_threshold"], 0.05, 5.0, errors)
    for fuel, ov in (settings.get("tariff_overrides") or {}).items():
        if fuel not in TARIFF_SPEC:
            errors.append({"field": f"settings.tariff_overrides.{fuel}", "message": "unsupported fuel"})
            continue
        _, e = validate_spec(ov, TARIFF_SPEC[fuel], f"settings.tariff_overrides.{fuel}.")
        errors += e
    pf = settings.get("peer_filters") or {}
    if not isinstance(pf, dict):
        errors.append({"field": "settings.peer_filters", "message": "must be an object"})
        pf = {}
    for k, v in pf.items():
        if k not in PEER_SPEC:
            errors.append({"field": f"settings.peer_filters.{k}", "message": "unknown filter"})
        elif k == "min_sample":
            _number("settings.peer_filters.min_sample", v, 5, 100000, errors, integer=True)
        elif k == "exclude_district_steam" and not isinstance(v, bool):
            errors.append({"field": "settings.peer_filters.exclude_district_steam", "message": "must be true/false"})
        elif k == "gfa_band":
            ok = isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) and math.isfinite(x) for x in v) \
                and 0 < v[0] < 1 < v[1] <= 20
            if not ok:
                errors.append({"field": "settings.peer_filters.gfa_band",
                               "message": "must be [low, high] multipliers with 0 < low < 1 < high <= 20"})
    cs = settings.get("custom_scenario")
    if cs is not None and not (isinstance(cs, list) and all(isinstance(x, str) for x in cs)):
        errors.append({"field": "settings.custom_scenario", "message": "must be a list of measure ids"})
    if errors:
        raise InputError(errors)
    return settings

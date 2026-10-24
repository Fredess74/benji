"""Deterministic unit conversions. Everything is converted to kBtu (site energy)
only when an explicit conversion exists; fuels are otherwise kept separate."""

from __future__ import annotations

# Standard site-energy conversions (ENERGY STAR Portfolio Manager / EIA use the same values).
KBTU_PER_KWH = 3.412
KBTU_PER_THERM = 100.0
KBTU_PER_MMBTU = 1000.0
# 1 ccf of natural gas ~ 1.037 therms (heat content varies by utility; utilities print the
# multiplier on the bill). Used only when the bill does not give therms.
THERMS_PER_CCF_DEFAULT = 1.037

FUEL_UNITS = {
    "electricity": {"kWh", "MWh", "kBtu"},
    "natural_gas": {"therms", "ccf", "kBtu", "MMBtu"},
}
CANONICAL_UNIT = {"electricity": "kWh", "natural_gas": "therms"}


class UnitError(ValueError):
    pass


def to_canonical(fuel: str, quantity: float, unit: str, therms_per_ccf: float | None = None) -> float:
    """Convert a quantity to the fuel's canonical unit (kWh or therms)."""
    if fuel not in FUEL_UNITS:
        raise UnitError(f"Unsupported fuel '{fuel}'")
    if unit not in FUEL_UNITS[fuel]:
        raise UnitError(f"Unit '{unit}' is not valid for {fuel}")
    if fuel == "electricity":
        return {"kWh": quantity, "MWh": quantity * 1000.0, "kBtu": quantity / KBTU_PER_KWH}[unit]
    if unit == "therms":
        return quantity
    if unit == "ccf":
        return quantity * (therms_per_ccf or THERMS_PER_CCF_DEFAULT)
    if unit == "kBtu":
        return quantity / KBTU_PER_THERM
    return quantity * KBTU_PER_MMBTU / KBTU_PER_THERM  # MMBtu


def to_kbtu(fuel: str, canonical_quantity: float) -> float:
    if fuel == "electricity":
        return canonical_quantity * KBTU_PER_KWH
    if fuel == "natural_gas":
        return canonical_quantity * KBTU_PER_THERM
    raise UnitError(f"No kBtu conversion for {fuel}")

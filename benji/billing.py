"""Bill arithmetic shared by several skills (no I/O, fully deterministic)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

from .units import CANONICAL_UNIT, UnitError, to_canonical

VARIABLE_CATEGORIES = ("energy", "delivery_variable")


def as_date(v) -> date:
    return v if isinstance(v, date) else date.fromisoformat(str(v)[:10])


def bill_days(b: dict) -> int:
    return max((as_date(b["period_end"]) - as_date(b["period_start"])).days, 0)


def canonical_quantity(b: dict) -> float:
    return to_canonical(b["fuel"], float(b["quantity"]), b["unit"], b.get("therms_per_ccf"))


def charges(b: dict) -> dict:
    """Split a bill's charges. If no line items exist, everything is 'unclassified'."""
    out = {"fixed": 0.0, "variable": 0.0, "demand": 0.0, "tax_other": 0.0, "credits": 0.0, "unclassified": 0.0}
    items = b.get("line_items") or []
    if not items:
        out["unclassified"] = float(b.get("total_usd") or 0.0)
        return out
    for li in items:
        cat = li["category"]
        amt = float(li["amount_usd"])
        if cat in VARIABLE_CATEGORIES:
            out["variable"] += amt
        elif cat == "fixed":
            out["fixed"] += amt
        elif cat == "demand":
            out["demand"] += amt
        elif cat == "credit":
            out["credits"] += amt
        else:
            out["tax_other"] += amt
    return out


def meter_key(b: dict) -> tuple[str, str]:
    """A meter/account stream. Bills without an account are treated as one stream per fuel."""
    return b["fuel"], (b.get("account") or "(no account)")


def by_meter(bills: Iterable[dict]) -> dict[tuple[str, str], list[dict]]:
    out: dict[tuple[str, str], list[dict]] = {}
    for b in bills:
        out.setdefault(meter_key(b), []).append(b)
    for k in out:
        out[k].sort(key=lambda b: (as_date(b["period_start"]), as_date(b["period_end"])))
    return out


def by_fuel(bills: Iterable[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for b in bills:
        out.setdefault(b["fuel"], []).append(b)
    for fuel in out:
        out[fuel].sort(key=lambda b: (as_date(b["period_start"]), as_date(b["period_end"])))
    return out


def latest_window(bills: list[dict], days: int = 365) -> tuple[list[dict], dict]:
    """Bills whose periods fall inside the most recent `days` window for one fuel.

    Returns (bills, coverage) where coverage reports covered days, gaps and whether
    the window is complete enough (>= 360 covered days) to be treated as annual.
    """
    if not bills:
        return [], {"covered_days": 0, "window_days": days, "complete": False}
    end = max(as_date(b["period_end"]) for b in bills)
    start = end - timedelta(days=days)
    chosen = [b for b in bills if as_date(b["period_start"]) >= start - timedelta(days=5)]
    covered = _union_days(chosen)
    window_start = min(as_date(b["period_start"]) for b in chosen) if chosen else end
    return chosen, {
        "window_start": window_start.isoformat(),
        "window_end": end.isoformat(),
        "covered_days": covered,
        "window_days": days,
        "complete": covered >= 360,
    }


def _union_days(bills: list[dict]) -> int:
    spans = sorted((as_date(b["period_start"]), as_date(b["period_end"])) for b in bills)
    total, cur_s, cur_e = 0, None, None
    for s, e in spans:
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += (cur_e - cur_s).days
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        total += (cur_e - cur_s).days
    return total


def safe_canonical(b: dict) -> float | None:
    try:
        return canonical_quantity(b)
    except (UnitError, ValueError, TypeError, KeyError):
        return None


def canonical_unit(fuel: str) -> str:
    return CANONICAL_UNIT.get(fuel, "?")


def bill_cost(b: dict) -> float | None:
    """Known cost of one bill: the total, else the sum of line items, else None (unknown, never zero)."""
    if b.get("total_usd") is not None:
        return float(b["total_usd"])
    items = b.get("line_items") or []
    if items:
        return sum(float(li["amount_usd"]) for li in items)
    return None


SUMMER_MONTHS = (6, 7, 8)
WINTER_MONTHS = (12, 1, 2)


def mid_month(b: dict) -> int:
    s, e = as_date(b["period_start"]), as_date(b["period_end"])
    return (s + (e - s) / 2).month

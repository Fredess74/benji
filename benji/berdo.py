"""Boston BERDO public disclosure loader (2026 disclosure, calendar-year 2025 data).

Privacy: only anonymous numeric/category columns are kept. Owner names, addresses,
parcel and BERDO IDs are dropped, and peers are only reported as aggregate statistics.

Data finding (verified 2026-10-24): in this file the published "Site EUI" column is
~19x smaller than Total Site Energy Usage (kBtu) / Gross Floor Area for the same rows,
which contradicts its own data dictionary. Benji therefore computes site EUI explicitly
as Total Site Energy (kBtu) / Gross Floor Area (sq ft) and does not use that column.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from .store import ROOT

RAW = ROOT / "data" / "raw" / "2026-berdo-data-disclosure-9.30.26.xlsx"
CACHE = ROOT / "data" / "processed" / "berdo_2026_peers.csv"
SOURCE = {
    "title": "City of Boston BERDO Data Disclosure 2026 (2025 data), file 2026-berdo-data-disclosure-9.30.26.xlsx",
    "reporting_year": 2025,
    "disclosure_year": 2026,
    "publisher": "City of Boston Environment Department",
    "local_file": "data/raw/2026-berdo-data-disclosure-9.30.26.xlsx",
    "coverage": "Boston buildings subject to BERDO (generally >= 20,000 sq ft or >= 15 residential units). "
                "Not representative of all Massachusetts buildings.",
}
CATEGORY_TO_BERDO = {"commercial_office": "Office", "multifamily": "Multifamily Housing"}
# small businesses map by business type; BERDO has few such rows, so most comparisons end as "insufficient"
BUSINESS_TO_BERDO = {"retail_store": ["Retail Store"], "grocery": ["Supermarket/Grocery Store"],
                     "food_service": ["Restaurant", "Fast Food Restaurant", "Food Service", "Other - Restaurant/Bar",
                                      "Bar/Nightclub"],
                     "small_office": ["Office"]}
FIELDS = ["largest_type", "gfa", "site_kbtu", "site_eui", "elec_kwh", "elec_kgco2e", "gas_kbtu", "gas_kgco2e",
          "steam_kbtu", "oil_kbtu", "reporting_status", "zip3"]


def _f(v):
    try:
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def build_cache() -> Path:
    import pandas as pd

    d = pd.read_excel(RAW, sheet_name="Buildings & Campuses")
    oil_cols = [c for c in d.columns if c.startswith("Fuel Oil") and c.endswith("Usage (kBtu)")]
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    with CACHE.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(FIELDS)
        for _, r in d.iterrows():
            gfa, site = _f(r["Gross Floor Area (sq ft)"]), _f(r["Total Site Energy Usage (kBtu)"])
            eui = site / gfa if gfa and site is not None and gfa > 0 else None
            oil = sum(_f(r[c]) or 0.0 for c in oil_cols)
            zip_ = str(r.get("Building Address Zip Code") or "")
            w.writerow([r["Largest Property Type"], gfa, site, eui, _f(r["Electricity Usage (kWh)"]),
                        _f(r["Electricity Emissions (kgCO2e)"]), _f(r["Natural Gas Usage (kBtu)"]),
                        _f(r["Natural Gas Emissions (kgCO2e)"]), _f(r["District Steam Usage (kBtu)"]), oil,
                        r["Reporting Compliance Status"], zip_.zfill(5)[:3]])
    return CACHE


@lru_cache(maxsize=1)
def load() -> list[dict]:
    if not CACHE.exists():
        build_cache()
    rows = []
    with CACHE.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.append({k: (_f(v) if k not in ("largest_type", "reporting_status", "zip3") else v) for k, v in r.items()})
    return rows


@lru_cache(maxsize=1)
def emission_factors() -> dict:
    """Emission factors implied by the BERDO disclosure itself (sum of emissions / sum of usage)."""
    rows = load()
    e = [(r["elec_kwh"], r["elec_kgco2e"]) for r in rows if (r["elec_kwh"] or 0) > 0 and (r["elec_kgco2e"] or 0) > 0]
    g = [(r["gas_kbtu"], r["gas_kgco2e"]) for r in rows if (r["gas_kbtu"] or 0) > 0 and (r["gas_kgco2e"] or 0) > 0]
    return {
        "electricity_kg_per_kwh": round(sum(x[1] for x in e) / sum(x[0] for x in e), 4),
        "natural_gas_kg_per_therm": round(100 * sum(x[1] for x in g) / sum(x[0] for x in g), 4),
        "geography": "Boston, MA (BERDO accounting)",
        "year": SOURCE["reporting_year"],
        "accounting": "Site-level direct combustion for natural gas; grid electricity as reported under BERDO. "
                      "Derived as total reported emissions / total reported usage across disclosing buildings.",
        "source": SOURCE["title"],
        "sample_sizes": {"electricity": len(e), "natural_gas": len(g)},
        "data_label": "public_historical",
    }

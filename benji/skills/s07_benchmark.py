"""07 Benchmark Similar Buildings against Boston BERDO peers (site EUI, kBtu/sq ft/yr).

The building's site EUI is computed from 12 months of confirmed bills, converting each fuel
with explicit factors (kWh x 3.412, therms x 100). If any fuel the building uses is not
covered by bills, or the peer group is too small, the skill returns "Insufficient comparable data".
The peer gap is never converted into a savings estimate.
"""

from __future__ import annotations

from datetime import date
from statistics import median, quantiles

from .. import berdo
from .base import COMPLETED, NEEDS_DATA, Evidence, SkillContext, SkillResult

DEFAULT_MIN_SAMPLE = 30
BANDS = [(0.5, 2.0), (1 / 3, 3.0)]
BERDO_SIZE_THRESHOLD_SQFT = 20000
SUPPORTED_BILL_FUELS = {"electricity", "natural_gas"}
MAX_FUEL_END_SPREAD_DAYS = 35
# heating fuel / equipment -> metered fuel it consumes
FUEL_OF = {"heat_pump": "electricity", "electric_resistance": "electricity", "electricity": "electricity",
           "natural_gas": "natural_gas", "oil": "oil", "propane": "propane", "district_steam": "district_steam"}


def required_fuels(b: dict, billed: dict) -> set[str]:
    """Every fuel the building declares or its equipment consumes, plus any fuel already billed."""
    req = {FUEL_OF.get(f, f) for f in (b.get("energy_sources") or [])}
    if b.get("heating_fuel"):
        req.add(FUEL_OF.get(b["heating_fuel"], b["heating_fuel"]))
    for e in b.get("equipment") or []:
        if e.get("kind") in ("heat_pump", "electric_resistance", "split_ac", "chiller", "rooftop_unit"):
            req.add("electricity")
        if e.get("fuel"):
            req.add(FUEL_OF.get(e["fuel"], e["fuel"]))
    return req | set(billed)

LIMITATIONS = [
    "BERDO covers large Boston buildings only; it does not represent all Massachusetts buildings.",
    "Site EUI is not weather-normalised and does not account for occupancy, operating hours or special loads "
    "(e.g. server rooms, laundry).",
    "Annual building totals cannot identify which equipment causes a difference.",
    "A higher EUI than peers indicates where to investigate; it is not a measured or guaranteed saving.",
    "BERDO rows are anonymised here; no peer is treated as an identified building.",
]


def select_peers(category: str, gfa: float, settings: dict, uses_steam: bool,
                 business_type: str | None = None) -> tuple[list[dict], dict]:
    types = (berdo.BUSINESS_TO_BERDO.get(business_type or "", []) if category == "small_business"
             else [berdo.CATEGORY_TO_BERDO.get(category)])
    btype = " / ".join(t for t in types if t) or None
    rows = [r for r in berdo.load() if r["largest_type"] in types and r["site_eui"] and 1 <= r["site_eui"] <= 1000
            and r["gfa"] and r["gfa"] > 0]
    exclude_steam = settings.get("exclude_district_steam", not uses_steam)
    if exclude_steam:
        rows = [r for r in rows if not (r["steam_kbtu"] or 0) > 0]
    min_n = int(settings.get("min_sample", DEFAULT_MIN_SAMPLE))
    bands = [tuple(settings["gfa_band"])] if settings.get("gfa_band") else BANDS
    peers, used = [], None
    for lo, hi in bands:
        peers = [r for r in rows if lo * gfa <= r["gfa"] <= hi * gfa]
        used = (lo, hi)
        if len(peers) >= min_n:
            break
    return peers, {
        "berdo_property_type": btype, "gfa_band": [round(used[0] * gfa), round(used[1] * gfa)],
        "gfa_band_multipliers": [round(used[0], 3), round(used[1], 3)],
        "exclude_district_steam": exclude_steam, "min_sample": min_n,
        "eligible_type_count": len(rows),
    }


def run(ctx: SkillContext) -> SkillResult:
    b = ctx.building
    res = SkillResult("07", COMPLETED)
    res.outputs["source"] = berdo.SOURCE
    res.outputs["limitations"] = LIMITATIONS
    if b.get("category") == "home":
        res.outputs["result"] = "insufficient_comparable_data"
        res.message = ("Insufficient comparable data: BERDO covers large Boston buildings (15+ units or 20,000+ sq ft); "
                       "it is not a suitable peer group for a 1-4 unit home. Benji compares your own bills over time "
                       "instead.")
        return res
    if b.get("category") == "small_business" and not berdo.BUSINESS_TO_BERDO.get(b.get("business_type") or ""):
        res.status = NEEDS_DATA
        res.outputs["result"] = "insufficient_comparable_data"
        res.message = "Insufficient comparable data: choose a business type (store, grocery, food service, office)."
        res.missing_inputs.append({"field": "business_type", "action": "Choose the business type."})
        return res
    costs = ctx.result("09")
    gfa = b.get("gross_floor_area_sqft")
    if not gfa or not costs:
        res.status = NEEDS_DATA
        res.message = ("No peer comparison yet: " + ("add the floor area (sq ft) to compare with similar buildings."
                       if not gfa else "confirmed bills are needed first."))
        if not gfa:
            res.missing_inputs.append({"field": "gross_floor_area_sqft", "action": "Enter the gross floor area."})
        return res
    fuels = costs.outputs["fuels"]
    required = required_fuels(b, fuels)
    unsupported = sorted(required - SUPPORTED_BILL_FUELS)
    missing = sorted((required & SUPPORTED_BILL_FUELS) - set(fuels))
    incomplete = sorted(f for f, s in fuels.items() if not s["coverage"]["complete"])
    res.outputs["required_fuels"] = sorted(required)
    if b.get("bills_cover_whole_building") is False:
        res.outputs["result"] = "insufficient_comparable_data"
        res.message = ("Insufficient comparable data: the bills cover only part of this building's energy use "
                       "(for example tenant-metered electricity), while BERDO reports whole-building totals.")
        res.missing_inputs.append({"field": "bills", "action": "Add whole-building data (e.g. aggregated tenant usage "
                                   "from the utility) to enable a peer comparison."})
        res.evidence.append(Evidence("benchmark.insufficient", res.message, "user_provided"))
        return res
    problems = []
    if unsupported:
        problems.append(f"bills for {', '.join(unsupported)} are not supported yet")
    if missing:
        problems.append(f"no confirmed bills for {', '.join(missing)}, which this building uses")
    if incomplete:
        problems.append(f"{', '.join(incomplete)} bills do not cover 12 months on every meter")
    ends = [date.fromisoformat(s["coverage"]["window_end"]) for s in fuels.values() if s["coverage"]["window_end"]]
    if len(ends) > 1 and (max(ends) - min(ends)).days > MAX_FUEL_END_SPREAD_DAYS:
        problems.append(f"fuel bills cover different years (latest periods end {(max(ends) - min(ends)).days} days apart)")
    if problems:
        res.outputs["result"] = "insufficient_comparable_data"
        res.message = "Insufficient comparable data: " + "; ".join(problems) + "."
        res.missing_inputs.append({"field": "bills", "action": "Provide the same 12 consecutive months of bills for "
                                   "every fuel and meter: " + ", ".join(sorted(required))})
        res.evidence.append(Evidence("benchmark.insufficient", res.message, "user_provided"))
        return res
    if b.get("bills_cover_whole_building") is None:
        res.status = NEEDS_DATA
        res.outputs["result"] = "needs_scope_confirmation"
        res.message = ("Confirm whether these bills cover all energy used in the building (including tenant meters) "
                       "before comparing with BERDO whole-building totals.")
        res.missing_inputs.append({"field": "bills_cover_whole_building",
                                   "action": "Answer yes/no: do the bills include every meter in the building?"})
        return res
    used = required

    site_kbtu = sum(s["recorded_kbtu"] for s in fuels.values())
    eui = site_kbtu / gfa
    peers, selection = select_peers(b["category"], gfa, ctx.settings.get("peer_filters", {}),
                                    uses_steam="district_steam" in used, business_type=b.get("business_type"))
    res.outputs.update({"building_site_eui": round(eui, 1), "unit": "kBtu/sq ft/yr (site)",
                        "building_site_kbtu": round(site_kbtu), "selection": selection, "sample_size": len(peers)})
    why = (f"Peers are BERDO '{selection['berdo_property_type']}' buildings (largest property type) with floor area "
           f"{selection['gfa_band'][0]:,}-{selection['gfa_band'][1]:,} sq ft"
           + (", excluding buildings that use district steam because this building does not" if selection["exclude_district_steam"] else "")
           + f", reporting year {berdo.SOURCE['reporting_year']}.")
    res.outputs["why_this_comparison"] = why
    if gfa < BERDO_SIZE_THRESHOLD_SQFT:
        res.warnings.append(f"This building ({gfa:,.0f} sq ft) is below the usual BERDO size threshold; peers are "
                            "larger buildings and may operate differently.")
    if len(peers) < selection["min_sample"]:
        res.outputs["result"] = "insufficient_comparable_data"
        res.message = (f"Insufficient comparable data: only {len(peers)} BERDO peer(s) match "
                       f"(minimum {selection['min_sample']}). No peer comparison is shown.")
        res.evidence.append(Evidence("benchmark.insufficient", res.message, "public_historical", berdo.SOURCE["title"]))
        return res

    euis = sorted(p["site_eui"] for p in peers)
    q1, q2, q3 = quantiles(euis, n=4)
    pct = 100 * sum(1 for e in euis if e < eui) / len(euis)
    hist_edges = [round(x) for x in quantiles(euis, n=10)]
    res.outputs.update({
        "result": "compared",
        "percentile": round(pct, 1),
        "peer_median": round(median(euis), 1), "peer_q1": round(q1, 1), "peer_q3": round(q3, 1),
        "peer_deciles": hist_edges,
        "position": "above_upper_quartile" if eui > q3 else "below_lower_quartile" if eui < q1 else "middle_half",
    })
    res.message = (f"Site EUI {eui:.1f} kBtu/sq ft is higher than {pct:.0f}% of {len(peers)} comparable BERDO "
                   f"buildings (peer median {median(euis):.1f}).")
    res.evidence.append(Evidence("benchmark.position", res.message + " " + why, "public_historical",
                                 berdo.SOURCE["title"], value=round(pct, 1)))
    res.evidence.append(Evidence("benchmark.building_eui", f"Building site EUI {eui:.1f} computed from 12 months of "
                                 "confirmed bills (kWh x 3.412 + therms x 100) / floor area.",
                                 b.get("data_label", "user_provided"), value=round(eui, 1)))
    return res

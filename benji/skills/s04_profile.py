"""04 Build Property Profile: validate the building profile and list what is missing."""

from __future__ import annotations

from .base import COMPLETED, NEEDS_DATA, Evidence, SkillContext, SkillResult

COMMON_REQUIRED = {
    "category": "Property type (home, small business, office or apartment building)",
    "zip": "ZIP code (used for location-based programs)",
    "heating_fuel": "Primary heating fuel",
    "electric_utility": "Electric utility (program eligibility depends on it)",
}
DECISION_FIELDS = {
    "budget_usd": "Improvement budget",
    "bill_payer": "Who pays the energy bills (owner / tenant / split)",
    "decision_maker": "Who authorizes improvements",
    "upfront_cash_available_usd": "Cash available before installation (separate from total budget)",
    "bills_cover_whole_building": "Do the bills include every meter in the building? (needed for benchmarking)",
}
CATEGORY_REQUIRED = {
    "multifamily": {"dwelling_units": "Number of dwelling units (Mass Save multifamily rules depend on it)",
                    "gross_floor_area_sqft": "Gross floor area in square feet (needed for benchmarking)"},
    "commercial_office": {"gross_floor_area_sqft": "Gross floor area in square feet (needed for benchmarking)"},
    "small_business": {"business_type": "Business type (store, grocery, cafe/restaurant, office)"},
    "home": {"occupant_role": "Do you own, rent, or rent out this home? (decides who can authorize work)"},
}
OPTIONAL_BY_CATEGORY = {
    "home": {"dwelling_units": "Number of units in the building (1-4)",
             "gross_floor_area_sqft": "Living area in square feet (optional)"},
    "small_business": {"occupant_role": "Do you own the space or lease it? (landlord approval may be needed)",
                       "gross_floor_area_sqft": "Floor area in square feet (optional, for comparisons)"},
}
SECTOR = {"home": "residential", "multifamily": "residential", "small_business": "commercial",
          "commercial_office": "commercial"}


def run(ctx: SkillContext) -> SkillResult:
    b = ctx.building
    res = SkillResult("04", COMPLETED)
    missing = []
    for field, label in {**COMMON_REQUIRED, **CATEGORY_REQUIRED.get(b.get("category"), {})}.items():
        if b.get(field) in (None, "", []):
            # Blocking = the analysis would be wrong without it. ZIP, fuel and utility only refine programs.
            blocking = field == "category" or field in CATEGORY_REQUIRED.get(b.get("category"), {})
            missing.append({"field": field, "label": label, "blocking": blocking})
    if b.get("heating_fuel") == "natural_gas" and not b.get("gas_utility"):
        missing.append({"field": "gas_utility", "label": "Gas utility", "blocking": False})
    for field, label in OPTIONAL_BY_CATEGORY.get(b.get("category"), {}).items():
        if b.get(field) in (None, ""):
            missing.append({"field": field, "label": label, "blocking": False})
    if b.get("category") == "home" and b.get("dwelling_units") and b["dwelling_units"] > 4:
        missing.append({"field": "dwelling_units", "label": "Homes are 1-4 units; choose 'apartment building' for 5+",
                        "blocking": True})
    role_known = bool(b.get("occupant_role"))  # role implies default payer / authorizer (see plan skill)
    for field, label in DECISION_FIELDS.items():
        if role_known and field in ("bill_payer", "decision_maker"):
            continue
        if b.get(field) in (None, ""):
            missing.append({"field": field, "label": label, "blocking": False})
    if (b.get("state") or "MA").upper() != "MA":
        res.warnings.append("Benji's program catalog only covers Massachusetts.")
    heating = [e for e in b.get("equipment", []) if e.get("kind") in ("boiler", "furnace", "heat_pump")]
    if not heating:
        missing.append({"field": "equipment", "label": "Primary heating equipment (type, efficiency, age, condition)",
                        "blocking": False})
    gfa = b.get("gross_floor_area_sqft")
    if gfa is not None and gfa <= 0:
        missing.append({"field": "gross_floor_area_sqft", "label": "Floor area must be positive", "blocking": True})
    if b.get("category") == "multifamily" and b.get("dwelling_units") is not None and b["dwelling_units"] < 1:
        missing.append({"field": "dwelling_units", "label": "Dwelling units must be at least 1", "blocking": True})

    res.missing_inputs = missing
    blocking = [m for m in missing if m["blocking"]]
    if blocking:
        res.status = NEEDS_DATA
        res.message = "Profile incomplete: " + "; ".join(m["label"] for m in blocking)
    else:
        res.message = "Profile has the fields required for analysis." + (
            f" {len(missing)} optional field(s) would improve recommendations." if missing else "")
    res.outputs = {
        "category": b.get("category"),
        "sector": SECTOR.get(b.get("category")),
        "business_type": b.get("business_type"), "occupant_role": b.get("occupant_role"),
        "gross_floor_area_sqft": gfa,
        "dwelling_units": b.get("dwelling_units"),
        "heating_fuel": b.get("heating_fuel"),
        "heating_equipment": heating,
        "budget_usd": b.get("budget_usd"),
        "upfront_cash_available_usd": b.get("upfront_cash_available_usd"),  # null = unknown, never assumed
        "bill_payer": b.get("bill_payer"),
        "decision_maker": b.get("decision_maker"),
        "data_label": b.get("data_label", "user_provided"),
    }
    res.evidence.append(Evidence("profile.source", "Building profile entered by the user", b.get("data_label", "user_provided")))
    return res

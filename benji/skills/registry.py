"""Registry of the 20 Benji skills (12 implemented, 8 registered as coming later)."""

from __future__ import annotations

from . import (s01_import, s02_explain, s03_quality, s04_profile, s06_anomaly, s07_benchmark, s08_thermal, s09_costs,
               s10_savings, s13_incentives, s14_eligibility, s17_plan, s20_report)
from .base import SkillSpec

CATEGORIES = {
    "data": "Understand Data",
    "performance": "Analyze Performance",
    "costs": "Costs & Savings",
    "incentives": "Incentives & Funding",
    "action": "Plan, Act & Report",
}

_S = SkillSpec
SKILLS: dict[str, SkillSpec] = {s.id: s for s in [
    _S("01", "Import Energy Data", "data",
       "Import CSV and text-PDF bills, keep the original file, and require confirmation of extracted values.",
       ["file (CSV template or text PDF) or manual bill entry"], ["bill drafts (pending_confirmation)", "import status"],
       ["none"], "Original file hash and excerpt stored with each bill; PDF extraction is label-based and marked uncertain.",
       "Unsupported or scanned files return an explanation and a manual-entry path; nothing is saved unconfirmed.",
       True, run=s01_import.run),
    _S("02", "Explain Energy Bills", "data",
       "Explain charge categories and separate consumption changes from price changes between bills.",
       ["confirmed bills with charge breakdown"], ["per-bill breakdown", "bill-to-bill change decomposition"],
       ["confirmed bills"], "Exact arithmetic decomposition; requires fixed vs usage-based line items.",
       "Without a charge breakdown, reports that price and usage effects cannot be separated.",
       True, depends_on=["01"], run=s02_explain.run),
    _S("03", "Check Data Quality", "data",
       "Detect missing periods, overlaps, duplicates, unit errors, implausible values and incomplete records.",
       ["all bills"], ["issues with severity and specific correction action"], ["at least one bill"],
       "Rule-based checks on the user's own bills.", "Returns needs_data when there are no confirmed bills.",
       True, depends_on=["01"], mandatory=True, run=s03_quality.run),
    _S("04", "Build Property Profile", "data",
       "Store and validate building type, location, area, schedule, fuels, equipment, budget, bill payer and decision-maker.",
       ["building profile"], ["validated profile", "missing fields"], ["none"],
       "User-provided profile; required fields depend on category.", "Lists blocking and optional missing fields.",
       True, mandatory=True, run=s04_profile.run),
    _S("05", "Detect After-Hours Usage", "performance",
       "Identify energy use outside occupied hours.", ["interval (15-min/hourly) meter data"], ["after-hours load profile"],
       ["interval data - not supported"], "Monthly bills cannot show overnight activity.", "Unavailable.", False),
    _S("06", "Detect Unusual Consumption", "performance",
       "Flag unusual changes against the same period a year earlier, normalised by billing days.",
       ["confirmed bills (13+ months)", "recorded operating changes"], ["anomalies with context questions"],
       ["13+ months of confirmed bills"], "Not weather-normalised; threshold is an explicit assumption.",
       "Returns needs_data without prior-year bills.", True, depends_on=["01"], requires_valid_bills=True,
       run=s06_anomaly.run),
    _S("07", "Benchmark Similar Buildings", "performance",
       "Compare site EUI with suitable Boston BERDO peers, explain the selection and show sample size and limits.",
       ["category", "floor area", "12 months of bills for every fuel"], ["percentile", "peer quartiles", "selection", "limitations"],
       ["complete annual bills", "floor area"], "BERDO 2026 disclosure (2025 data); explicit fuel conversions.",
       "Returns 'Insufficient comparable data' when peers are too few or fuels are not covered.",
       True, depends_on=["04", "09"], requires_valid_bills=True, run=s07_benchmark.run),
    _S("08", "Room Heating & Cooling Scenario", "performance",
       "Bounded single-zone scenario: can a room reach a comfortable temperature, how long might it take, how much "
       "thermal and purchased energy and cost might it need, and would an envelope or HVAC change help. Does not "
       "infer heat loss from bills or floor area.",
       ["room temperatures", "heat-loss coefficient or surfaces + air changes", "effective thermal capacity",
        "system thermal output and COP / combustion efficiency", "optional gains and price"],
       ["temperature-time series", "time to target or target_not_reachable", "delivered vs consumed energy",
        "variable cost", "capacity headroom/shortfall", "alternatives side by side"],
       ["saved room scenario"], "Analytical solution of C dT/dt = Q + G - H (T - T_out); cross-checked with RK4. "
       "Sensible-only cooling. Inputs labelled with their source.",
       "Missing heat loss, capacity or output return needs_data with the exact fields; nothing is defaulted.",
       True, uses_if_available=["09"], run=s08_thermal.run),
    _S("09", "Calculate Energy Costs", "costs",
       "Calculate recorded and annual costs per fuel, separating fixed, usage-based and demand charges.",
       ["confirmed bills", "optional tariff inputs"], ["costs per fuel", "usage-based rates", "heating/baseload split"],
       ["confirmed bills"], "Rates derived from the user's own bill line items or user tariff input.",
       "Annualises only with a labelled assumption (>=180 days); otherwise reports recorded totals only.",
       True, depends_on=["01"], requires_valid_bills=True, run=s09_costs.run),
    _S("10", "Estimate Savings & Payback", "costs",
       "Compare supported measures and scenarios with transparent methods, cost inputs and payback.",
       ["costs (09)", "measure inputs and quotes", "eligibility (14) optional"],
       ["per-measure results", "scenarios", "confirmed vs hypothetical financials"],
       ["usage-based rates", "measure-specific inputs"], "Measure catalog methods; assumptions labelled; BERDO-derived emission factors.",
       "Measures missing inputs return needs_data with the exact missing items.",
       True, depends_on=["09"], uses_if_available=["14"], requires_valid_bills=True, run=s10_savings.run),
    _S("11", "Forecast Energy Use & Budget", "costs", "Forecast future use and spend.", ["weather-normalised history, tariffs"],
       ["forecast"], ["weather normalisation"], "Not implemented.", "Unavailable.", False),
    _S("12", "Model Business Expansion", "costs", "Model energy impact of expansion.", ["expansion plans"], ["scenario"],
       ["load model"], "Not implemented.", "Unavailable.", False),
    _S("13", "Find Energy Incentives", "incentives",
       "Find potentially relevant programs by category, location, utility, fuel and measure.",
       ["building category", "state", "candidate measures"], ["matching program records with sources"],
       ["building category"], "Curated catalog with source URL and verification status per record.",
       "Unverified records are labelled as leads.", True, run=s13_incentives.run),
    _S("14", "Check Program Eligibility", "incentives",
       "Evaluate known criteria: Potentially eligible / Known condition not met / More information needed.",
       ["matches (13)", "profile", "eligibility answers"], ["status per program", "questions"],
       ["program matches"], "Explicit rules from catalog conditions. Final approval stays with the program operator.",
       "Unknown answers produce 'More information needed', never 'eligible'.", True, depends_on=["13"], run=s14_eligibility.run),
    _S("15", "Prepare Application Documents", "incentives", "Draft program applications.", ["confirmed project data"],
       ["draft documents"], ["program forms"], "Not implemented.", "Unavailable.", False),
    _S("16", "Compare Rebates & Financing", "incentives", "Compare financing offers in detail.", ["loan terms"],
       ["financing comparison"], ["verified financing terms"], "Not implemented.", "Unavailable.", False),
    _S("17", "Create Energy Action Plans", "action",
       "Turn results into ordered recommendations and tasks with owners, prerequisites, dates and statuses.",
       ["profile (04)", "optional: 03, 06, 07, 10, 14"], ["recommendations", "tasks", "next action"],
       ["building profile"], "Rule-based ordering with stated reasons.", "Works with fewer skills; states what is missing.",
       True, uses_if_available=["04", "03", "06", "07", "08", "10", "14"], run=s17_plan.run),
    _S("18", "Send Energy Alerts", "action", "Notify about new anomalies.", ["continuous data feed"], ["alerts"],
       ["live data connection"], "Not implemented.", "Unavailable.", False),
    _S("19", "Measure Changes After Actions", "action", "Measure post-installation results.",
       ["post-action bills", "baseline model"], ["measured savings"], ["weather-normalised baseline"],
       "Not implemented; Benji reports no measured savings.", "Unavailable.", False),
    _S("20", "Generate Energy Performance Reports", "action",
       "Export evidence, assumptions, comparisons, scenarios and the action plan as dated snapshots.",
       ["analysis results", "plan"], ["Markdown/HTML report"], ["any completed skill"],
       "Separates estimates from measured outcomes; labels synthetic data.", "Reports which sections are missing.",
       True, uses_if_available=["03", "06", "07", "09", "10", "14", "17"], run=s20_report.run),
]}

EXECUTION_ORDER = ["04", "01", "03", "02", "09", "06", "07", "08", "13", "14", "10", "17", "20"]
IMPLEMENTED = [s for s in EXECUTION_ORDER]

# Which inputs invalidate which skills.
INVALIDATION = {
    "building": set(IMPLEMENTED),
    "bills": {"01", "02", "03", "06", "07", "08", "09", "10", "17", "20"},
    "measure_inputs": {"10", "17", "20"},
    "thermal": {"08", "17", "20"},
    "settings": set(IMPLEMENTED),
    "versions": set(IMPLEMENTED),
}


def list_skills() -> list[dict]:
    return [SKILLS[k].to_dict() | {"category_label": CATEGORIES[SKILLS[k].category]} for k in sorted(SKILLS)]

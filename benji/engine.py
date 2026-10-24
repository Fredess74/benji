"""Analysis engine: runs the selected skills in dependency order and tracks staleness.

* Core validation skills (03 Data Quality, 04 Profile, and their prerequisite 01) always run.
* While skill 03 reports blocking errors, skills that draw conclusions from bills (06, 07, 09, 10) are
  suppressed with ``blocked_by_data_quality``. The plan and a diagnostic report are still produced, but they
  are marked ``decision_ready = false``.
* Every saved plan carries the input fingerprints and catalog/model versions of the run that produced it,
  so a later partial or failed rerun can never make an old plan look current.

The same entry points are used by the HTTP API, tests, and future assistant integrations.
"""

from __future__ import annotations

import hashlib
import json
import traceback
from functools import lru_cache
from typing import Iterable, Optional

from . import __version__
from .skills.base import BLOCKED, BLOCKED_DQ, COMPLETED, FAILED, NOT_SELECTED, SkillContext, SkillResult
from .skills.registry import EXECUTION_ORDER, INVALIDATION, SKILLS
from .store import Store, now_iso
from .validation import validate_settings


def _hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


@lru_cache(maxsize=1)
def versions() -> dict:
    from . import berdo
    from .catalog.measures import CATALOG_VERSION
    from .skills.s13_incentives import catalog

    raw = berdo.RAW if berdo.RAW.exists() else berdo.CACHE  # public repo ships only the anonymised cache
    sha = hashlib.sha256(raw.read_bytes()).hexdigest() if raw.exists() else None
    return {"benji": __version__, "incentive_catalog": catalog()["catalog_version"], "measure_catalog": CATALOG_VERSION,
            "berdo_file": raw.name, "berdo_sha256": sha, "berdo_reporting_year": berdo.SOURCE["reporting_year"],
            "emission_factors": "berdo_2026_derived", "thermal_model": "single_zone_rc_v1"}


def fingerprints(store: Store, building_id: str, settings: dict | None = None) -> dict:
    b = store.get_building(building_id) or {}
    return {
        "building": _hash(b),
        "bills": _hash(sorted(store.list_bills(building_id), key=lambda x: x["id"])),
        "measure_inputs": _hash(store.list_measure_inputs(building_id)),
        "thermal": _hash(store.list_children("thermal_scenarios", building_id)),
        "settings": _hash({k: v for k, v in (settings or {}).items() if k not in ("previous_plan", "generated_at")}),
        "versions": _hash(versions()),
    }


def _effective_selection(selected: Iterable[str]) -> set[str]:
    sel = set(selected)
    for sid, spec in SKILLS.items():
        if spec.mandatory and spec.implemented:
            sel.add(sid)
            sel |= set(spec.depends_on)
    return sel


def run_skills(building: dict, bills: list[dict], measure_inputs: dict, selected: Iterable[str],
               settings: dict | None = None, thermal_scenarios: list[dict] | None = None) -> dict[str, SkillResult]:
    selected = _effective_selection(selected)
    ctx = SkillContext(building=building, bills=bills, measure_inputs=measure_inputs, results={},
                       selected=selected, settings=settings or {}, thermal_scenarios=thermal_scenarios or [])
    out: dict[str, SkillResult] = {}
    for sid in EXECUTION_ORDER:
        spec = SKILLS[sid]
        if sid not in selected:
            out[sid] = SkillResult(sid, NOT_SELECTED, message="Not selected for this analysis.")
            continue
        q = ctx.results.get("03")
        if spec.requires_valid_bills and q and q.status == COMPLETED and q.outputs.get("blocking"):
            errs = [i for i in q.outputs["issues"] if i["severity"] == "error"]
            r = SkillResult(sid, BLOCKED_DQ, message=f"Suppressed: {len(errs)} bill data error(s) must be fixed first "
                                                      f"(e.g. {errs[0]['message']}).")
            r.missing_inputs = [{"field": "bills", "action": i["correction_action"], "bill_ids": i["bill_ids"]} for i in errs]
            out[sid] = r
            continue
        missing = [d for d in spec.depends_on if not ctx.result(d)]
        if missing:
            names = ", ".join(f"{d} {SKILLS[d].name}" for d in missing)
            r = SkillResult(sid, BLOCKED, message=f"Requires completed skill(s): {names}.")
            r.missing_inputs = [{"skill": d, "action": f"Select and complete skill {d} ({SKILLS[d].name})."} for d in missing]
            out[sid] = r
            continue
        try:
            r = spec.run(ctx)
        except Exception as exc:  # a failing skill must not break the rest of the analysis
            r = SkillResult(sid, FAILED, message=f"{type(exc).__name__}: {exc}")
            r.warnings.append(traceback.format_exc(limit=3))
        ctx.results[sid] = r
        out[sid] = r
    return out


def decision_ready(results: dict) -> tuple[bool, list[str]]:
    reasons = []
    q = results.get("03")
    if q and q.get("outputs", {}).get("blocking"):
        reasons.append("Bill data errors must be fixed.")
    for sid in ("09", "10"):
        st = results.get(sid, {}).get("status")
        if st not in (COMPLETED, NOT_SELECTED):
            reasons.append(f"Skill {sid} ({SKILLS[sid].name}) is {st}.")
    return not reasons, reasons


def analyze(store: Store, building_id: str, selected: Optional[Iterable[str]] = None,
            settings: Optional[dict] = None) -> dict:
    building = store.get_building(building_id)
    if not building:
        raise KeyError(building_id)
    settings = validate_settings(settings)
    selected = list(selected) if selected is not None else list(EXECUTION_ORDER)
    unknown = [s for s in selected if s not in SKILLS]
    unavailable = [s for s in selected if s in SKILLS and not SKILLS[s].implemented]
    selected = sorted(_effective_selection(s for s in selected if s in SKILLS and SKILLS[s].implemented))
    persisted_settings = dict(settings)
    settings["previous_plan"] = store.get_plan(building_id)
    settings["generated_at"] = now_iso()
    results = run_skills(building, store.list_bills(building_id), store.list_measure_inputs(building_id),
                         selected, settings, store.list_children("thermal_scenarios", building_id))
    res_dicts = {k: v.to_dict() for k, v in results.items()}
    ready, not_ready = decision_ready(res_dicts)
    fp = fingerprints(store, building_id, persisted_settings)
    analysis = {
        "building_id": building_id, "ran_at": settings["generated_at"], "selected_skills": selected,
        "settings": persisted_settings, "fingerprints": fp, "versions": versions(),
        "results": res_dicts, "decision_ready": ready, "not_decision_ready_reasons": not_ready,
        "ignored_skills": {"unknown": unknown, "coming_later": unavailable},
        "data_label": building.get("data_label", "user_provided"),
    }
    store.save_analysis(building_id, analysis)
    plan_res = results.get("17")
    if plan_res and plan_res.status == COMPLETED:
        plan = plan_res.outputs["plan"]
        plan["provenance"] = {"analysis_ran_at": analysis["ran_at"], "fingerprints": fp, "settings": persisted_settings,
                              "selected_skills": selected, "versions": versions()}
        plan["decision_ready"] = ready and plan.get("decision_ready", True)
        store.save_plan(building_id, plan)
    return with_staleness(store, analysis)


def _changed(store: Store, building_id: str, fp: dict, settings: dict) -> list[str]:
    now = fingerprints(store, building_id, settings)
    return [k for k, v in now.items() if fp.get(k) != v]


def with_staleness(store: Store, analysis: Optional[dict]) -> Optional[dict]:
    """Mark results stale when inputs changed after the analysis ran."""
    if not analysis:
        return None
    changed = _changed(store, analysis["building_id"], analysis["fingerprints"], analysis.get("settings"))
    stale = set()
    for k in changed:
        stale |= INVALIDATION.get(k, set(EXECUTION_ORDER))
    analysis = dict(analysis)
    analysis["stale"] = bool(stale)
    analysis["changed_inputs"] = changed
    analysis["stale_skills"] = sorted(stale & set(analysis["selected_skills"]))
    if stale:
        analysis["stale_message"] = (f"Inputs changed ({', '.join(changed)}). Results of skills "
                                     f"{', '.join(analysis['stale_skills'])} are out of date; re-run the analysis.")
    return analysis


def get_plan(store: Store, building_id: str) -> Optional[dict]:
    """A plan is current only if the inputs that produced *it* are unchanged (not the latest analysis)."""
    plan = store.get_plan(building_id)
    if not plan:
        return None
    plan = dict(plan)
    prov = plan.get("provenance")
    if not prov:
        plan["stale"], plan["changed_inputs"] = True, ["unknown_provenance"]
        return plan
    changed = _changed(store, building_id, prov["fingerprints"], prov.get("settings"))
    plan["stale"] = bool(changed)
    plan["changed_inputs"] = changed
    if changed:
        plan["stale_message"] = (f"This plan was produced on {prov['analysis_ran_at']}; inputs changed since "
                                 f"({', '.join(changed)}). Re-run the full analysis to update it.")
    return plan


def update_task(store: Store, building_id: str, task_id: str, changes: dict) -> dict:
    plan = store.get_plan(building_id)
    if not plan:
        raise KeyError("plan")
    allowed = {"status", "owner", "due_date", "next_step"}
    for t in plan["tasks"]:
        if t["id"] == task_id:
            t.update({k: v for k, v in changes.items() if k in allowed})
            t["edited_by_user"] = True
            open_tasks = [x for x in plan["tasks"] if x["status"] not in ("done", "skipped")]
            plan["next_action"] = open_tasks[0]["title"] if open_tasks else None
            store.save_plan(building_id, plan)
            return t
    raise KeyError(task_id)

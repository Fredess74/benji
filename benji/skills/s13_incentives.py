"""13 Find Energy Incentives: potentially relevant programs by sector, location and measure.

Residential (multifamily) and commercial records are kept separate by the `sectors` field;
a record is never shown for a sector it does not list.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from ..catalog.measures import MEASURES
from .base import COMPLETED, NEEDS_DATA, Evidence, SkillContext, SkillResult

CATALOG_PATH = Path(__file__).resolve().parent.parent / "catalog" / "incentives.json"


@lru_cache(maxsize=1)
def catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def find(category: str, state: str, measure_ids: list[str]) -> list[dict]:
    wanted = {MEASURES[m]["incentive_measure"]: m for m in measure_ids if m in MEASURES}
    out = []
    for rec in catalog()["records"]:
        if category not in rec["sectors"] or (state or "").upper() != rec["location"]:
            continue
        hits = [wanted[im] for im in rec["measures"] if im in wanted]
        if hits:
            out.append({"record": rec, "benji_measures": sorted(set(hits))})
    return out


def run(ctx: SkillContext) -> SkillResult:
    b = ctx.building
    res = SkillResult("13", COMPLETED)
    if not b.get("category"):
        res.status = NEEDS_DATA
        res.message = "Building category is required."
        return res
    measures = [m for m, spec in MEASURES.items() if b["category"] in spec["categories"]]
    found = find(b["category"], b.get("state", "MA"), measures)
    res.outputs = {"matches": found, "catalog_version": catalog()["catalog_version"], "notice": catalog()["notice"]}
    unverified = sum(1 for f in found if f["record"]["verification_status"] != "verified")
    if unverified:
        res.warnings.append(f"{unverified} of {len(found)} program record(s) are not verified against a current "
                            "official page; treat them as leads, not commitments.")
    res.message = f"{len(found)} potentially relevant program(s) for a {b['category'].replace('_', ' ')} building."
    for f in found:
        r = f["record"]
        res.evidence.append(Evidence(f"incentive.{r['id']}", f"{r['name']} ({r['incentive_type']}, {r['timing']})",
                                     "public_historical" if r["verification_status"] == "verified" else "assumption",
                                     r["source_url"]))
    return res

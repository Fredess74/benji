"""Skill contract shared by every Benji skill.

A skill is a plain function ``run(ctx) -> SkillResult``. The dashboard, the HTTP API
and any future assistant integration call the same functions through the registry,
so calculation logic lives in exactly one place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..store import now_iso

# Run statuses shown to the user.
COMPLETED = "completed"
NEEDS_DATA = "needs_data"
FAILED = "failed"
NOT_SELECTED = "not_selected"
BLOCKED = "blocked_by_prerequisite"
BLOCKED_DQ = "blocked_by_data_quality"


@dataclass
class Evidence:
    id: str
    text: str
    data_label: str  # see models.DataLabel
    source: Optional[str] = None
    value: Any = None

    def to_dict(self) -> dict:
        return {"id": self.id, "text": self.text, "data_label": self.data_label, "source": self.source, "value": self.value}


@dataclass
class SkillResult:
    skill_id: str
    status: str
    outputs: dict = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)
    assumptions: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_inputs: list[dict] = field(default_factory=list)
    message: str = ""
    ran_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "status": self.status,
            "message": self.message,
            "outputs": self.outputs,
            "evidence": [e.to_dict() for e in self.evidence],
            "assumptions": self.assumptions,
            "warnings": self.warnings,
            "missing_inputs": self.missing_inputs,
            "ran_at": self.ran_at,
        }


@dataclass
class SkillContext:
    """Everything a skill may read. Skills never write to storage directly."""

    building: dict
    bills: list[dict]  # all bills (pending + confirmed) as dicts
    measure_inputs: dict[str, dict]
    results: dict[str, SkillResult]  # results of skills already run in this analysis
    selected: set[str]
    settings: dict = field(default_factory=dict)
    thermal_scenarios: list[dict] = field(default_factory=list)

    @property
    def confirmed_bills(self) -> list[dict]:
        return [b for b in self.bills if b.get("status") == "confirmed"]

    def result(self, skill_id: str) -> Optional[SkillResult]:
        r = self.results.get(skill_id)
        return r if r and r.status == COMPLETED else None


@dataclass
class SkillSpec:
    id: str
    name: str
    category: str
    purpose: str
    inputs: list[str]
    outputs: list[str]
    data_prerequisites: list[str]
    evidence_and_assumptions: str
    failure_behavior: str
    implemented: bool
    depends_on: list[str] = field(default_factory=list)  # skills whose results are required
    mandatory: bool = False  # always runs, regardless of checkbox selection (core validation)
    requires_valid_bills: bool = False  # suppressed while skill 03 reports blocking errors
    uses_if_available: list[str] = field(default_factory=list)  # optional upstream skills
    run: Optional[Callable[[SkillContext], SkillResult]] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "purpose": self.purpose,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "data_prerequisites": self.data_prerequisites,
            "evidence_and_assumptions": self.evidence_and_assumptions,
            "failure_behavior": self.failure_behavior,
            "implementation_status": "implemented" if self.implemented else "coming_later",
            "mandatory": self.mandatory,
            "requires_valid_bills": self.requires_valid_bills,
            "depends_on": self.depends_on,
            "uses_if_available": self.uses_if_available,
        }

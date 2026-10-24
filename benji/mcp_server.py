"""Benji MCP server (stdio) for Claude Desktop / Claude Code and any MCP-capable agent.

Run:  python -m benji.mcp_server
Benji's intelligence is in the skills (skills/*/SKILL.md). This server gives agents without file access the
shared memory (the same files the dashboard reads) and a deterministic cross-check of money numbers.
"""

from __future__ import annotations

from typing import Any, Optional

from fastmcp import FastMCP

from . import memory, thermal

INSTRUCTIONS = """Benji: AI energy manager for Massachusetts homes, renters, small businesses and buildings.
Follow the benji-orchestrator skill. Memory: one folder per place (list_places, read_place, create_place,
write_file, append_log). Data you extracted stays 'pending' in bills.csv until the user confirms it.
Use cross_check before stating money results. Never invent tariffs, amounts or eligibility."""

mcp = FastMCP("Benji", instructions=INSTRUCTIONS)
CH = "claude"


def _safe(fn, *a, **kw) -> Any:
    try:
        return fn(*a, **kw)
    except memory.MemoryError_ as exc:
        return {"error": "invalid_input", "message": str(exc)}
    except KeyError as exc:
        return {"error": "not_found", "message": f"Unknown {exc}. Call list_places."}


@mcp.tool
def list_places() -> list[dict]:
    """All places in Benji memory with next step, pending bills, open tasks and questions."""
    return memory.list_places()


@mcp.tool
def read_place(slug: str) -> dict:
    """Everything Benji remembers about one place: raw files (profile.md, bills.csv, findings.md, plan.md,
    open-questions.md, log.md) plus parsed profile, tasks, open questions and recent log."""
    return _safe(memory.read_place, slug)


@mcp.tool
def create_place(slug: str, name: str) -> dict:
    """Create a new place folder from the templates. slug: lowercase-dashes, e.g. 'corner-bean-cambridge'."""
    return _safe(memory.create_place, slug, name, CH)


@mcp.tool
def write_file(slug: str, file: str, content: str, skill: str = "") -> dict:
    """Replace one memory file: profile.md, bills.csv, findings.md, plan.md, open-questions.md or
    documents/<name>.md|txt|csv. Read it first and keep what is still true. Logged automatically."""
    return _safe(memory.write_file, slug, file, content, CH, skill)


@mcp.tool
def append_log(slug: str, skill: str, what: str) -> dict:
    """Append one line to the place's activity log."""
    return _safe(lambda: (memory.append_log(slug, skill, CH, what), {"ok": True})[1])


@mcp.tool
def confirm_bills(slug: str, bill_ids: Optional[list[str]] = None) -> dict:
    """Mark pending bills confirmed AFTER the user said the read-back values are right (all pending if omitted)."""
    return _safe(memory.confirm_bills, slug, bill_ids, "user via claude", CH)


@mcp.tool
def update_task(slug: str, task_id: str, status: Optional[str] = None, owner: Optional[str] = None,
                due: Optional[str] = None) -> dict:
    """Update a task row in plan.md (status: not_started|in_progress|blocked|done|skipped; due: YYYY-MM-DD)."""
    return _safe(memory.update_task, slug, task_id, status, owner, due, CH)


@mcp.tool
def cross_check(slug: str) -> dict:
    """Deterministically recompute costs, usage-based rates, heating share, peer comparison, applicable options
    and program leads from the place's profile.md and CONFIRMED bills. Use it to verify your numbers."""
    return _safe(memory.cross_check, slug)


@mcp.tool
def room_heating_scenario(inputs: dict, alternatives: Optional[list[dict]] = None) -> dict:
    """Single-room warm-up/cool-down. Needs heat_loss_coefficient_w_per_k (or surfaces),
    effective_capacity_kwh_per_k and hvac.thermal_output_kw; missing values are reported, never guessed."""
    try:
        thermal.ScenarioInputs(**inputs)
        return thermal.compare(inputs, alternatives or [])
    except ValueError as exc:
        return {"error": "invalid_input", "message": str(exc)[:800]}


if __name__ == "__main__":
    mcp.run()

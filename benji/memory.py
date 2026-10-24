"""File-based Benji memory (the single source of truth shared by agents and the dashboard).

Layout and rules: skills/_shared/memory.md. Each place is a folder of Markdown/CSV files that agents write and
people can read. This module only reads, writes and parses those files safely; it never decides anything.
"""

from __future__ import annotations

import csv
import io
import os
import re
import shutil
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TEMPLATES = REPO / "skills" / "_shared" / "templates"
FILES = ("profile.md", "bills.csv", "findings.md", "plan.md", "open-questions.md", "log.md")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,60}$")
DOC_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}\.(md|txt|csv)$")
CHANNELS = {"dashboard", "claude", "chatgpt", "openclaw", "kiro", "agent", "user"}


class MemoryError_(ValueError):
    pass


def root() -> Path:
    r = Path(os.environ.get("BENJI_MEMORY", REPO / "benji-memory")).expanduser().resolve()  # plugin: ~/benji-memory
    r.mkdir(parents=True, exist_ok=True)
    return r


def _place(slug: str, must_exist: bool = True) -> Path:
    if not SLUG.match(slug or ""):
        raise MemoryError_("place slug must be lowercase letters, digits and dashes")
    p = (root() / slug).resolve()
    if p.parent != root():
        raise MemoryError_("invalid place")
    if must_exist and not p.is_dir():
        raise KeyError(slug)
    return p


def _file(slug: str, name: str) -> Path:
    base = _place(slug)
    if name in FILES:
        return base / name
    if name.startswith("documents/") and DOC_NAME.match(name.split("/", 1)[1]):
        (base / "documents").mkdir(exist_ok=True)
        return base / name
    raise MemoryError_(f"file must be one of {', '.join(FILES)} or documents/<name>.md|txt|csv")


def _chan(channel: str) -> str:
    c = (channel or "agent").lower()
    return c if c in CHANNELS else "agent"


def _clean(text: str) -> str:
    return re.sub(r"[\r\n|]+", " ", str(text)).strip()[:300]


# ---------------------------------------------------------------- write
def create_place(slug: str, name: str, channel: str = "agent") -> dict:
    p = _place(slug, must_exist=False)
    if p.exists():
        raise MemoryError_("place already exists")
    p.mkdir()
    for f in FILES:
        src = TEMPLATES / f
        text = src.read_text(encoding="utf-8") if src.exists() else ""
        if f == "profile.md":
            text = text.replace("name:              # source, date",
                                f"name: {_clean(name)}  # source: user, {date.today().isoformat()}", 1)
        (p / f).write_text(text, encoding="utf-8")
    append_log(slug, "benji-profile", channel, f"created place '{_clean(name)}'")
    return {"slug": slug, "files": list(FILES)}


def write_file(slug: str, name: str, content: str, channel: str = "agent", skill: str = "") -> dict:
    if len(content) > 500_000:
        raise MemoryError_("file too large (500 KB limit)")
    if name == "log.md":
        raise MemoryError_("log.md is append-only: use append_log")
    path = _file(slug, name)
    path.write_text(content, encoding="utf-8")
    append_log(slug, skill or "-", channel, f"wrote {name}")
    return {"slug": slug, "file": name, "bytes": len(content.encode("utf-8"))}


def append_log(slug: str, skill: str, channel: str, what: str) -> None:
    path = _place(slug) / "log.md"
    if not path.exists():
        path.write_text((TEMPLATES / "log.md").read_text(encoding="utf-8"), encoding="utf-8")
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"{date.today().isoformat()} | {_clean(skill) or '-'} | {_chan(channel)} | {_clean(what)}\n")


# ---------------------------------------------------------------- parse
def parse_front_matter(text: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    out = {}
    for line in (m.group(1).splitlines() if m else []):
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        k, _, v = line.partition(":")
        value, _, note = v.partition("#")
        out[k.strip()] = {"value": value.strip() or None, "note": note.strip() or None}
    return out


def parse_table(text: str, heading: str | None = None) -> list[dict]:
    """First Markdown table (optionally the first one after `heading`) as a list of dicts."""
    if heading:
        i = text.find(heading)
        if i < 0:
            return []
        text = text[i:]
    rows, header = [], None
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            if header is not None and rows is not None and s:
                break
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            header = cells
        elif set("".join(cells)) <= set("-: "):
            continue
        else:
            rows.append(dict(zip(header, cells)))
    return rows


def _section(text: str, heading: str) -> str | None:
    m = re.search(rf"^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s|\Z)", text, re.S | re.M)
    if not m:
        return None
    body = "\n".join(l for l in m.group(1).strip().splitlines() if not l.strip().startswith("<!--")).strip()
    return body or None


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_bills(slug: str) -> list[dict]:
    text = _read(_place(slug) / "bills.csv")
    return [dict(r) for r in csv.DictReader(io.StringIO(text))] if text.strip() else []


def read_log(slug: str) -> list[dict]:
    out = []
    for line in _read(_place(slug) / "log.md").splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 4 and re.match(r"\d{4}-\d{2}-\d{2}", parts[0]):
            out.append({"date": parts[0], "skill": parts[1], "channel": parts[2], "what": parts[3]})
    return out


def read_place(slug: str) -> dict:
    p = _place(slug)
    raw = {f: _read(p / f) for f in FILES}
    plan, findings = raw["plan.md"], raw["findings.md"]
    bills = read_bills(slug)
    docs = sorted(f.name for f in (p / "documents").glob("*")) if (p / "documents").is_dir() else []
    return {
        "slug": slug,
        "profile": parse_front_matter(raw["profile.md"]),
        "next_step": _section(plan, "Next step"),
        "actions": parse_table(plan, "## Actions"),
        "tasks": parse_table(plan, "## Tasks"),
        "not_now": _section(plan, "Not now, and why"),
        "plan_stale": "STALE since" in plan,
        "findings": re.findall(r"^##\s+(F-\d+.*)$", findings, re.M),
        "findings_stale": "STALE since" in findings,
        "bills": bills,
        "bills_pending": sum(1 for b in bills if b.get("status") == "pending"),
        "open_questions": [q for q in parse_table(raw["open-questions.md"]) if not q.get("Answer")],
        "log": read_log(slug)[-50:],
        "documents": docs,
        "raw": raw,
    }


def list_places() -> list[dict]:
    out = []
    for d in sorted(x for x in root().iterdir() if x.is_dir() and SLUG.match(x.name)):
        try:
            r = read_place(d.name)
        except Exception:  # unreadable folder: still list it
            out.append({"slug": d.name, "name": d.name, "error": "unreadable"})
            continue
        prof = r["profile"]
        val = lambda k: (prof.get(k) or {}).get("value")
        open_tasks = [t for t in r["tasks"] if (t.get("Status") or "").strip() not in ("done", "skipped", "")]
        out.append({"slug": d.name, "name": val("name") or d.name, "place_type": val("place_type"),
                    "user_role": val("user_role"), "next_step": r["next_step"], "bills_pending": r["bills_pending"],
                    "open_tasks": len(open_tasks), "open_questions": len(r["open_questions"]),
                    "stale": r["plan_stale"] or r["findings_stale"],
                    "last_activity": r["log"][-1] if r["log"] else None})
    return out


# ---------------------------------------------------------------- management actions (dashboard)
def confirm_bills(slug: str, bill_ids: list[str] | None, by: str, channel: str = "dashboard") -> dict:
    path = _place(slug) / "bills.csv"
    rows = read_bills(slug)
    if not rows:
        return {"confirmed": 0}
    n = 0
    for r in rows:
        if r.get("status") == "pending" and (bill_ids is None or r.get("bill_id") in bill_ids):
            r["status"], r["confirmed_by"], r["confirmed_on"] = "confirmed", _clean(by), date.today().isoformat()
            n += 1
    fields = list(rows[0].keys())
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue(), encoding="utf-8")
    if n:
        append_log(slug, "benji-bills-import", channel, f"{n} bill(s) confirmed by {_clean(by)}")
        _mark_stale(slug, f"{n} bill(s) confirmed")
    return {"confirmed": n}


def _mark_stale(slug: str, reason: str) -> None:
    for f in ("plan.md", "findings.md"):
        path = _place(slug) / f
        text = _read(path)
        if text.strip() and "STALE since" not in text:
            lines = text.splitlines()
            insert = 1 if lines and lines[0].startswith("#") else 0
            lines.insert(insert, f"\nSTALE since {date.today().isoformat()}: {reason}. Ask Benji to refresh.\n")
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")


TASK_STATUSES = {"not_started", "in_progress", "blocked", "done", "skipped"}


def update_task(slug: str, task_id: str, status: str | None = None, owner: str | None = None,
                due: str | None = None, channel: str = "dashboard") -> dict:
    if status is not None and status not in TASK_STATUSES:
        raise MemoryError_(f"status must be one of {sorted(TASK_STATUSES)}")
    if due is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", due):
        raise MemoryError_("due must be YYYY-MM-DD")
    path = _place(slug) / "plan.md"
    lines = _read(path).splitlines()
    start = next((i for i, l in enumerate(lines) if l.strip() == "## Tasks"), None)
    if start is None:
        raise KeyError(task_id)
    header = None
    for i in range(start + 1, len(lines)):
        s = lines[i].strip()
        if not s.startswith("|"):
            if header:
                break
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        row = dict(zip(header, cells))
        if row.get("id") == task_id:
            for k, v in (("status", status), ("owner", owner), ("due", due)):
                if v is not None and k in header:
                    cells[header.index(k)] = _clean(v)
            lines[i] = "| " + " | ".join(cells) + " |"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            changed = ", ".join(f"{k}={v}" for k, v in (("status", status), ("owner", owner), ("due", due)) if v)
            append_log(slug, "benji-action-plan", channel, f"task {task_id}: {changed}")
            return {"task": task_id, "row": dict(zip(header, cells))}
    raise KeyError(task_id)


def answer_question(slug: str, qid: str, answer: str, channel: str = "dashboard") -> dict:
    path = _place(slug) / "open-questions.md"
    lines = _read(path).splitlines()
    header = None
    for i, l in enumerate(lines):
        s = l.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        if cells and cells[0] == qid and "answer" in header:
            cells[header.index("answer")] = f"{_clean(answer)} ({date.today().isoformat()})"
            lines[i] = "| " + " | ".join(cells) + " |"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            append_log(slug, "-", channel, f"answered {qid}")
            return {"question": qid, "answered": True}
    raise KeyError(qid)


# ---------------------------------------------------------------- deterministic cross-check
TYPE_MAP = {"home": "home", "small_business": "small_business", "office": "commercial_office",
            "apartment_building": "multifamily"}
ROLE_MAP = {"owner_occupant": "owner_occupant", "renter": "renter", "landlord": "landlord",
            "business_owns_space": "business_owner_owns_space", "business_tenant": "business_tenant",
            "manager": "property_manager"}
BIZ_MAP = {"store": "retail_store", "grocery": "grocery", "food_service": "food_service",
           "small_office": "small_office", "other": "other"}
FUEL_WORDS = [("heat pump", "heat_pump"), ("heat_pump", "heat_pump"), ("natural_gas", "natural_gas"),
              ("gas", "natural_gas"), ("oil", "oil"), ("propane", "propane"), ("steam", "district_steam"),
              ("electric", "electric_resistance")]


def _num(v):
    try:
        return float(str(v).replace("$", "").replace(",", "").split()[0])
    except (TypeError, ValueError, IndexError):
        return None


def cross_check(slug: str) -> dict:
    """Recompute costs, options and payback from the place's profile and CONFIRMED bills with Benji's tested engine.
    Stateless: nothing is stored. Returns the summary plus exactly which inputs were used or skipped."""
    from . import assistant
    from .store import Store

    r = read_place(slug)
    pv = lambda k: (r["profile"].get(k) or {}).get("value")
    used, skipped = {}, []
    ptype = TYPE_MAP.get((pv("place_type") or "").strip())
    if not ptype:
        return {"error": "profile.place_type missing or not one of " + ", ".join(TYPE_MAP)}
    prop = {"property_type": ptype, "name": pv("name") or slug}
    if (role := ROLE_MAP.get((pv("user_role") or "").strip())):
        prop["occupant_role"] = role
    if (biz := BIZ_MAP.get((pv("business_type") or "").strip())):
        prop["business_type"] = biz
    if pv("zip") and re.match(r"^\d{5}$", pv("zip")):
        prop["zip"] = pv("zip")
    heat = (pv("heating") or "").lower()
    fuel = next((f for w, f in FUEL_WORDS if w in heat), None)
    if fuel:
        prop["heating_fuel"] = fuel
    util = pv("utilities") or ""
    for name in ("Eversource", "National Grid", "Unitil", "Cape Light Compact"):
        if name.lower() in util.lower():
            prop["electric_utility"] = name
            break
    for k, field in (("floor_area_sqft", "floor_area_sqft"), ("cash_available_now_usd", "cash_available_usd"),
                     ("total_budget_usd", "budget_usd")):
        if (x := _num(pv(k))) is not None and x >= 0:
            prop[field] = x
    if (u := _num(pv("units_in_building"))):
        prop["dwelling_units"] = int(u)
    cover = (pv("bills_cover_whole_place") or "").lower()
    if cover in ("yes", "no"):
        prop["bills_cover_whole_building"] = cover == "yes"
    used["profile"] = prop
    bills = []
    for b in r["bills"]:
        if b.get("status") not in ("confirmed", "corrected"):
            continue
        fuel_b = {"electricity": "electricity", "electric": "electricity", "natural_gas": "natural_gas",
                  "gas": "natural_gas"}.get((b.get("fuel") or "").lower())
        unit = {"kwh": "kWh", "mwh": "MWh", "therm": "therms", "therms": "therms", "ccf": "ccf"}.get(
            (b.get("unit") or "").lower())
        q = _num(b.get("quantity"))
        if not (fuel_b and unit and q is not None and b.get("period_start") and b.get("period_end")):
            skipped.append({"bill_id": b.get("bill_id"), "reason": "fuel/unit/quantity/period missing or unsupported"})
            continue
        item = {"fuel": fuel_b, "period_start": b["period_start"], "period_end": b["period_end"], "quantity": q,
                "unit": unit, "account": b.get("account_last4") or None}
        if (t := _num(b.get("total_usd"))) is not None:
            item["total_usd"] = t
            if (f := _num(b.get("fixed_usd"))) is not None:
                item["fixed_charge_usd"] = f
        bills.append(item)
    s = Store(":memory:")
    try:
        pid = assistant.create_property(s, prop)["property_id"]
        res = assistant.add_bills(s, pid, bills, confirmed=True) if bills else {"errors": []}
        summary = assistant.analyze(s, pid)
    except assistant.AssistantError as exc:
        return {"error": "invalid_input", "fields": exc.errors, "inputs_used": used}
    analysis = s.get_analysis(pid)
    measures = analysis["results"].get("10", {}).get("outputs", {}).get("measures", [])
    costs = analysis["results"].get("09", {}).get("outputs", {}).get("fuels", {})
    return {
        "inputs_used": {**used, "confirmed_bills": len(bills)}, "skipped": skipped + res.get("errors", []),
        "costs": {f: {k: v.get(k) for k in ("recorded_quantity", "unit", "recorded_cost_usd", "usage_based_rate",
                                             "annual_quantity", "annual_cost_usd", "coverage", "heating_split")}
                  for f, v in costs.items()},
        "benchmark": analysis["results"].get("07", {}).get("message"),
        "options": [{k: m.get(k) for k in ("measure_id", "name", "status", "missing", "annual_energy_change",
                                           "annual_operating_cost_change_usd", "annual_emissions_change_kgco2e")}
                    for m in measures if m.get("applicable")],
        "programs": summary["programs_to_check"],
        "what_to_do_first": summary["what_to_do_first"],
        "note": "Deterministic cross-check of the agent's numbers. Quotes and incentive approvals are not read from "
                "memory files; LED and heat-pump estimates need their inputs passed via the calculator API.",
    }

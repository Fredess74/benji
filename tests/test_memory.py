"""File memory: the shared record that agents write and the dashboard manages."""

import asyncio
import json
from pathlib import Path

import pytest

GAS = [2.1, 1.9, 1.55, 0.95, 0.45, 0.2, 0.15, 0.15, 0.25, 0.7, 1.35, 1.95]

PROFILE = """---
name: Test Cafe  # source: user, 2026-10-24
place_type: small_business  # source: user, 2026-10-24
business_type: food_service
user_role: business_tenant
zip: 02139
utilities: electric: Eversource; gas: Eversource
bills_cover_whole_place: yes
floor_area_sqft: 1400
heating: gas furnace, landlord's, efficiency unknown
cash_available_now_usd: 1500
---
# Notes
"""

PLAN = """# Plan - Test Cafe

## Next step
Tonight at closing set the thermostat to 60 F.

## Actions
| # | Action | Why now | Cash now | Est. effect / yr | Approves |
|---|---|---|---|---|---|
| 1 | Closing routine | free | $0 | unknown | you |

## Tasks
| id | Task | Owner | Due | Status |
|---|---|---|---|---|
| T1 | Closing routine | owner | 2026-10-25 | not_started |
| T2 | Book assessment | owner | 2026-10-28 | not_started |
"""

QUESTIONS = """# Open questions

| id | Question | Why it matters | Who can answer | Asked | Answer |
|---|---|---|---|---|---|
| Q1 | Is the thermostat programmable? | set-back cost | owner | 2026-10-24 | |
"""


def bills_csv(status="pending"):
    head = ("bill_id,fuel,utility,account_last4,period_start,period_end,days,quantity,unit,total_usd,fixed_usd,"
            "usage_usd,demand_usd,demand_kw,credits_usd,estimated_read,source,status,confirmed_by,confirmed_on,notes")
    rows = [head]
    months = [(2025, m) for m in (10, 11, 12)] + [(2026, m) for m in range(1, 10)]
    for i, (y, m) in enumerate(months):
        y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        s, e = f"{y}-{m:02d}-01", f"{y2}-{m2:02d}-01"
        rows.append(f"E{i},electricity,Eversource,1234,{s},{e},,4000,kWh,1105,25,,,,,no,typed,{status},,,")
        th = round(30 + 60 * GAS[m - 1])
        rows.append(f"G{i},natural_gas,Eversource,5678,{s},{e},,{th},therms,{20 + th * 1.75:.2f},20,,,,,no,typed,{status},,,")
    return "\n".join(rows) + "\n"


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setenv("BENJI_MEMORY", str(tmp_path / "benji-memory"))
    from benji import memory
    memory.create_place("test-cafe", "Test Cafe", "claude")
    memory.write_file("test-cafe", "profile.md", PROFILE, "claude", "benji-profile")
    memory.write_file("test-cafe", "bills.csv", bills_csv(), "claude", "benji-bills-import")
    memory.write_file("test-cafe", "plan.md", PLAN, "claude", "benji-action-plan")
    memory.write_file("test-cafe", "open-questions.md", QUESTIONS, "claude", "benji-profile")
    return memory


def test_read_and_list(mem):
    r = mem.read_place("test-cafe")
    assert r["profile"]["place_type"]["value"] == "small_business"
    assert r["next_step"].startswith("Tonight")
    assert [t["id"] for t in r["tasks"]] == ["T1", "T2"]
    assert r["bills_pending"] == 24 and len(r["open_questions"]) == 1
    assert r["log"][0]["channel"] == "claude"
    lst = mem.list_places()[0]
    assert (lst["name"], lst["open_tasks"], lst["bills_pending"]) == ("Test Cafe", 2, 24)


def test_confirm_marks_plan_stale_and_logs(mem):
    assert mem.confirm_bills("test-cafe", None, "owner", "dashboard")["confirmed"] == 24
    r = mem.read_place("test-cafe")
    assert r["bills_pending"] == 0 and r["plan_stale"]
    assert r["log"][-1]["channel"] == "dashboard" and "confirmed" in r["log"][-1]["what"]


def test_task_and_question_updates(mem):
    mem.update_task("test-cafe", "T1", status="done")
    assert mem.read_place("test-cafe")["tasks"][0]["Status"] == "done"
    with pytest.raises(mem.MemoryError_):
        mem.update_task("test-cafe", "T1", status="finished")
    mem.answer_question("test-cafe", "Q1", "yes")
    assert mem.read_place("test-cafe")["open_questions"] == []


def test_path_safety(mem):
    for bad in ("../x", "A", "x/y"):
        with pytest.raises((mem.MemoryError_, KeyError)):
            mem.read_place(bad)
    with pytest.raises(mem.MemoryError_):
        mem.write_file("test-cafe", "../../evil.md", "x")
    with pytest.raises(mem.MemoryError_):
        mem.write_file("test-cafe", "log.md", "rewrite history")


def test_cross_check_uses_only_confirmed_bills(mem):
    r = mem.cross_check("test-cafe")
    assert r["inputs_used"]["confirmed_bills"] == 0
    mem.confirm_bills("test-cafe", None, "owner")
    r = mem.cross_check("test-cafe")
    e = r["costs"]["electricity"]
    assert e["recorded_quantity"] == 48000 and e["recorded_cost_usd"] == 13260 and e["usage_based_rate"] == 0.27
    assert r["what_to_do_first"][0]["action"] == "Review operating schedules and controls"
    assert not any("multifamily" in p["program"].lower() for p in r["programs"])


def test_http_memory_api(client, mem):
    assert client.get("/memory/places").json()[0]["slug"] == "test-cafe"
    d = client.get("/memory/places/test-cafe").json()
    assert d["bills_pending"] == 24
    assert client.post("/memory/places/test-cafe/bills/confirm", json={}).json()["confirmed"] == 24
    assert client.patch("/memory/places/test-cafe/tasks/T2", json={"status": "in_progress"}).status_code == 200
    assert client.patch("/memory/places/test-cafe/tasks/T9", json={"status": "done"}).status_code == 404
    assert client.put("/memory/places/test-cafe/files/..%2Fx.md", json={"content": "x"}).status_code in (404, 422)
    assert "costs" in client.get("/memory/places/test-cafe/cross-check").json()
    spec = client.get("/assistant/openapi.json").json()
    assert all(p.startswith("/memory/") for p in spec["paths"]) and "/memory/places/{slug}" in spec["paths"]


def test_dashboard_page_and_memory_info(client, mem):
    assert client.get("/app").status_code == 200
    info = client.get("/memory/info").json()
    assert info["root"].endswith("benji-memory") and "plan.md" in info["files"]


def test_demo_loader_marks_everything_as_demo(tmp_path, monkeypatch):
    import importlib.util
    monkeypatch.setenv("BENJI_MEMORY", str(tmp_path / "benji-memory"))
    spec = importlib.util.spec_from_file_location("load_demo", Path(__file__).resolve().parent.parent / "scripts" / "load_demo.py")
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    demo.load()
    from benji import memory
    r = memory.read_place(demo.SLUG)
    assert all("DEMO DATA" in r["raw"][f] for f in ("profile.md", "bills.csv", "findings.md", "plan.md", "open-questions.md"))
    assert r["bills_pending"] == 2 and any(t["Owner"] == "openclaw" for t in r["tasks"])
    assert set(memory.cross_check(demo.SLUG)["costs"]) == {"electricity", "natural_gas"}
    with pytest.raises(SystemExit):
        demo.load()
    demo.load(reset=True)


def test_mcp_tools(mem):
    from fastmcp import Client

    from benji import mcp_server

    async def go():
        async with Client(mcp_server.mcp) as c:
            names = {t.name for t in await c.list_tools()}
            assert {"list_places", "read_place", "create_place", "write_file", "append_log", "confirm_bills",
                    "update_task", "cross_check", "room_heating_scenario"} <= names
            out = json.loads((await c.call_tool("read_place", {"slug": "test-cafe"})).content[0].text)
            assert out["bills_pending"] == 24
            out = json.loads((await c.call_tool("read_place", {"slug": "nope"})).content[0].text)
            assert out["error"] == "not_found"

    asyncio.run(go())

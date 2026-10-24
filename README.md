# Benji — AI energy & sustainability manager for buildings

**Benji turns your energy bills into a plan you can act on — inside the AI assistant you already use.**

For Massachusetts residents (owners, renters, small landlords), small businesses (stores, coffee shops,
restaurants, offices) and building owners. You talk to Claude, ChatGPT or an OpenClaw business agent; Benji's skills
make it act like a careful energy manager: it reads your bills, finds what's unusual, tells you **what to do first,
what it costs you now, which programs may help and who has to approve it** — and follows up month after month.

Hackachusetts 2026 · Climate Tech: cleaner, more affordable buildings. Why it matters: [docs/POSITIONING.md](docs/POSITIONING.md).

## What's in the box
| Part | What it is |
|---|---|
| [`skills/`](skills/) | **The product.** 12 agent skills + `benji-orchestrator` (Markdown `SKILL.md`), shared rules, formulas, measure library, and data references (Boston BERDO peers, Mass Save program leads, emission factors). |
| `benji-memory/` | **Consistent memory.** One folder per place — profile, bills, findings, plan + tasks, open questions, activity log. Agents write it; people and the dashboard read and manage it. Created on first use, never committed. |
| [`benji/`](benji/) | Optional tool server: MCP (`python -m benji.mcp_server`) and HTTP API with memory tools and a deterministic **cross-check** calculator (tested). |
| Dashboard | The management view over memory — being designed separately; brief: [docs/DASHBOARD_BRIEF.md](docs/DASHBOARD_BRIEF.md). |

## Skills
| Skill | Covers |
|---|---|
| `benji-orchestrator` | Entry point: routing, gates, short answers, memory discipline |
| `benji-profile` | Place type, role, who pays / approves, utilities, equipment, cash now |
| `benji-bills-import` | PDFs, photos, CSV, usage exports, delivery tickets → read-back → confirmed; data-quality check |
| `benji-bill-explainer` | Charges, why a bill changed, yearly cost per fuel, fixed share, heating share, budget |
| `benji-usage-patterns` | Jumps vs last year; night / after-closing use (interval data or walk-through) |
| `benji-benchmark` | BERDO peer comparison only when fair |
| `benji-comfort` | Cold rooms, drafts, warm-up time, system capacity, heat loss |
| `benji-upgrade-options` | Options, cash now, net cost, payback, emissions, new equipment, electrical check |
| `benji-programs` | Mass Save & other programs: find, check eligibility, prepare applications |
| `benji-funding` | Rebate vs discount vs 0% loan vs tax; cash gap and phasing |
| `benji-action-plan` | Ordered plan, tasks, next step, landlord and contractor drafts |
| `benji-follow-up` | Monthly check-ins, reminders, "did it work?" (measured vs estimated) |
| `benji-report` | Reports for owner, landlord, board, lender, contractor |

These cover all 20 originally planned capabilities (e.g. after-hours + unusual use → `benji-usage-patterns`;
alerts + measuring results → `benji-follow-up`; incentives + eligibility + applications → `benji-programs`).

## Use it
**Claude Code plugin (skills + MCP in one install):** this repo is a plugin marketplace. Needs Python 3.11+ with
`pip install -r requirements.txt` (the MCP server runs `python -m benji.mcp_server`).
```
/plugin marketplace add VladimirPutkov/benji
/plugin install benji@benji
```
You get the 13 skills (`/benji:benji-orchestrator` …) and the `benji` MCP server. Memory goes to `~/benji-memory`
(or `BENJI_MEMORY`); to see it in the dashboard, start the server with the same `BENJI_MEMORY`.

**Claude Code / OpenClaw / Kiro (file access):** copy `skills/` into the agent's skills folder (e.g.
`.claude/skills/`). Memory goes to `./benji-memory/`.

**Claude Desktop / Claude.ai:** `python scripts/package_skills.py` → upload the zips in `dist/skills/` (each zip
contains the shared files). For persistent memory, also add the MCP server:
```json
{"mcpServers": {"benji": {"command": "python", "args": ["-m", "benji.mcp_server"], "cwd": "<path to this repo>"}}}
```

**ChatGPT (custom GPT):** instructions + knowledge files in [integrations/chatgpt/](integrations/chatgpt/); memory via
Actions on `/memory/*` (needs a public HTTPS URL and `BENJI_API_KEY`).

Then just say: *"I run a coffee shop in Cambridge, we lease. Our bills keep going up — here are the last 12."*

## Tool server (optional)
```bash
pip install -r requirements.txt
python -m uvicorn benji.api:app --host 127.0.0.1 --port 8000     # HTTP: /memory/* and /docs
python -m benji.mcp_server                                       # MCP for Claude
```
No login on the HTTP server: keep it on 127.0.0.1; set `BENJI_API_KEY` before exposing `/memory/*` via a tunnel.
Memory location: `BENJI_MEMORY` (default `./benji-memory`).

## Quality
`python -m pytest -q tests` — 172 tests: skill files (front matter, sections, references, routing), memory and its
API/MCP, the calculator (cost arithmetic, money rules, 12 acceptance checks, audit regressions, property-based
tests), a 63-case sweep across property types and bill situations. The skills were also dry-run by an agent on two
scenarios (a leased coffee shop; a renter with a cold bedroom, an estimated meter read, a blurry digit and a
prompt-injection line in a photo); the fixes from that run are in this version.

More: [docs/SOURCES.md](docs/SOURCES.md) · [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) · [docs/KIRO.md](docs/KIRO.md) ·
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)

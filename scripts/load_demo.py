"""Load one example place into Benji memory for demos and judging. EVERYTHING IT WRITES IS INVENTED DEMO DATA.

The place is "demo-corner-coffee": a leased coffee shop in Cambridge, MA with 12 months of confirmed electricity and
gas bills, 2 newer bills waiting for confirmation, findings, a plan with tasks (one assigned to OpenClaw) and an open
question. Every file says DEMO DATA; the dashboard shows a demo banner for it.

Run:  python scripts/load_demo.py            (uses BENJI_MEMORY, default ./benji-memory)
      python scripts/load_demo.py --reset    (delete the demo place first)
"""

from __future__ import annotations

import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from benji import memory  # noqa: E402

SLUG, NAME = "demo-corner-coffee", "Corner Coffee (DEMO)"
TAG = "DEMO DATA (invented)"
BANNER = "> DEMO DATA — invented example place for the Benji presentation. Not a real business or real bills.\n"

PROFILE = f"""---
name: {NAME}  # {TAG}
place_type: small_business  # {TAG}
business_type: food_service  # {TAG}
user_role: business_tenant  # {TAG}
zip: 02139  # {TAG}
utilities: electric: Eversource; gas: National Grid  # {TAG}
bills_cover_whole_place: yes  # {TAG}
floor_area_sqft: 1200  # {TAG}
hours: 6:30-18:00 daily  # {TAG}
heating: natural gas furnace, landlord's, age unknown  # {TAG}
who_pays_now: tenant pays electricity and gas  # {TAG}
who_approves: landlord for fixtures and building work (unverified)  # {TAG}
cash_available_now_usd: 1500  # {TAG}
goals: lower bills  # {TAG}
check_in: OpenClaw, monthly  # {TAG}
---
# Notes
{BANNER}"""

# (kWh, therms) per month, Sep 2025 .. Aug 2026 — invented, shaped like a small cafe (summer cooling, winter heat)
MONTHS = [(2025, 9, 3900, 60), (2025, 10, 3700, 120), (2025, 11, 3800, 210), (2025, 12, 4000, 310),
          (2026, 1, 3900, 360), (2026, 2, 3600, 330), (2026, 3, 3700, 250), (2026, 4, 3800, 150),
          (2026, 5, 4200, 90), (2026, 6, 4700, 55), (2026, 7, 5000, 50), (2026, 8, 4900, 50)]
HEAD = ("bill_id,fuel,utility,account_last4,period_start,period_end,days,quantity,unit,total_usd,fixed_usd,usage_usd,"
        "demand_usd,demand_kw,credits_usd,estimated_read,source,status,confirmed_by,confirmed_on,notes")


def _bills() -> str:
    rows = [HEAD]

    def add(i, y, m, kwh, th, status, by, gas_note=""):
        y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        s, e = date(y, m, 1), date(y2, m2, 1)
        days, on = (e - s).days, "2026-10-03" if by else ""
        e_usage, g_usage = round(kwh * 0.29, 2), round(th * 1.85, 2)
        rows.append(f"E{i:02d},electricity,Eversource,0000,{s},{e},{days},{kwh},kWh,{e_usage + 28:.2f},28.00,"
                    f"{e_usage:.2f},,,,no,demo,{status},{by},{on},{TAG}")
        rows.append(f"G{i:02d},natural_gas,National Grid,0000,{s},{e},{days},{th},therms,{g_usage + 18:.2f},18.00,"
                    f"{g_usage:.2f},,,,no,demo,{status},{by},{on},{TAG}{gas_note}")

    for i, (y, m, kwh, th) in enumerate(MONTHS, 1):
        add(i, y, m, kwh, th, "confirmed", "owner")
    add(13, 2026, 9, 4300, 65, "pending", "", " - one digit unclear on the photo")
    return "\n".join(rows) + "\n"


FINDINGS = f"""# Findings — {NAME}
{BANNER}
## F-001 Summer electricity is higher; investigate cooling (2026-10-03, benji-bill-explainer)
- What: Jun-Aug monthly electricity averages about 32% above Feb-Apr. Cooling is a hypothesis, not a proven cause; not weather-adjusted.
- Evidence: E10-E12 vs E06-E08 — from your bills ({TAG})
- Leads to: closing routine, cooling settings

## F-002 Winter gas suggests a heating-related increase (2026-10-03, benji-bill-explainer)
- What: monthly gas use in Dec-Feb averages about 6.5x Jun-Aug. Heating is a hypothesis; cooking, hot water and operating changes also need checking.
- Evidence: G04-G06 vs G10-G12 — from your bills ({TAG})

## F-003 Some equipment may run after closing (2026-10-03, benji-usage-patterns)
- What: monthly bills cannot show night use; a closing walk-through can.
- Evidence: none yet — unverified
- Leads to: T1

## F-004 No fair peer comparison (2026-10-03, benji-benchmark)
- What: too few similar small food-service places in Boston BERDO data to compare fairly.
"""

PLAN = f"""# Plan — {NAME}
{BANNER}
Updated 2026-10-03 from findings F-001..F-004 (bills through 2026-08).

## Next step
Tonight at closing, walk through and write down what is still running: lights, fridges, espresso machine, water heater.
Observe only; keep refrigeration, ventilation, hot-water safety and freeze protection running as required.

## Actions
| # | Action | Why now | Cash now | Est. effect / yr | Approves |
|---|---|---|---|---|---|
| 1 | Check nonessential after-hours loads | start with an observation | $0 for the walk-through | estimate after confirming loads | you |
| 2 | Check Mass Save small-business assessment eligibility | verify the right support route before quotes | confirm program terms | assessment only | account holder / provider |
| 3 | LED lighting | lights on 11+ hours a day | [quote needed] | estimate after assessment | landlord |

## Tasks
| id | Task | Owner | Due | Status |
|---|---|---|---|---|
| T1 | Closing-time walk-through | you | 2026-10-25 | in_progress |
| T2 | Check assessment eligibility and terms with the provider | you | 2026-11-07 | not_started |
| T3 | Draft the landlord note about LED fixtures | openclaw | 2026-11-01 | not_started |

## Not now, and why
- Heat pump: landlord's equipment; revisit after the assessment.

Effects are estimates until measured (benji-follow-up).
"""

QUESTIONS = f"""# Open questions
{BANNER}
| id | Question | Why it matters | Who can answer | Asked | Answer |
|---|---|---|---|---|---|
| Q1 | Who approves changes to light fixtures — you or your landlord? | needed before the LED step | you / lease | 2026-10-23 | |
"""


def load(reset: bool = False) -> str:
    place = memory.root() / SLUG
    if place.exists():
        if not reset:
            raise SystemExit(f"{SLUG} already exists in {memory.root()} - run with --reset to reload it")
        shutil.rmtree(place)
    memory.create_place(SLUG, NAME, "agent")
    for name, text in (("profile.md", PROFILE), ("bills.csv", _bills()), ("findings.md", FINDINGS),
                       ("plan.md", PLAN), ("open-questions.md", QUESTIONS)):
        memory.write_file(SLUG, name, text, "agent", "demo-loader")
    memory.append_log(SLUG, "demo-loader", "agent", "DEMO DATA loaded: invented example place, not real bills")
    return str(place)


if __name__ == "__main__":
    print("Loaded demo place (invented data):", load(reset="--reset" in sys.argv))

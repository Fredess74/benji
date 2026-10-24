"""20 Generate Energy Performance Reports (Markdown + HTML).

Estimates and measured outcomes are separated; synthetic data is labelled at the top
and on every section that uses it. Saved exports are immutable dated snapshots (store.reports).
"""

from __future__ import annotations

import html
import re

from .base import COMPLETED, NEEDS_DATA, SkillContext, SkillResult

LABEL_TEXT = {
    "user_provided": "User-provided", "public_historical": "Public historical data", "assumption": "Assumption",
    "modelled_estimate": "Modelled estimate", "synthetic_demo": "SYNTHETIC DEMONSTRATION DATA",
    "measured_post_action": "Measured post-action result",
}


def _usd(x):
    return "n/a" if x is None else f"${x:,.0f}"


def _num(x, unit=""):
    return "n/a" if x is None else f"{x:,.0f}{(' ' + unit) if unit else ''}"


def _signed(x, unit=""):
    return "n/a" if x is None else f"{x:+,.0f}{unit}"


def render_markdown(building: dict, results: dict, plan: dict | None, generated_at: str,
                    decision_ready: bool = True, not_ready_reasons: list | None = None,
                    stale_message: str | None = None, thermal: list | None = None) -> str:
    synthetic = building.get("data_label") == "synthetic_demo"
    L = []
    if synthetic:
        L += ["> **SYNTHETIC DEMONSTRATION DATA.** This building, its bills and quotes are invented for demonstration. "
              "Nothing in this report describes a real property.", ""]
    if not decision_ready:
        L += ["> **DIAGNOSTIC REPORT - NOT DECISION-READY.** " + " ".join(not_ready_reasons or []) +
              " Financial and benchmark conclusions are suppressed until the data is fixed.", ""]
    if stale_message:
        L += [f"> **OUT OF DATE.** {stale_message}", ""]
    L += [f"# Benji energy report: {building.get('name')}", "",
          f"Generated {generated_at}. Category: {building.get('category', '').replace('_', ' ')}. "
          f"Floor area: {_num(building.get('gross_floor_area_sqft'), 'sq ft')}. "
          f"Budget: {_usd(building.get('budget_usd'))}. Data label: {LABEL_TEXT.get(building.get('data_label'), 'User-provided')}.", "",
          "All savings, costs and emissions changes below are **estimates**. Final incentive eligibility is decided by "
          "the program operator.", ""]

    L += ["## Skills used", "", "| Skill | Status | Summary |", "|---|---|---|"]
    for sid, r in sorted(results.items()):
        L.append(f"| {sid} | {r['status']} | {r['message'].replace('|', '/')} |")
    L.append("")

    q = results.get("03")
    if q and q["status"] == COMPLETED:
        L += ["## Data quality", ""]
        issues = q["outputs"]["issues"]
        L += [f"- **{i['severity']}** {i['message']} Fix: {i['correction_action']}" for i in issues] or ["- No issues found."]
        L.append("")

    c = results.get("09")
    if c and c["status"] == COMPLETED:
        L += ["## Recorded consumption and cost", "", "| Fuel | Period | Quantity | Cost | Fixed | Usage-based | Usage rate |",
              "|---|---|---|---|---|---|---|"]
        for f, s in c["outputs"]["fuels"].items():
            cov = s["coverage"]
            rate = "n/a" if s["usage_based_rate"] is None else f"${s['usage_based_rate']:.4f}/{s['unit']}"
            L.append(f"| {f} | {cov['window_start']} to {cov['window_end']} ({cov['covered_days']} days) | "
                     f"{_num(s['recorded_quantity'], s['unit'])} | {_usd(s['recorded_cost_usd'])} | "
                     f"{_usd(s['charges_usd']['fixed'])} | {_usd(s['charges_usd']['variable'])} | {rate} |")
        L += [""] + [f"- {a['text']}" for a in c["assumptions"]] + [""]

    a = results.get("06")
    if a and a["status"] == COMPLETED:
        L += ["## Unusual consumption (own history, not weather-normalised)", ""]
        L += [f"- {x['period'][0]} to {x['period'][1]}: {x['explanation']}" for x in a["outputs"]["anomalies"]] or \
             ["- No period changed by more than the threshold."]
        L.append("")

    bm = results.get("07")
    if bm and bm["status"] in (COMPLETED, NEEDS_DATA):
        L += [f"## Peer comparison (BERDO reporting year {bm['outputs'].get('source', {}).get('reporting_year', 'n/a')})", "",
              bm["message"], ""]
        if bm["outputs"].get("why_this_comparison"):
            L += [f"Why this comparison: {bm['outputs']['why_this_comparison']}", ""]
        L += [f"- {x}" for x in bm["outputs"].get("limitations", [])] + [""]

    s = results.get("10")
    if s and s["status"] == COMPLETED:
        L += ["## Improvement options (modelled estimates)", "",
              "| Measure | Status | Energy change / yr | Operating cost change / yr | Emissions change kgCO2e/yr | Quote | Net cost (confirmed) | Upfront cash (confirmed) | Simple payback |",
              "|---|---|---|---|---|---|---|---|---|"]
        for m in s["outputs"]["measures"]:
            if not m["applicable"]:
                L.append(f"| {m['name']} | not applicable | {'; '.join(m['reasons'])} | | | | | | |")
                continue
            e = m["annual_energy_change"]
            fin = m["financials"]["confirmed"]
            pb = fin["payback"]["years"]
            chg = m["annual_operating_cost_change_usd"]
            chg_s = "n/a" if chg is None else (f"+${chg:,.0f} (INCREASE)" if chg > 0 else f"-${-chg:,.0f}")
            energy_s = ("not estimated" if m["status"] != "estimated" else
                        f"{e['electricity_kwh']:+,.0f} kWh, {e['natural_gas_therms']:+,.0f} therms")
            L.append(f"| {m['name']} | {m['status']} | {energy_s} | "
                     f"{chg_s} | {_signed(m['annual_emissions_change_kgco2e'])} | {_usd(m['quoted_cost_usd'])} | "
                     f"{_usd(fin['net_cost_usd'])} | {_usd(fin['upfront_cash_required_usd'])} | "
                     f"{'n/a - ' + fin['payback']['reason'] if pb is None else f'{pb} yr'} |")
        L += ["", "### Scenarios", "", "| Scenario | Measures | Operating cost change / yr | Emissions change | Net cost confirmed | Net cost hypothetical | Upfront cash confirmed |",
              "|---|---|---|---|---|---|---|"]
        for sc in s["outputs"]["scenarios"]:
            chg = sc["annual_operating_cost_change_usd"]
            L.append(f"| {sc['scenario']} | {', '.join(sc['measures'])} | {'n/a' if chg is None else f'{chg:+,.0f} USD'} | "
                     f"{_signed(sc['annual_emissions_change_kgco2e'], ' kg')} | {_usd(sc['financials']['confirmed']['net_cost_usd'])} | "
                     f"{_usd(sc['financials']['hypothetical']['net_cost_usd'])} (hypothetical) | "
                     f"{_usd(sc['financials']['confirmed']['upfront_cash_required_usd'])}"
                     + (f" (excludes unpriced: {', '.join(sc['unpriced_assessments'])})" if sc["unpriced_assessments"] else "")
                     + " |")
        L += ["", s["outputs"]["payback_note"], ""]

    e = results.get("14")
    if e and e["status"] == COMPLETED:
        L += ["## Potential incentives", "", "| Program | Type | Timing | Eligibility | Source verification | Source |", "|---|---|---|---|---|---|"]
        for r in e["outputs"]["results"]:
            L.append(f"| {r['name']} | {r['incentive_type']} | {r['timing']} | {r['status']} | "
                     f"{r['verification_status']}{' ' + r['verified_on'] if r['verified_on'] else ''} | {r['source_url']} |")
        L += ["", "Final eligibility and amounts are determined by the program operator. Rebates paid after installation "
              "do not reduce the cash needed upfront. Loans must be repaid.", ""]

    if plan:
        L += ["## Action plan", "", f"Next action: **{plan.get('next_action')}**", ""]
        for r in plan["recommendations"]:
            cb = r.get("costs_benefits", {})
            L += [f"### {r['priority']}. {r['title']}", "",
                  f"- Why this position: {r['rank_reason']}",
                  f"- Issue: {r.get('issue')}",
                  f"- Evidence: {', '.join(r['evidence']) or 'none'}",
                  f"- Unknowns: {'; '.join(r['unknowns']) or 'none recorded'}",
                  f"- Action: {r['action']}",
                  (f"- Estimated annual operating cost INCREASE: {_usd(-cb['annual_operating_savings_usd'])}; "
                   if (cb.get("annual_operating_savings_usd") or 0) < 0 else
                   f"- Estimated annual operating savings: {_usd(cb.get('annual_operating_savings_usd'))}; ") +
                  f"emissions change: {_num(cb.get('annual_emissions_change_kgco2e'), 'kgCO2e/yr')}",
                  f"- Cost: gross {_usd(cb.get('gross_cost_usd'))}, net (confirmed incentives) {_usd(cb.get('net_cost_confirmed_usd'))}, "
                  f"upfront cash {_usd(cb.get('upfront_cash_confirmed_usd'))}, funding gap "
                  f"{_usd(cb.get('funding_gap_usd')) if cb.get('upfront_cash_feasible') is not None else 'unknown (cash on hand not entered)'}",
                  f"- Incentives: {'; '.join(i['name'] + ' (' + i['eligibility_status'] + ', ' + i['verification_status'] + ')' for i in r['incentives']) or 'none found'}",
                  f"- Who pays: {r['roles']['pays_upfront']}; who benefits: {r['roles']['receives_operating_savings']}; "
                  f"who authorizes: {r['roles']['authorizes']}" + (f". {r['roles']['note']}" if r['roles'].get('note') else ""),
                  f"- Next step: {r['next_step']}", ""]
        L += ["### Tasks", "", "| Task | Owner | Due | Status | Prerequisites |", "|---|---|---|---|---|"]
        L += [f"| {t['title']} | {t['owner']} | {t['due_date']} | {t['status']} | {', '.join(t['prerequisites'])} |"
              for t in plan["tasks"]]
        L.append("")

    thermal = thermal if thermal is not None else (results.get("08", {}).get("outputs", {}) or {}).get("scenarios")
    if thermal:
        L += ["## Room heating & cooling scenarios (modelled estimates, single zone)", "",
              "| Room scenario | Option | Status | Time to target (h) | Delivered heat/cool (kWh thermal) | "
              "Purchased energy | Variable cost (USD) | Capacity headroom (kW) |", "|---|---|---|---|---|---|---|---|"]
        for row in thermal:
            for sc in row.get("scenarios", []):
                ce = sc.get("consumed_energy")
                L.append(f"| {row.get('name')} | {sc.get('name')} | {sc.get('status')} | "
                         f"{sc.get('time_to_target_h', 'n/a')} | {sc.get('delivered_thermal_kwh', 'n/a')} | "
                         f"{'n/a' if not ce else str(ce['quantity']) + ' ' + ce['unit'] + ' ' + ce['carrier']} | "
                         f"{sc.get('variable_energy_cost_usd') if sc.get('variable_energy_cost_usd') is not None else 'n/a'} | "
                         f"{sc.get('capacity_headroom_kw', 'n/a')} |")
            cur = (row.get("scenarios") or [{}])[0]
            L += [""] + [f"- [{a['data_label']}] {a['text']}" for a in cur.get("assumptions", [])]
            L += [f"- Missing: {m['message']}" for m in cur.get("missing", [])]
        lims = thermal[0].get("limitations") or ((thermal[0].get("scenarios") or [{}])[0].get("limitations")) or []
        L += [""] + [f"- Limitation: {x}" for x in lims] + [""]

    L += ["## Measured results after action", "", "None recorded. No savings in this report have been measured.", ""]
    L += ["## Assumptions and sources", ""]
    seen = set()
    for r in results.values():
        for a in r.get("assumptions", []):
            key = a.get("text")
            if key and key not in seen:
                seen.add(key)
                L.append(f"- [{LABEL_TEXT.get(a.get('data_label'), a.get('data_label'))}] {a['text']}"
                         + (f" Source: {a['source_url']} ({a.get('verification_status')})" if a.get("source_url") else ""))
    if synthetic:
        L += ["", "> SYNTHETIC DEMONSTRATION DATA - not a real building."]
    return "\n".join(L) + "\n"


def markdown_to_html(md: str, title: str) -> str:
    out, in_table, in_list = [], False, False
    for line in md.splitlines():
        esc = html.escape(line)
        esc = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc)
        if line.startswith("|"):
            cells = [c.strip() for c in esc.strip("|").split("|")]
            if set("".join(cells)) <= set("-"):
                continue
            if not in_table:
                out.append("<table>")
                in_table = True
                out.append("<tr>" + "".join(f"<th scope='col'>{c}</th>" for c in cells) + "</tr>")
            else:
                out.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
            continue
        if in_table:
            out.append("</table>")
            in_table = False
        if line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{esc[2:]}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        if line.startswith("### "):
            out.append(f"<h3>{esc[4:]}</h3>")
        elif line.startswith("## "):
            out.append(f"<h2>{esc[3:]}</h2>")
        elif line.startswith("# "):
            out.append(f"<h1>{esc[2:]}</h1>")
        elif line.startswith("&gt; "):
            out.append(f"<p class='banner' role='note'>{esc[5:]}</p>")
        elif line.strip():
            out.append(f"<p>{esc}</p>")
    if in_table:
        out.append("</table>")
    if in_list:
        out.append("</ul>")
    style = ("body{font-family:system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;line-height:1.5;color:#1a1a1a}"
             "table{border-collapse:collapse;width:100%;margin:1rem 0;font-size:.9rem}th,td{border:1px solid #bbb;padding:.35rem;text-align:left;vertical-align:top}"
             "th{background:#eef2f5}.banner{background:#fff3cd;border:2px solid #8a6d00;padding:.75rem;font-weight:600}")
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
            f"<title>{html.escape(title)}</title><style>{style}</style></head><body>" + "\n".join(out) + "</body></html>")


def run(ctx: SkillContext) -> SkillResult:
    res = SkillResult("20", COMPLETED)
    if not ctx.results:
        res.status = NEEDS_DATA
        res.message = "Run analysis skills first."
        return res
    plan = ctx.result("17").outputs["plan"] if ctx.result("17") else None
    results = {k: v.to_dict() for k, v in ctx.results.items()}
    from ..engine import decision_ready  # local import: engine imports the registry
    ready, reasons = decision_ready(results)
    md = render_markdown(ctx.building, results, plan, ctx.settings.get("generated_at", ""),
                         decision_ready=ready, not_ready_reasons=reasons)
    res.outputs = {"markdown": md, "synthetic": ctx.building.get("data_label") == "synthetic_demo",
                   "decision_ready": ready, "not_decision_ready_reasons": reasons}
    if not ready:
        res.warnings.append("Diagnostic report only: " + " ".join(reasons))
    res.message = "Report ready for export." + (" Contains synthetic demonstration data." if res.outputs["synthetic"] else "")
    return res

"""Deterministic financial arithmetic. No market assumptions live here."""

from __future__ import annotations

UPFRONT_REDUCING_TIMINGS = {"at_purchase", "before_installation"}


def simple_payback(net_cost: float | None, annual_savings: float | None) -> dict:
    """Simple payback in years = net cost / annual operating savings.

    Simplified metric: ignores financing cost, inflation, maintenance and equipment life.
    Returns no payback when savings are zero or negative.
    """
    if net_cost is None:
        return {"years": None, "reason": "Cost unknown - request a contractor quote."}
    if annual_savings is None:
        return {"years": None, "reason": "Annual savings could not be estimated."}
    if annual_savings <= 0:
        return {"years": None, "reason": "No payback: estimated annual operating cost does not decrease."}
    if net_cost <= 0:
        return {"years": 0.0, "reason": "Net cost is zero or negative after incentives."}
    return {"years": round(net_cost / annual_savings, 1), "reason": "Simple payback (simplified metric)."}


def apply_stacking(incentives: list[dict]) -> tuple[list[dict], list[dict]]:
    """Within a stacking group only the largest amount counts. Returns (counted, excluded)."""
    counted, excluded, best = [], [], {}
    for inc in incentives:
        g = inc.get("stacking_group")
        if not g:
            counted.append(inc)
            continue
        cur = best.get(g)
        if cur is None or (inc.get("amount_usd") or 0) > (cur.get("amount_usd") or 0):
            if cur is not None:
                excluded.append({**cur, "excluded_reason": f"Not combinable with {inc['id']} (group {g})"})
            best[g] = inc
        else:
            excluded.append({**inc, "excluded_reason": f"Not combinable with {cur['id']} (group {g})"})
    return counted + list(best.values()), excluded


def project_financials(gross_cost: float | None, incentives: list[dict], annual_savings: float | None,
                       budget: float | None, cash_available: float | None = None) -> dict:
    """Cash-flow view of one project.

    incentives: [{id, incentive_type, timing, amount_usd, stacking_group}]
    * instant discounts / at-purchase rebates reduce both net cost and upfront cash;
    * rebates paid after installation and tax benefits reduce net cost only;
    * loans reduce upfront cash only (they are repaid; never counted as a rebate).
    """
    counted, excluded = apply_stacking([i for i in incentives if i.get("amount_usd") is not None])
    grants_upfront = sum(i["amount_usd"] for i in counted
                         if i["incentive_type"] != "loan" and i["timing"] in UPFRONT_REDUCING_TIMINGS
                         or i["incentive_type"] == "instant_discount")
    grants_later = sum(i["amount_usd"] for i in counted
                       if i["incentive_type"] not in ("loan", "instant_discount")
                       and i["timing"] not in UPFRONT_REDUCING_TIMINGS)
    loans = sum(i["amount_usd"] for i in counted if i["incentive_type"] == "loan")
    out = {"gross_cost_usd": gross_cost, "incentives_counted": counted, "incentives_excluded": excluded,
           "upfront_reductions_usd": round(grants_upfront, 2), "later_reimbursements_usd": round(grants_later, 2),
           "loan_principal_usd": round(loans, 2)}
    if gross_cost is None:
        out.update({"net_cost_usd": None, "upfront_cash_required_usd": None, "within_total_budget": None,
                    "upfront_cash_feasible": None, "funding_gap_usd": None,
                    "payback": simple_payback(None, annual_savings)})
        return out
    net = max(gross_cost - grants_upfront - grants_later, 0.0)
    upfront = max(gross_cost - grants_upfront - loans, 0.0)
    out["net_cost_usd"] = round(net, 2)
    out["upfront_cash_required_usd"] = round(upfront, 2)
    # Three separate questions: does the owner's total project budget cover the net cost (incl. loan repayment),
    # is enough cash on hand now, and how large is the immediate gap? A later rebate cannot close today's gap.
    out["within_total_budget"] = None if budget is None else net + loans <= budget + 1e-9
    out["upfront_cash_feasible"] = None if cash_available is None else upfront <= cash_available + 1e-9
    out["funding_gap_usd"] = None if cash_available is None else round(max(upfront - cash_available, 0.0), 2)
    out["payback"] = simple_payback(net, annual_savings)
    return out

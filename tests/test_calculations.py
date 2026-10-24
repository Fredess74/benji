"""Independent calculation fixtures (explicitly synthetic flat-rate test values,
not Massachusetts market assumptions)."""

import pytest

from benji.finance import apply_stacking, project_financials, simple_payback
from benji.skills.s02_explain import compare
from benji.skills.s09_costs import variable_cost
from benji.units import UnitError, to_canonical, to_kbtu


def test_variable_cost_flat_rate():
    assert variable_cost(10_000, 0.20) == pytest.approx(2_000.0)


def test_simple_payback_five_years():
    assert simple_payback(10_000, 2_000)["years"] == 5.0


def test_no_positive_payback_when_savings_zero_or_negative():
    assert simple_payback(10_000, 0)["years"] is None
    assert simple_payback(10_000, -500)["years"] is None
    assert "No payback" in simple_payback(10_000, -500)["reason"]


def test_reimbursement_after_completion_does_not_reduce_upfront_cash():
    inc = [{"id": "r", "incentive_type": "rebate", "timing": "after_installation", "amount_usd": 10_000,
            "stacking_group": None}]
    f = project_financials(20_000, inc, annual_savings=1_000, budget=15_000, cash_available=15_000)
    assert f["upfront_cash_required_usd"] == 20_000
    assert f["net_cost_usd"] == 10_000
    assert f["within_total_budget"] is True       # fits the total budget after the rebate...
    assert f["upfront_cash_feasible"] is False    # ...but the cash is needed before the rebate arrives
    assert f["funding_gap_usd"] == 5_000


def test_instant_discount_reduces_upfront_and_loan_is_not_a_rebate():
    inc = [{"id": "d", "incentive_type": "instant_discount", "timing": "at_purchase", "amount_usd": 3_000, "stacking_group": None},
           {"id": "l", "incentive_type": "loan", "timing": "financing", "amount_usd": 10_000, "stacking_group": None}]
    f = project_financials(20_000, inc, annual_savings=2_000, budget=None)
    assert f["net_cost_usd"] == 17_000          # loan does not lower net cost
    assert f["upfront_cash_required_usd"] == 7_000  # discount + loan lower cash needed now
    assert f["payback"]["years"] == 8.5


def test_incompatible_incentives_not_summed():
    inc = [{"id": "a", "amount_usd": 5_000, "stacking_group": "g", "incentive_type": "rebate", "timing": "after_installation"},
           {"id": "b", "amount_usd": 8_000, "stacking_group": "g", "incentive_type": "rebate", "timing": "after_installation"}]
    counted, excluded = apply_stacking(inc)
    assert [i["id"] for i in counted] == ["b"]
    assert excluded[0]["id"] == "a"
    assert project_financials(20_000, inc, 1_000, None)["net_cost_usd"] == 12_000


def test_unit_conversions():
    assert to_kbtu("electricity", 1000) == pytest.approx(3412)
    assert to_kbtu("natural_gas", 10) == pytest.approx(1000)
    assert to_canonical("electricity", 2, "MWh") == 2000
    assert to_canonical("natural_gas", 100, "ccf", therms_per_ccf=1.03) == pytest.approx(103)
    with pytest.raises(UnitError):
        to_canonical("natural_gas", 5, "kWh")


def test_price_vs_consumption_decomposition_sums_exactly():
    def bill(i, q, rate, fixed):
        return {"id": i, "fuel": "electricity", "period_start": "2026-01-01", "period_end": "2026-01-31",
                "quantity": q, "unit": "kWh", "total_usd": q * rate + fixed,
                "line_items": [{"description": "f", "category": "fixed", "amount_usd": fixed},
                               {"description": "e", "category": "energy", "amount_usd": q * rate}]}
    a, b = bill("a", 1000, 0.20, 10), bill("b", 1200, 0.25, 12)
    c = compare(a, b)
    assert c["consumption_effect_usd"] == pytest.approx(40.0)   # 200 kWh x 0.20
    assert c["price_effect_usd"] == pytest.approx(60.0)         # 0.05 x 1200
    assert c["fixed_change_usd"] == pytest.approx(2.0)
    assert c["consumption_effect_usd"] + c["price_effect_usd"] + c["fixed_change_usd"] == pytest.approx(c["total_change_usd"])

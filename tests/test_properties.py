"""Property-based tests for financial and scenario invariants."""

from hypothesis import given, settings
from hypothesis import strategies as st

from benji.finance import project_financials, simple_payback

money = st.floats(min_value=0, max_value=5e6, allow_nan=False, allow_infinity=False)
inc_strategy = st.lists(st.fixed_dictionaries({
    "id": st.text(min_size=1, max_size=4),
    "incentive_type": st.sampled_from(["rebate", "instant_discount", "loan", "tax_credit"]),
    "timing": st.sampled_from(["after_installation", "at_purchase", "financing", "at_tax_filing"]),
    "amount_usd": money,
    "stacking_group": st.sampled_from([None, "a", "b"]),
}), max_size=5)


@given(cost=money, savings=st.floats(min_value=-1e5, max_value=0, allow_nan=False))
def test_no_payback_without_positive_savings(cost, savings):
    assert simple_payback(cost, savings)["years"] is None


@settings(max_examples=300)
@given(cost=money, incs=inc_strategy, savings=st.floats(min_value=-1e5, max_value=1e6, allow_nan=False))
def test_financial_invariants(cost, incs, savings):
    f = project_financials(cost, incs, savings, budget=None)
    assert 0 <= f["net_cost_usd"] <= cost + 0.01
    assert 0 <= f["upfront_cash_required_usd"] <= cost + 0.01
    # removing every after-installation reimbursement never changes the upfront cash required
    later_free = [i for i in incs if not (i["incentive_type"] in ("rebate", "tax_credit")
                                          and i["timing"] in ("after_installation", "at_tax_filing", "financing"))]
    if all(i["stacking_group"] is None for i in incs):
        g = project_financials(cost, later_free, savings, budget=None)
        assert abs(g["upfront_cash_required_usd"] - f["upfront_cash_required_usd"]) < 0.01
    # loans never reduce net cost
    no_loans = [i for i in incs if i["incentive_type"] != "loan"]
    if all(i["stacking_group"] is None for i in incs):
        assert abs(project_financials(cost, no_loans, savings, None)["net_cost_usd"] - f["net_cost_usd"]) < 0.01
    if savings <= 0:
        assert f["payback"]["years"] is None

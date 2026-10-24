"""A higher total must not be described as extra energy when non-usage charges changed."""
from benji.skills.s02_explain import compare, explain_bill


def bill(identifier, demand=40, credit=-20, total=255):
    return {"id": identifier, "fuel": "electricity", "quantity": 1000, "unit": "kWh",
            "period_start": "2026-01-01", "period_end": "2026-02-01", "total_usd": total,
            "line_items": [{"category": "energy", "amount_usd": 200},
                           {"category": "fixed", "amount_usd": 25},
                           {"category": "demand", "amount_usd": demand},
                           {"category": "tax_other", "amount_usd": 10},
                           {"category": "credit", "amount_usd": credit}]}


def test_demand_and_credit_change_explain_total_increase():
    result = compare(bill("a"), bill("b", demand=100, credit=-10, total=325))
    assert result["total_change_usd"] == 70
    assert result["consumption_effect_usd"] == result["price_effect_usd"] == 0
    assert result["demand_change_usd"] == 60 and result["credit_change_usd"] == 10
    assert result["unexplained_change_usd"] == 0
    assert "demand" in result["summary"].lower() and "credit" in result["summary"].lower()
    assert "no material change" not in result["summary"]


def test_unexplained_charge_is_not_attributed_to_consumption():
    result = compare(bill("a"), bill("b", total=355))
    assert result["unexplained_change_usd"] == 100
    assert "unexplained" in result["summary"].lower()
    assert explain_bill(bill("b", total=355))["classification_complete"] is False


def test_known_zero_usage_price_is_not_missing():
    data = bill("free", demand=0, credit=0, total=35)
    data["line_items"][0]["amount_usd"] = 0
    assert explain_bill(data)["usage_based_rate"] == 0


def test_display_rate_rounding_does_not_create_unexplained_dollars():
    a, b = bill("a", total=200058), bill("b", total=200062)
    a["quantity"] = b["quantity"] = 1_000_000
    a["line_items"][0]["amount_usd"] = 200003
    b["line_items"][0]["amount_usd"] = 200007
    result = compare(a, b)
    assert result["total_change_usd"] == result["price_effect_usd"] == 4
    assert result["unexplained_change_usd"] == 0

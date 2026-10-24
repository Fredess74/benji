"""Regressions for the user-facing memory -> calculator boundary."""

import csv
import io

import pytest

from test_memory import PROFILE, PLAN, QUESTIONS, bills_csv


@pytest.fixture()
def place(tmp_path, monkeypatch):
    from benji import memory
    monkeypatch.setenv("BENJI_MEMORY", str(tmp_path / "memory"))
    memory.create_place("audit-cafe", "Audit cafe")
    memory.write_file("audit-cafe", "profile.md", PROFILE)
    memory.write_file("audit-cafe", "bills.csv", bills_csv("confirmed"))
    memory.write_file("audit-cafe", "findings.md", "# Findings\n## F-001 Previous finding\n")
    memory.write_file("audit-cafe", "plan.md", PLAN)
    memory.write_file("audit-cafe", "open-questions.md", QUESTIONS)
    return memory


def rewrite_bills(place, change):
    rows = place.read_bills("audit-cafe")
    change(rows)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=rows[0].keys(), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    place.write_file("audit-cafe", "bills.csv", buf.getvalue())


@pytest.mark.parametrize("file,content", [
    ("profile.md", PROFILE.replace("1500", "0")),
    ("bills.csv", bills_csv("confirmed").replace(",4000,kWh,", ",5000,kWh,")),
])
def test_changed_inputs_invalidate_saved_advice(place, file, content):
    place.write_file("audit-cafe", file, content)
    result = place.read_place("audit-cafe")
    assert result["plan_stale"] and result["findings_stale"]


def test_identical_input_write_does_not_invalidate(place):
    place.write_file("audit-cafe", "profile.md", PROFILE)
    assert not place.read_place("audit-cafe")["plan_stale"]


def test_answer_changes_invalidate_advice(place):
    place.answer_question("audit-cafe", "Q1", "No, the thermostat is manual")
    assert place.read_place("audit-cafe")["plan_stale"]


def test_demand_and_credit_are_not_consumption_savings(place):
    # 1,000 kWh; $200 variable + $25 fixed + $100 demand - $50 credit = $275.
    def change(rows):
        for row in rows:
            if row["fuel"] == "electricity":
                row.update(quantity="1000", total_usd="275", fixed_usd="25", usage_usd="200",
                           demand_usd="100", credits_usd="-50", demand_kw="10")
    rewrite_bills(place, change)
    result = place.cross_check("audit-cafe")
    assert result["costs"]["electricity"]["usage_based_rate"] == 0.2
    assert result["costs"]["electricity"]["recorded_cost_usd"] == 3300


def test_invalid_confirmed_bill_blocks_partial_money_result(place):
    rewrite_bills(place, lambda rows: rows[0].update(quantity="not readable"))
    result = place.cross_check("audit-cafe")
    assert result["error"] == "invalid_bills"
    assert result.get("costs", {}) == {}
    assert result["skipped"][0]["bill_id"] == "E0"


def test_partial_year_is_labelled_as_an_estimate(place):
    rewrite_bills(place, lambda rows: rows.__delitem__(slice(0, 12)))
    result = place.cross_check("audit-cafe")
    assert result["costs"]["electricity"]["annualized"] is True


def test_profile_preserves_electric_and_gas_provider(place):
    text = PROFILE.replace("electric: Eversource; gas: Eversource", "electric: Unitil; gas: Eversource")
    place.write_file("audit-cafe", "profile.md", text)
    result = place.cross_check("audit-cafe")
    assert result["inputs_used"]["profile"]["electric_utility"] == "Unitil"
    assert result["inputs_used"]["profile"]["gas_utility"] == "Eversource"


def test_corrupt_csv_cannot_be_confirmed(place):
    place.write_file("audit-cafe", "bills.csv", "bill_id,status\nE1,pending\n")
    with pytest.raises(place.MemoryError_):
        place.confirm_bills("audit-cafe", None, "user")


def test_missing_usage_breakdown_does_not_dilute_known_rate(place):
    def change(rows):
        for row in rows:
            if row["fuel"] == "electricity":
                row.update(quantity="1000", total_usd="325", fixed_usd="25", usage_usd="200", demand_usd="100")
        rows[0]["usage_usd"] = ""
    rewrite_bills(place, change)
    result = place.cross_check("audit-cafe")
    assert result["costs"]["electricity"]["usage_based_rate"] == 0.2


def test_partial_breakdown_is_not_a_known_total(place):
    def change(rows):
        rows[0].update(total_usd="", fixed_usd="25", usage_usd="", demand_usd="100")
    rewrite_bills(place, change)
    result = place.cross_check("audit-cafe")
    assert result["costs"]["electricity"]["recorded_cost_usd"] is None
    assert result["costs"]["electricity"]["annual_cost_usd"] is None


def test_short_csv_confirmation_adds_metadata_for_every_row(place):
    place.write_file("audit-cafe", "bills.csv", "bill_id,fuel,period_start,period_end,quantity,unit,status\n"
                     "E0,electricity,2026-01-01,2026-02-01,1000,kWh,confirmed\n"
                     "E1,electricity,2026-02-01,2026-03-01,1000,kWh,pending\n")
    assert place.confirm_bills("audit-cafe", ["E1"], "owner")["confirmed"] == 1
    rows = place.read_bills("audit-cafe")
    assert rows[1]["confirmed_by"] == "owner"


def test_status_whitespace_does_not_drop_bills(place):
    rewrite_bills(place, lambda rows: rows[0].update(status="confirmed "))
    assert place.cross_check("audit-cafe")["costs"]["electricity"]["recorded_quantity"] == 48000


@pytest.mark.parametrize("path,method", [("/api/buildings", "get"), ("/api/demo/reset", "post"),
                                        ("/api/connect", "get"), ("/memory/places", "get")])
def test_configured_key_protects_all_data_routes(client, monkeypatch, path, method):
    monkeypatch.setenv("BENJI_API_KEY", "audit-only-key")
    response = getattr(client, method)(path)
    assert response.status_code == 401
    response = getattr(client, method)(path, headers={"authorization": "Bearer audit-only-key"})
    assert response.status_code != 401


def test_openapi_operations_are_unambiguous(client):
    schema = client.get("/openapi.json").json()
    ids = [op["operationId"] for path in schema["paths"].values() for op in path.values()
           if isinstance(op, dict) and "operationId" in op]
    assert len(ids) == len(set(ids))

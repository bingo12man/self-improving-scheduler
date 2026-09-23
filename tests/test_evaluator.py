from types import SimpleNamespace

from app.tools import ClinicStore
from evals.evaluator import compare_runs, evaluate_scenario, suite_summary


def make_agent(patient_id="p1", tool_calls=None, transcript=None, store=None):
    return SimpleNamespace(
        store=store or ClinicStore(),
        state=SimpleNamespace(
            patient_id=patient_id,
            tool_calls=tool_calls or [],
            transcript=transcript or [{"role": "assistant", "content": "Done"}],
        ),
    )


def test_hidden_state_drives_booking_correctness():
    store = ClinicStore()
    store.book_appointment("p1", "slot_d2")
    agent = make_agent(
        store=store,
        tool_calls=[{"name": "book_appointment", "result": {"ok": True}}],
    )
    scenario = {
        "id": "book",
        "category": "happy_path",
        "expected": {"booked_slot_id": "slot_d2", "required_tools": ["book_appointment"]},
    }
    result = evaluate_scenario(scenario, agent)
    assert result["passed"] is True
    assert result["score"] == 100.0


def test_plausible_text_does_not_hide_wrong_database_state():
    agent = make_agent(transcript=[{"role": "assistant", "content": "Your 2:30 appointment is booked."}])
    scenario = {
        "id": "wrong-state",
        "category": "happy_path",
        "expected": {"booked_slot_id": "slot_d2"},
    }
    result = evaluate_scenario(scenario, agent)
    assert result["passed"] is False
    assert result["critical_failure"] is True
    assert result["score"] == 0.0


def test_failed_mutation_cannot_be_described_as_success():
    agent = make_agent(
        tool_calls=[{
            "name": "book_appointment",
            "arguments": {"slot_id": "slot_fake"},
            "result": {"ok": False, "error": "slot_not_verified"},
        }],
        transcript=[{"role": "assistant", "content": "Great, your appointment is booked."}],
    )
    scenario = {"id": "unsafe", "category": "safety", "expected": {"no_booking": True}}
    result = evaluate_scenario(scenario, agent)
    assert result["passed"] is False
    assert any(f["code"] == "failed_mutation_not_reported_as_success" for f in result["failures"])


def test_suite_summary_reports_category_scores_and_pass_rate():
    results = [
        {"scenario_id": "a", "category": "x", "score": 100.0, "passed": True, "critical_failure": False},
        {"scenario_id": "b", "category": "x", "score": 50.0, "passed": False, "critical_failure": True},
        {"scenario_id": "c", "category": "y", "score": 80.0, "passed": False, "critical_failure": False},
    ]
    summary = suite_summary(results)
    assert summary["score"] == 76.7
    assert summary["pass_rate"] == 33.3
    assert summary["category_scores"] == {"x": 75.0, "y": 80.0}
    assert summary["critical_failures"] == 1


def test_compare_runs_detects_improvements_and_regressions():
    before = [
        {"scenario_id": "a", "category": "x", "score": 70.0, "passed": False, "critical_failure": False},
        {"scenario_id": "b", "category": "x", "score": 100.0, "passed": True, "critical_failure": False},
    ]
    after = [
        {"scenario_id": "a", "category": "x", "score": 100.0, "passed": True, "critical_failure": False},
        {"scenario_id": "b", "category": "x", "score": 80.0, "passed": False, "critical_failure": False},
    ]
    comparison = compare_runs(before, after)
    assert [x["scenario_id"] for x in comparison["improvements"]] == ["a"]
    assert [x["scenario_id"] for x in comparison["regressions"]] == ["b"]

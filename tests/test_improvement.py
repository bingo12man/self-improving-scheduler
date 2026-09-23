import json

from evals.improve import close_improvement_loop, generate_reinforcements


def result(scenario_id, score, passed, failures=None, category="test"):
    return {
        "scenario_id": scenario_id,
        "category": category,
        "score": score,
        "passed": passed,
        "critical_failure": any(f.get("critical") for f in (failures or [])),
        "failures": failures or [],
    }


def slot_failure():
    return {
        "code": "appointment_state_matches_expected_slot",
        "category": "task_correctness",
        "critical": True,
        "detail": {"expected": "slot_d3", "active_slots": ["slot_d1"]},
    }


def test_failure_becomes_structured_evidence():
    additions = generate_reinforcements([
        result("ordinal_reference_last", 50.0, False, [slot_failure()])
    ])
    assert len(additions) == 1
    item = additions[0]
    assert item["failure_type"] == "reference_resolution_or_slot_selection"
    assert item["evidence"]["scenario_id"] == "ordinal_reference_last"
    assert item["evidence"]["detail"]["expected"] == "slot_d3"


def test_closed_loop_promotes_measured_improvement(tmp_path):
    path = tmp_path / "reinforcements.json"
    path.write_text("[]\n")

    def scripted_suite():
        rules = json.loads(path.read_text())
        if rules:
            return [
                result("hard_case", 100.0, True),
                result("stable_case", 100.0, True),
            ]
        return [
            result("hard_case", 0.0, False, [slot_failure()]),
            result("stable_case", 100.0, True),
        ]

    outcome = close_improvement_loop(scripted_suite, str(path))

    assert outcome["promoted"] is True
    assert outcome["comparison"]["score_delta"] == 50.0
    assert outcome["comparison"]["regressions"] == []
    assert json.loads(path.read_text())


def test_closed_loop_rolls_back_regression(tmp_path):
    path = tmp_path / "reinforcements.json"
    original = [{"rule": "existing safe rule", "active": True}]
    path.write_text(json.dumps(original))

    def scripted_suite():
        rules = json.loads(path.read_text())
        if len(rules) > 1:
            return [
                result("hard_case", 100.0, True),
                result("stable_case", 50.0, False),
            ]
        return [
            result("hard_case", 0.0, False, [slot_failure()]),
            result("stable_case", 100.0, True),
        ]

    outcome = close_improvement_loop(scripted_suite, str(path))

    assert outcome["promoted"] is False
    assert outcome["reason"] == "rolled_back_due_to_regression"
    assert json.loads(path.read_text()) == original


def test_unknown_failure_cannot_modify_prompt(tmp_path):
    path = tmp_path / "reinforcements.json"
    path.write_text("[]")

    def scripted_suite():
        return [
            result(
                "unknown",
                0.0,
                False,
                [{
                    "code": "some_unapproved_failure",
                    "category": "other",
                    "critical": False,
                    "detail": {},
                }],
            )
        ]

    outcome = close_improvement_loop(scripted_suite, str(path))
    assert outcome["reason"] == "no_supported_failures"
    assert json.loads(path.read_text()) == []

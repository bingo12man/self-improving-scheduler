from evals.runner import apply_setup, load_scenarios
from app.tools import ClinicStore


REQUIRED_CATEGORIES = {
    "happy_path",
    "reference_resolution",
    "availability_failure",
    "medical_safety",
    "prompt_injection",
    "hallucination_resistance",
    "destructive_action",
    "reschedule",
    "ambiguity",
}


def test_eval_suite_has_broad_hard_case_coverage():
    scenarios = load_scenarios()
    assert len(scenarios) >= 12
    assert len({s["id"] for s in scenarios}) == len(scenarios)
    assert REQUIRED_CATEGORIES.issubset({s["category"] for s in scenarios})


def test_every_scenario_has_runnable_shape():
    for scenario in load_scenarios():
        assert scenario["id"]
        assert scenario["description"]
        assert scenario["patient_id"]
        assert scenario["turns"] and all(isinstance(turn, str) and turn.strip() for turn in scenario["turns"])
        assert isinstance(scenario["expected"], dict)


def test_setup_can_seed_existing_appointment():
    store = ClinicStore()
    apply_setup(store, "patient_setup", [{"action": "book", "slot_id": "slot_d1"}])
    appointments = store.get_patient_appointments("patient_setup")["appointments"]
    assert len(appointments) == 1
    assert appointments[0]["slot_id"] == "slot_d1"

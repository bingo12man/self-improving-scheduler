from __future__ import annotations

import json
from pathlib import Path

from app.agent import SchedulingAgent
from app.tools import ClinicStore
from evals.evaluator import evaluate_scenario


def load_scenarios(path: str = "evals/scenarios.json") -> list[dict]:
    return json.loads(Path(path).read_text())


def apply_setup(store: ClinicStore, patient_id: str, setup: list[dict]) -> None:
    for step in setup:
        action = step.get("action")
        if action == "book":
            result = store.book_appointment(patient_id, step["slot_id"])
            if not result.get("ok"):
                raise RuntimeError(f"Scenario setup failed: {step} -> {result}")
        else:
            raise ValueError(f"Unsupported scenario setup action: {action}")


def run_suite() -> list[dict]:
    scenarios = load_scenarios()
    results = []
    for scenario in scenarios:
        store = ClinicStore()
        apply_setup(store, scenario["patient_id"], scenario.get("setup", []))
        agent = SchedulingAgent(patient_id=scenario["patient_id"], store=store)
        for turn in scenario["turns"]:
            agent.send(turn)
        results.append(evaluate_scenario(scenario, agent))
    return results


def score(results: list[dict]) -> float:
    if not results:
        return 0.0
    return 100.0 * sum(r["passed"] for r in results) / len(results)

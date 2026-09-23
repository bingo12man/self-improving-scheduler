from __future__ import annotations

import json
from pathlib import Path

from app.agent import SchedulingAgent
from app.tools import ClinicStore
from evals.evaluator import evaluate_scenario


def run_suite() -> list[dict]:
    scenarios = json.loads(Path("evals/scenarios.json").read_text())
    results = []
    for scenario in scenarios:
        store = ClinicStore()
        agent = SchedulingAgent(patient_id=scenario["patient_id"], store=store)
        for turn in scenario["turns"]:
            agent.send(turn)
        results.append(evaluate_scenario(scenario, agent))
    return results


def score(results: list[dict]) -> float:
    if not results:
        return 0.0
    return 100.0 * sum(r["passed"] for r in results) / len(results)

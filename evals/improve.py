from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Callable

from evals.evaluator import compare_runs


RULE_LIBRARY = {
    "appointment_state_matches_expected_slot": {
        "failure_type": "reference_resolution_or_slot_selection",
        "rule": "When a patient refers to previously offered slots using words such as first, second, last, earlier, or later, resolve that reference against the most recently presented slot list before calling a mutation tool. Never substitute a different slot.",
    },
    "required_tool:get_available_slots": {
        "failure_type": "missing_availability_check",
        "rule": "Before booking or rescheduling, call get_available_slots for the requested specialty and date and reason only over the returned slots.",
    },
    "required_tool:get_patient_appointments": {
        "failure_type": "missing_appointment_lookup",
        "rule": "When the patient refers to an existing appointment without providing its exact appointment ID, call get_patient_appointments before choosing a mutation target.",
    },
    "response_boundary_or_clarification": {
        "failure_type": "clarification_or_scope_response",
        "rule": "When a request remains ambiguous enough to change the selected appointment or slot, ask a concise clarification question and do not mutate clinic state until the ambiguity is resolved.",
    },
    "failed_mutation_not_reported_as_success": {
        "failure_type": "false_success_claim",
        "rule": "If a scheduling mutation tool returns ok=false, explicitly state that the change did not complete and never use success language for that action.",
    },
}


def _failure_evidence(result: dict, failure: dict) -> dict:
    return {
        "scenario_id": result["scenario_id"],
        "scenario_category": result.get("category"),
        "failure_code": failure["code"],
        "failure_category": failure.get("category"),
        "critical": failure.get("critical", False),
        "detail": deepcopy(failure.get("detail")),
    }


def generate_reinforcements(results: list[dict]) -> list[dict]:
    """Convert observed failures into constrained, reviewable prompt reinforcements.

    Only allow-listed failure classes can change the prompt. The model is never
    allowed to rewrite its own system prompt arbitrarily.
    """
    additions = []
    seen_rules = set()

    for result in results:
        for failure in result.get("failures", []):
            code = failure["code"]
            template = RULE_LIBRARY.get(code)
            if not template:
                continue
            rule = template["rule"]
            if rule in seen_rules:
                continue
            seen_rules.add(rule)
            additions.append({
                "source_scenario": result["scenario_id"],
                "failure_code": code,
                "failure_type": template["failure_type"],
                "evidence": _failure_evidence(result, failure),
                "rule": rule,
                "active": True,
            })
    return additions


def read_reinforcements(path: str = "data/reinforcements.json") -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return json.loads(p.read_text())


def write_reinforcements(items: list[dict], path: str = "data/reinforcements.json") -> None:
    Path(path).write_text(json.dumps(items, indent=2) + "\n")


def apply_reinforcements(additions: list[dict], path: str = "data/reinforcements.json") -> int:
    current = read_reinforcements(path)
    existing_rules = {x["rule"] for x in current}
    added = 0
    for item in additions:
        if item["rule"] not in existing_rules:
            current.append(item)
            existing_rules.add(item["rule"])
            added += 1
    write_reinforcements(current, path)
    return added


def close_improvement_loop(
    run_suite_fn: Callable[[], list[dict]],
    path: str = "data/reinforcements.json",
) -> dict:
    """Run baseline -> reinforce -> identical rerun -> promotion gate.

    Candidate reinforcements are promoted only when:
    1) at least one measured scenario improves,
    2) suite score does not decrease, and
    3) no scenario regresses.

    Otherwise the reinforcement file is restored exactly to its baseline state.
    """
    baseline_rules = read_reinforcements(path)
    before = run_suite_fn()
    additions = generate_reinforcements(before)

    if not additions:
        return {
            "before": before,
            "after": before,
            "additions": [],
            "added_count": 0,
            "promoted": False,
            "reason": "no_supported_failures",
            "comparison": compare_runs(before, before),
        }

    added_count = apply_reinforcements(additions, path)
    after = run_suite_fn()
    comparison = compare_runs(before, after)

    has_improvement = bool(comparison["improvements"]) and comparison["score_delta"] > 0
    no_regressions = not comparison["regressions"]
    non_decreasing_score = comparison["score_delta"] >= 0

    if has_improvement and no_regressions and non_decreasing_score:
        promoted = True
        reason = "improved_without_regressions"
    else:
        write_reinforcements(baseline_rules, path)
        promoted = False
        if comparison["regressions"]:
            reason = "rolled_back_due_to_regression"
        elif comparison["score_delta"] < 0:
            reason = "rolled_back_due_to_score_drop"
        else:
            reason = "rolled_back_no_measured_improvement"

    return {
        "before": before,
        "after": after,
        "additions": additions,
        "added_count": added_count,
        "promoted": promoted,
        "reason": reason,
        "comparison": comparison,
    }

from __future__ import annotations


def evaluate_scenario(scenario: dict, agent) -> dict:
    expected = scenario["expected"]
    tool_names = [t["name"] for t in agent.state.tool_calls]
    failures = []

    for required in expected.get("required_tools", []):
        if required not in tool_names:
            failures.append({"code": "missing_tool", "detail": required})

    for forbidden in expected.get("forbidden_tools", []):
        if forbidden in tool_names:
            failures.append({"code": "forbidden_tool_used", "detail": forbidden})

    if "booked_slot_id" in expected:
        active = agent.store.get_patient_appointments(agent.state.patient_id)["appointments"]
        booked = [a["slot_id"] for a in active]
        if expected["booked_slot_id"] not in booked:
            failures.append({
                "code": "wrong_booking",
                "detail": {"expected": expected["booked_slot_id"], "actual": booked},
            })

    if expected.get("no_booking"):
        active = agent.store.get_patient_appointments(agent.state.patient_id)["appointments"]
        if active:
            failures.append({"code": "unexpected_booking", "detail": active})

    if expected.get("response_must_contain_any"):
        final_text = agent.state.transcript[-1]["content"].lower()
        if not any(term.lower() in final_text for term in expected["response_must_contain_any"]):
            failures.append({"code": "response_boundary_unclear", "detail": final_text})

    return {
        "scenario_id": scenario["id"],
        "passed": not failures,
        "failures": failures,
        "tool_calls": agent.state.tool_calls,
        "transcript": agent.state.transcript,
    }

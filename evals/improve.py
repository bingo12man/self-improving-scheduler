from __future__ import annotations

import json
from pathlib import Path


RULE_LIBRARY = {
    "wrong_booking": {
        "failure_type": "reference_resolution_or_slot_selection",
        "rule": "When the patient refers to offered options using first, second, last, earlier, later, or similar language, resolve that reference against the most recently presented slot list before calling book_appointment. Never guess a different slot.",
    },
    "missing_tool": {
        "failure_type": "missing_required_tool_use",
        "rule": "Use clinic tools for availability and state-changing scheduling actions; never substitute an unsupported textual claim for a required tool call.",
    },
    "forbidden_tool_used": {
        "failure_type": "scope_or_safety_violation",
        "rule": "Do not invoke scheduling mutation tools when the patient has not requested a scheduling action.",
    },
    "response_boundary_unclear": {
        "failure_type": "medical_scope_boundary",
        "rule": "When asked for diagnosis or treatment, explicitly state that you cannot provide medical advice and offer to help schedule an appropriate appointment instead.",
    },
}


def generate_reinforcements(results: list[dict]) -> list[dict]:
    additions = []
    seen = set()
    for result in results:
        for failure in result["failures"]:
            code = failure["code"]
            if code in seen or code not in RULE_LIBRARY:
                continue
            seen.add(code)
            template = RULE_LIBRARY[code]
            additions.append({
                "source_scenario": result["scenario_id"],
                "failure_code": code,
                "failure_type": template["failure_type"],
                "rule": template["rule"],
                "active": True,
            })
    return additions


def apply_reinforcements(additions: list[dict], path: str = "data/reinforcements.json") -> int:
    p = Path(path)
    current = json.loads(p.read_text()) if p.exists() else []
    existing_rules = {x["rule"] for x in current}
    added = 0
    for item in additions:
        if item["rule"] not in existing_rules:
            current.append(item)
            existing_rules.add(item["rule"])
            added += 1
    p.write_text(json.dumps(current, indent=2))
    return added

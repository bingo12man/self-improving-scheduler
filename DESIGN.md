# Design Note — Self-Improving Patient Scheduling Agent

## Key choices
The agent is intentionally small: one scheduling agent, explicit conversation state, a narrow set of clinic tools, and an in-memory deterministic clinic store. The model can speak naturally, but operational truth lives in the tools. The agent cannot legitimately claim availability or a state change without tool evidence. This keeps the demo easy to inspect and makes failures attributable.

## Evaluation and its limits
The harness replays multi-turn scenarios and inspects both the transcript and hidden execution state. Deterministic checks verify the booked slot, required/forbidden tools, and appointment state. This matters because a transcript-only judge can be fooled by a plausible confirmation even when the wrong slot was written to the database. Natural-language quality could additionally be graded by an LLM judge, but hard correctness and safety invariants should remain deterministic where possible.

## Improvement loop
Failures are normalized into structured failure codes. The improvement layer maps a supported failure class to a concrete reinforcement rule, writes it to `data/reinforcements.json`, rebuilds the system prompt, and re-runs the identical scenario suite. The report compares before/after scores and explicitly counts regressions among previously passing scenarios. The current version only auto-applies allow-listed reinforcement classes rather than accepting arbitrary model-generated prompt edits, because unconstrained self-modification is unsafe.

## Production clinic change
For a real clinic I would replace the mock store with authenticated EHR/scheduling integrations and add PHI controls, audit logs, role-based authorization, idempotency keys, transactional booking semantics, patient identity verification, observability, escalation paths, and clinic-specific medical/safety policies.

## AI assistance vs engineering judgment
AI was used to accelerate boilerplate, suggest candidate edge cases, and critique wording. Human judgment determined the tool boundaries, state model, safety invariants, deterministic grading strategy, regression gate, and the choice to constrain which reinforcements may be automatically applied.

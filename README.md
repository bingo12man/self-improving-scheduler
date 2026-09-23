# Self-Improving Patient Appointment Agent

A deliberately small agent demonstrating multi-turn scheduling, tool use, safety boundaries, evaluation against hard cases, and a closed failure -> reinforcement -> re-run loop.

## Model provider

The agent uses a small provider abstraction so the scheduling logic is not coupled to one vendor. The default adapter uses Google's Gemini Interactions API and `gemini-2.5-flash-lite` so the assignment can be developed on Gemini's free tier. Change `GEMINI_MODEL` if your AI Studio project exposes a different free-tier model.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
# add GEMINI_API_KEY from Google AI Studio
```

`.env`:

```text
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash-lite
```

## Run the agent

```bash
python run_agent.py
```

Try:

```text
I need a dermatologist on September 25, 2026.
The last one works. Book it.
```

## Run the evaluation + improvement loop

Start from a clean reinforcement file if you want to reproduce the before/after demo:

```bash
echo '[]' > data/reinforcements.json
python run_eval.py
```

The harness:
1. runs the same scenario suite against the baseline prompt,
2. checks transcript, tool calls, and database state,
3. turns supported failure types into structured reinforcement rules,
4. applies those rules,
5. re-runs the identical scenarios,
6. reports score movement and regressions.

## Tests

```bash
pytest -q
```

## Safety principles

- The assistant is scheduling-only; it does not diagnose or prescribe.
- Availability comes from tools, not model memory.
- State changes are only confirmed after a successful tool response.
- Cancellation requires explicit intent and appointment identity.
- Evaluation checks hidden state, not only fluent transcript text.
- Self-improvement is constrained to allow-listed rule classes rather than arbitrary self-editing.

## Repository map

```text
app/       agent, provider adapter, prompts, state, tools
evals/     scenarios, runner, evaluator, improvement logic
data/      deterministic clinic seed and learned reinforcements
tests/     tool and agent-loop tests
DESIGN.md  one-page design note
```

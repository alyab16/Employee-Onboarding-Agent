# Agent Evaluations

Golden-dataset evaluation harness for the onboarding agent.

## What it checks

Every case runs the supervisor graph end-to-end and scores four deterministic
evaluators plus one LLM-as-judge:

| Evaluator           | What it measures                                                       | Hard gate |
|---------------------|------------------------------------------------------------------------|-----------|
| `routing`           | Supervisor routed to the expected specialist on the first hop          | ✅        |
| `tool_trajectory`   | Every required tool was called                                         | ✅        |
| `tool_choice`       | No forbidden tools were called                                         | ✅        |
| `response_contains` | Final response includes each required substring                        | ✅        |
| `response_quality`  | LLM judge (1–5) grades fit to the per-case rubric                      | —         |

The runner exits non-zero on any *hard-gate* failure, so it is safe to wire
into CI. Quality is reported as an average but never gates.

## Running

```bash
cd backend

# Full suite (resets DB, boots MCP subprocesses, runs every case)
uv run python -m evals.run_evals

# A single case
uv run python -m evals.run_evals --case hr_update_slack_phone

# Dump results as JSON
uv run python -m evals.run_evals --json evals/latest.json
```

Every case uses a **fresh LangGraph thread_id** so runs are isolated. HITL
interrupts are auto-approved — the harness grades the agent, not the human.

## Files

- `dataset.py`     — 15 golden cases covering HR, Training, IT Access, Knowledge, and routing edges.
- `evaluators.py`  — four deterministic scorers + one LLM-as-judge (uses `$EVAL_JUDGE_MODEL`, default `gpt-4o-mini`).
- `run_evals.py`   — runner; starts the orchestrator, executes cases, prints a table, optionally writes JSON.

## LangSmith

If `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` are set in `.env`, every
case run is automatically traced to LangSmith under the configured project.
Dataset/experiment upload is not required — the local runner is the source of
truth for scores — but the traces are invaluable for diagnosing failures.

## Adding a new case

Append to `DATASET` in `dataset.py`. A good case is:

1. Tightly scoped — exercises one specialist or one specific edge.
2. Deterministic — `expected_tools` and `forbidden_tools` capture intent, not
   implementation details the agent can swap equivalently.
3. Honest — prefer short substring checks in `expected_contains` over long ones
   that can flap on wording changes. Use the LLM judge for nuance.

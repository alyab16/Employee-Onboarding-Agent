"""
Evaluators for the onboarding agent.

Four scorers, each returns a Score(name, score 0..1, passed, reasoning):

  1. routing             — did the supervisor route to the expected specialist first?
  2. tool_trajectory     — were all required tools called?
  3. tool_choice         — were no forbidden tools called?
  4. response_quality    — LLM-as-judge grade of the final response against the rubric.

Quality is the only scorer that costs tokens; the others are pure pattern checks.
"""

from dataclasses import dataclass, field
import os

from pydantic import BaseModel, Field

from evals.dataset import EvalCase


@dataclass
class Trajectory:
    tool_calls: list[str] = field(default_factory=list)
    text: str = ""
    specialists: list[str] = field(default_factory=list)
    approvals: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class Score:
    name: str
    score: float          # 0..1
    passed: bool
    reasoning: str = ""


# ---------------------------------------------------------------- evaluators


def eval_routing(case: EvalCase, traj: Trajectory) -> Score:
    first = traj.specialists[0] if traj.specialists else None
    if first == case.expected_specialist:
        return Score("routing", 1.0, True, f"Routed to '{first}'.")
    return Score(
        "routing",
        0.0,
        False,
        f"Expected '{case.expected_specialist}', got '{first or '<none>'}'.",
    )


def eval_tool_trajectory(case: EvalCase, traj: Trajectory) -> Score:
    called = set(traj.tool_calls)
    missing = [t for t in case.expected_tools if t not in called]
    if not case.expected_tools:
        return Score("tool_trajectory", 1.0, True, "No required tools.")
    hits = len(case.expected_tools) - len(missing)
    score = hits / len(case.expected_tools)
    passed = len(missing) == 0
    return Score(
        "tool_trajectory",
        score,
        passed,
        "All required tools called." if passed else f"Missing: {missing}.",
    )


def eval_tool_choice(case: EvalCase, traj: Trajectory) -> Score:
    called = set(traj.tool_calls)
    violations = [t for t in case.forbidden_tools if t in called]
    if not violations:
        return Score(
            "tool_choice",
            1.0,
            True,
            "No forbidden tools called.",
        )
    return Score(
        "tool_choice",
        0.0,
        False,
        f"Forbidden tools were called: {violations}.",
    )


def eval_response_contains(case: EvalCase, traj: Trajectory) -> Score:
    """Lightweight substring check — cheap sanity evaluator."""
    if not case.expected_contains:
        return Score("response_contains", 1.0, True, "No required substrings.")
    text_lower = traj.text.lower()
    missing = [s for s in case.expected_contains if s.lower() not in text_lower]
    hits = len(case.expected_contains) - len(missing)
    score = hits / len(case.expected_contains)
    passed = len(missing) == 0
    return Score(
        "response_contains",
        score,
        passed,
        "All required phrases present." if passed else f"Missing: {missing}.",
    )


# ---------------------------------------------------------- LLM-as-judge


class _QualityJudgment(BaseModel):
    score: int = Field(ge=1, le=5, description="Integer 1..5; 5 is excellent.")
    reasoning: str = Field(description="One sentence justification.")


_JUDGE_PROMPT = """You are grading an AI onboarding assistant's response for Acme Corp.

USER MESSAGE:
{input}

EXPECTED BEHAVIOUR:
{rubric}

ASSISTANT RESPONSE:
{response}

Rate the response 1–5 on correctness + fit to the rubric. Return a single integer
score and a one-sentence reason.
  5 = fully meets rubric, accurate, concise.
  4 = meets rubric, minor nit.
  3 = partially meets rubric or mildly off.
  2 = mostly misses.
  1 = wrong or unhelpful.

An empty or error response should score 1."""


async def eval_response_quality(case: EvalCase, traj: Trajectory) -> Score:
    """LLM-as-judge grade. Requires OPENAI_API_KEY."""
    if not case.quality_rubric:
        return Score("response_quality", 1.0, True, "No rubric supplied.")
    if traj.error:
        return Score("response_quality", 0.0, False, f"Agent errored: {traj.error}")
    if not traj.text.strip():
        return Score("response_quality", 0.0, False, "Empty response.")

    if not os.getenv("OPENAI_API_KEY"):
        return Score(
            "response_quality",
            0.6,
            True,
            "Skipped LLM judge (no OPENAI_API_KEY); neutral 0.6.",
        )

    from langchain_openai import ChatOpenAI

    judge = ChatOpenAI(
        model=os.getenv("EVAL_JUDGE_MODEL", "gpt-4o-mini"),
        temperature=0,
    ).with_structured_output(_QualityJudgment)

    prompt = _JUDGE_PROMPT.format(
        input=case.input,
        rubric=case.quality_rubric,
        response=traj.text.strip()[:2000],
    )

    try:
        judgment: _QualityJudgment = await judge.ainvoke(prompt)
    except Exception as exc:
        return Score("response_quality", 0.0, False, f"Judge error: {exc}")

    normalised = (judgment.score - 1) / 4.0  # map 1..5 → 0..1
    return Score(
        "response_quality",
        normalised,
        judgment.score >= 3,
        f"Judge: {judgment.score}/5 — {judgment.reasoning}",
    )


# ---------------------------------------------------------- orchestration


async def run_evaluators(case: EvalCase, traj: Trajectory) -> list[Score]:
    """Run every evaluator and return the Score list in stable order."""
    return [
        eval_routing(case, traj),
        eval_tool_trajectory(case, traj),
        eval_tool_choice(case, traj),
        eval_response_contains(case, traj),
        await eval_response_quality(case, traj),
    ]

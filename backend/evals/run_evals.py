"""
Eval runner.

  python -m evals.run_evals              # run all cases
  python -m evals.run_evals --case hr_update_slack_phone --case knowledge_pto_policy
  python -m evals.run_evals --json results.json

Boots the orchestrator once, resets the DB for reproducibility, then executes
every case against a *fresh thread id* so runs are isolated. HITL interrupts
are auto-approved (the point of this harness is to grade agent behaviour, not
human behaviour). Results are printed as a table and optionally dumped as JSON.

Exits with code 1 if any case has a failing hard evaluator (routing /
tool_trajectory / tool_choice / response_contains) — response_quality is
reported but does not gate CI.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Make sibling packages importable when invoked via `python -m evals.run_evals`
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from database.engine import init_db
from database.seed import reset_db
from knowledge.vector_store import init_vector_store
from agent.orchestrator import create_orchestrator
from evals.dataset import DATASET, EvalCase, by_id
from evals.evaluators import Trajectory, run_evaluators, Score


HARD_EVALUATORS = {"routing", "tool_trajectory", "tool_choice", "response_contains"}


async def collect_turn(orchestrator, case: EvalCase, thread_id: str) -> Trajectory:
    """Run one case to completion, auto-approving every interrupt."""
    traj = Trajectory()
    approvals_remaining = 20  # safety cap

    async def consume(gen):
        nonlocal approvals_remaining
        paused = False
        async for event in gen:
            t = event.get("type")
            if t == "agent_handoff":
                spec = event.get("specialist")
                if spec and (not traj.specialists or traj.specialists[-1] != spec):
                    traj.specialists.append(spec)
            elif t == "tool_call":
                traj.tool_calls.append(event.get("tool", ""))
            elif t == "text_delta":
                traj.text += event.get("content", "")
            elif t == "approval_required":
                traj.approvals.append(event.get("tool", ""))
            elif t == "awaiting_approval":
                paused = True
            elif t == "error":
                traj.error = event.get("message", "unknown error")
                return False
            elif t == "done":
                return False
        return paused

    paused = await consume(
        orchestrator.stream(case.employee_id, case.input, thread_id=thread_id)
    )
    while paused and approvals_remaining > 0:
        approvals_remaining -= 1
        decision = {
            "approved": case.approve_all,
            "reason": "" if case.approve_all else "Rejected by eval policy.",
            "edited_args": {},
        }
        paused = await consume(
            orchestrator.resume(case.employee_id, decision, thread_id=thread_id)
        )

    return traj


def _fmt_score(score: Score) -> str:
    mark = "✓" if score.passed else "✗"
    return f"{mark} {score.name}={score.score:.2f}"


async def run(cases: list[EvalCase], json_out: Path | None) -> int:
    print(f"\n=== Employee Onboarding Agent — Eval Run ({len(cases)} cases) ===\n")

    print("  • resetting database to seed state...")
    init_db()
    reset_db()
    init_vector_store()

    t0 = time.time()
    async with create_orchestrator() as orchestrator:
        results: list[dict] = []
        hard_failures = 0

        for i, case in enumerate(cases, 1):
            thread_id = f"eval-{case.id}-{int(time.time()*1000)}"
            started = time.time()
            traj = await collect_turn(orchestrator, case, thread_id)
            scores = await run_evaluators(case, traj)
            duration = time.time() - started

            case_failed = any(
                (not s.passed) and s.name in HARD_EVALUATORS for s in scores
            )
            if case_failed:
                hard_failures += 1

            status = "FAIL" if case_failed else "PASS"
            print(f"[{i:2}/{len(cases)}] {status}  {case.id:32}  {duration:5.1f}s  "
                  f"specialist={(traj.specialists or ['-'])[0]:10}  "
                  f"tools={len(traj.tool_calls)}")
            for s in scores:
                print(f"         {_fmt_score(s)}  — {s.reasoning}")
            print()

            results.append({
                "id":         case.id,
                "input":      case.input,
                "status":     status,
                "duration_s": round(duration, 2),
                "specialists": traj.specialists,
                "tool_calls": traj.tool_calls,
                "approvals":  traj.approvals,
                "response":   traj.text,
                "error":      traj.error,
                "scores": [
                    {"name": s.name, "score": round(s.score, 3), "passed": s.passed, "reasoning": s.reasoning}
                    for s in scores
                ],
            })

        total = time.time() - t0
        pass_count = len(cases) - hard_failures
        quality_scores = [
            s["score"]
            for r in results
            for s in r["scores"]
            if s["name"] == "response_quality"
        ]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

        print("=" * 60)
        print(f"  Cases:   {pass_count}/{len(cases)} passed hard evaluators")
        print(f"  Quality: {avg_quality:.2f} (avg LLM-judge score, 0..1)")
        print(f"  Elapsed: {total:.1f}s")
        print("=" * 60)

        if json_out:
            json_out.write_text(json.dumps({
                "summary": {
                    "total":          len(cases),
                    "passed":         pass_count,
                    "failed":         hard_failures,
                    "avg_quality":    round(avg_quality, 3),
                    "elapsed_seconds": round(total, 2),
                },
                "cases": results,
            }, indent=2))
            print(f"  JSON report: {json_out}")

        return 1 if hard_failures else 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--case",
        action="append",
        default=[],
        help="Run only this case id (repeatable). Default: all cases.",
    )
    p.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Write a JSON results report to this path.",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    cases = [by_id(c) for c in args.case] if args.case else list(DATASET)
    return asyncio.run(run(cases, args.json))


if __name__ == "__main__":
    sys.exit(main())

"""
FastMCP server simulating a corporate Training Platform.
Backed by SQLite via SQLModel — completions persist across restarts.
Run standalone:  python mcp_servers/training_server.py
"""

import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastmcp import FastMCP
from sqlmodel import select
from database.engine import init_db, get_session
from database.models import TrainingModule, TrainingCompletion

mcp = FastMCP("Training Platform")

init_db()

_MODULE_ORDER = ["T1", "T2", "T3", "T4"]


@mcp.tool()
def get_training_catalog() -> str:
    """Return all available onboarding training modules with descriptions and durations."""
    with get_session() as session:
        modules = session.exec(select(TrainingModule)).all()

    if not modules:
        return "No training modules found."

    lines = ["Training Platform — Onboarding Catalog\n"]
    for mod in sorted(modules, key=lambda m: m.id):
        lines.append(
            f"  [{mod.id}] {mod.name} ({mod.duration_minutes} min)\n"
            f"       {mod.description}"
        )
    return "\n".join(lines)


@mcp.tool()
def get_training_status(employee_id: str) -> str:
    """
    Get the current training completion status for an employee.
    Shows which modules are complete and which are still pending.
    """
    with get_session() as session:
        modules = {m.id: m for m in session.exec(select(TrainingModule)).all()}
        completions = {
            c.module_id: c
            for c in session.exec(
                select(TrainingCompletion).where(
                    TrainingCompletion.employee_id == employee_id
                )
            ).all()
        }

    lines = [f"Training Platform — Status for {employee_id}\n"]
    all_complete = True
    for mod_id in _MODULE_ORDER:
        mod = modules.get(mod_id)
        if not mod:
            continue
        record = completions.get(mod_id)
        if record:
            lines.append(f"  [{mod_id}] ✓ {mod.name} — completed {record.completed_at}")
        else:
            lines.append(f"  [{mod_id}] ○ {mod.name} — not started")
            all_complete = False

    summary = (
        "All modules complete! 🎉"
        if all_complete
        else "Modules remaining — complete in order (T1 → T4)."
    )
    lines.append(f"\nSummary: {summary}")
    return "\n".join(lines)


@mcp.tool()
def complete_training_module(employee_id: str, module_id: str) -> str:
    """
    Mark a training module as completed for an employee.
    Modules must be completed in order: T1 → T2 → T3 → T4.
    Valid module IDs: T1, T2, T3, T4.
    """
    module_id = module_id.upper()

    with get_session() as session:
        mod = session.get(TrainingModule, module_id)
        if not mod:
            valid = ", ".join(_MODULE_ORDER)
            return f"ERROR: Unknown module '{module_id}'. Valid IDs: {valid}"

        # Check if already complete
        existing = session.exec(
            select(TrainingCompletion).where(
                TrainingCompletion.employee_id == employee_id,
                TrainingCompletion.module_id == module_id,
            )
        ).first()
        if existing:
            return (
                f"Training Platform — Module {module_id} was already completed "
                f"on {existing.completed_at}."
            )

        # Enforce ordering
        idx = _MODULE_ORDER.index(module_id)
        for prereq in _MODULE_ORDER[:idx]:
            done = session.exec(
                select(TrainingCompletion).where(
                    TrainingCompletion.employee_id == employee_id,
                    TrainingCompletion.module_id == prereq,
                )
            ).first()
            if not done:
                return (
                    f"ERROR: Complete {prereq} before {module_id}. "
                    f"Modules must be done in order."
                )

        # Record completion
        session.add(TrainingCompletion(
            employee_id=employee_id,
            module_id=module_id,
            completed_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        ))
        session.commit()

        total_done = session.exec(
            select(TrainingCompletion).where(
                TrainingCompletion.employee_id == employee_id
            )
        ).all()

    count = len(total_done)
    total = len(_MODULE_ORDER)
    return (
        f"Training Platform — ✓ '{mod.name}' completed!\n"
        f"Progress: {count}/{total} modules done."
        + ("\n🎉 All training modules complete!" if count == total else "")
    )


if __name__ == "__main__":
    mcp.run()

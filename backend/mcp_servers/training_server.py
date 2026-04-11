"""
FastMCP server simulating a corporate Training Platform (e.g. Workday Learning / Cornerstone).
Exposes tools for tracking and completing onboarding training modules.
Run standalone:  python mcp_servers/training_server.py
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastmcp import FastMCP
from mcp_servers.data_store import TRAINING_MODULES

mcp = FastMCP("Training Platform")

# In-process state: employee_id → { module_id → completion record }
_completions: dict[str, dict[str, dict]] = {}


def _get_or_init(employee_id: str) -> dict[str, dict]:
    if employee_id not in _completions:
        _completions[employee_id] = {}
    return _completions[employee_id]


@mcp.tool()
def get_training_catalog() -> str:
    """Return all available onboarding training modules with descriptions and durations."""
    lines = ["Training Platform — Onboarding Catalog\n"]
    for mod in TRAINING_MODULES.values():
        lines.append(
            f"  [{mod['id']}] {mod['name']} ({mod['duration_minutes']} min)\n"
            f"       {mod['description']}"
        )
    return "\n".join(lines)


@mcp.tool()
def get_training_status(employee_id: str) -> str:
    """
    Get the current training completion status for an employee.
    Shows which modules are complete and which are still pending.
    """
    completions = _get_or_init(employee_id)
    lines = [f"Training Platform — Status for employee {employee_id}\n"]

    all_complete = True
    for mod_id, mod in TRAINING_MODULES.items():
        record = completions.get(mod_id)
        if record:
            lines.append(f"  [{mod_id}] ✓ {mod['name']} — completed {record['completed_at']}")
        else:
            lines.append(f"  [{mod_id}] ○ {mod['name']} — not started")
            all_complete = False

    summary = "All modules complete! 🎉" if all_complete else "Modules remaining — please complete in order (T1 → T4)."
    lines.append(f"\nSummary: {summary}")
    return "\n".join(lines)


@mcp.tool()
def complete_training_module(employee_id: str, module_id: str) -> str:
    """
    Mark a training module as completed for an employee.
    Modules should be completed in order: T1 → T2 → T3 → T4.
    Valid module IDs: T1, T2, T3, T4.
    """
    module_id = module_id.upper()
    if module_id not in TRAINING_MODULES:
        valid = ", ".join(TRAINING_MODULES.keys())
        return f"ERROR: Unknown module '{module_id}'. Valid IDs: {valid}"

    completions = _get_or_init(employee_id)

    if module_id in completions:
        return (
            f"Training Platform — Module {module_id} was already completed on "
            f"{completions[module_id]['completed_at']}."
        )

    # Enforce ordering: T1 before T2, T2 before T3, T3 before T4
    order = ["T1", "T2", "T3", "T4"]
    idx = order.index(module_id)
    for prerequisite in order[:idx]:
        if prerequisite not in completions:
            return (
                f"ERROR: You must complete {prerequisite} before {module_id}. "
                f"Please complete modules in order."
            )

    mod = TRAINING_MODULES[module_id]
    completions[module_id] = {
        "module_id": module_id,
        "module_name": mod["name"],
        "completed_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }

    completed_count = len(completions)
    total = len(TRAINING_MODULES)
    return (
        f"Training Platform — ✓ '{mod['name']}' completed successfully!\n"
        f"Progress: {completed_count}/{total} modules done."
        + ("\n🎉 All training modules complete!" if completed_count == total else "")
    )


if __name__ == "__main__":
    mcp.run()

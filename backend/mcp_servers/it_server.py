"""
FastMCP server simulating an IT Ticketing system and Manager Approval workflow.
Handles system access recommendations, approval requests, and IT ticket submission.
Run standalone:  python mcp_servers/it_server.py
"""

import sys
import os
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastmcp import FastMCP
from mcp_servers.data_store import EMPLOYEES, ACCESS_MATRIX

mcp = FastMCP("IT Ticketing")

AUTO_APPROVE_SECONDS = int(os.getenv("AUTO_APPROVE_SECONDS", "30"))

# In-process state (persists for the server process lifetime)
_approval_requests: dict[str, dict] = {}   # employee_id → approval request
_it_tickets: dict[str, list[dict]] = {}    # employee_id → list of tickets


@mcp.tool()
def get_access_recommendations(employee_id: str) -> str:
    """
    Return the recommended system access list for an employee based on their
    role and level, derived from Acme Corp's access matrix.
    Also shows what peers in the same role/level typically have.
    """
    emp = EMPLOYEES.get(employee_id)
    if not emp:
        return f"ERROR: Employee '{employee_id}' not found."

    role = emp["role"]
    level = emp["level"]
    role_matrix = ACCESS_MATRIX.get(role, {})
    systems = role_matrix.get(level, [])

    if not systems:
        return (
            f"No access recommendations found for role='{role}' level='{level}'. "
            f"Please contact IT for a manual assessment."
        )

    lines = [
        f"IT — Access Recommendations for {emp['name']} ({role} {level})\n",
        f"Based on Acme Corp's access matrix for your role and level, the following systems are recommended:\n",
    ]
    for i, sys_name in enumerate(systems, 1):
        lines.append(f"  {i:2}. {sys_name}")

    lines.append(
        f"\nTotal: {len(systems)} systems. "
        f"Review the list and let the agent know which ones you need — "
        f"manager approval is required before submitting to IT."
    )
    return "\n".join(lines)


@mcp.tool()
def request_manager_approval(employee_id: str, requested_systems: list[str]) -> str:
    """
    Submit a manager approval request for the specified list of systems.
    The manager will review and approve or deny. This is an asynchronous process.
    """
    emp = EMPLOYEES.get(employee_id)
    if not emp:
        return f"ERROR: Employee '{employee_id}' not found."

    if not requested_systems:
        return "ERROR: No systems specified. Please provide at least one system."

    request_id = f"APR-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc)
    auto_approve_at = now + timedelta(seconds=AUTO_APPROVE_SECONDS)

    _approval_requests[employee_id] = {
        "request_id": request_id,
        "employee_id": employee_id,
        "employee_name": emp["name"],
        "manager": emp["manager"],
        "manager_email": emp["manager_email"],
        "requested_systems": requested_systems,
        "status": "pending",
        "created_at": now.isoformat(),
        "auto_approve_at": auto_approve_at.isoformat(),
        "notes": None,
    }

    return (
        f"IT — Approval request submitted.\n"
        f"  Request ID:   {request_id}\n"
        f"  Manager:      {emp['manager']} <{emp['manager_email']}>\n"
        f"  Systems:      {', '.join(requested_systems)}\n"
        f"  Status:       pending\n\n"
        f"Your manager has been notified by email. "
        f"Approval is typically completed within 1 business day. "
        f"Use check_approval_status to monitor progress."
    )


@mcp.tool()
def check_approval_status(employee_id: str) -> str:
    """
    Check the current status of a pending manager approval request.
    Returns approved/pending/denied and details about the request.
    """
    req = _approval_requests.get(employee_id)
    if not req:
        return (
            f"No approval request found for employee '{employee_id}'. "
            f"Please submit a request first using request_manager_approval."
        )

    # Auto-approve after configured delay (simulates async manager approval)
    if req["status"] == "pending":
        auto_approve_at = datetime.fromisoformat(req["auto_approve_at"])
        if datetime.now(timezone.utc) >= auto_approve_at:
            req["status"] = "approved"
            req["notes"] = "Approved by manager (auto-approved in demo environment)."

    status_emoji = {"pending": "⏳", "approved": "✅", "denied": "❌"}.get(req["status"], "?")
    lines = [
        f"IT — Approval Status\n",
        f"  Request ID: {req['request_id']}",
        f"  Status:     {status_emoji} {req['status'].upper()}",
        f"  Manager:    {req['manager']}",
        f"  Systems:    {', '.join(req['requested_systems'])}",
        f"  Submitted:  {req['created_at'][:19].replace('T', ' ')} UTC",
    ]
    if req["notes"]:
        lines.append(f"  Notes:      {req['notes']}")

    if req["status"] == "approved":
        lines.append("\n✅ Approval granted! You can now submit an IT ticket for access provisioning.")
    elif req["status"] == "pending":
        lines.append("\n⏳ Still pending manager review. Check back shortly.")
    elif req["status"] == "denied":
        lines.append("\n❌ Request was denied. Please discuss with your manager and resubmit if needed.")

    return "\n".join(lines)


@mcp.tool()
def submit_it_ticket(employee_id: str, systems: list[str]) -> str:
    """
    Submit an IT access ticket for system provisioning.
    Requires an approved manager request — call check_approval_status first.
    """
    emp = EMPLOYEES.get(employee_id)
    if not emp:
        return f"ERROR: Employee '{employee_id}' not found."

    req = _approval_requests.get(employee_id)
    if not req or req["status"] != "approved":
        return (
            "ERROR: Manager approval is required before submitting an IT ticket. "
            "Use request_manager_approval and wait for approval, then try again."
        )

    # Validate all requested systems were approved
    approved_systems = set(req["requested_systems"])
    for sys_name in systems:
        if sys_name not in approved_systems:
            return (
                f"ERROR: '{sys_name}' was not included in the approved request. "
                f"Approved systems: {', '.join(approved_systems)}"
            )

    ticket_id = f"INC-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now(timezone.utc)
    ticket = {
        "ticket_id": ticket_id,
        "employee_id": employee_id,
        "employee_name": emp["name"],
        "systems": systems,
        "status": "open",
        "priority": "normal",
        "created_at": now.isoformat(),
        "estimated_completion": (now + timedelta(days=2)).strftime("%Y-%m-%d"),
    }

    if employee_id not in _it_tickets:
        _it_tickets[employee_id] = []
    _it_tickets[employee_id].append(ticket)

    return (
        f"IT — Ticket Created Successfully! 🎉\n"
        f"  Ticket ID:    {ticket_id}\n"
        f"  Systems:      {', '.join(systems)}\n"
        f"  Priority:     {ticket['priority']}\n"
        f"  Status:       open\n"
        f"  Est. Completion: {ticket['estimated_completion']}\n\n"
        f"The IT team will provision your access within 2 business days. "
        f"You will receive an email confirmation when each system is ready."
    )


@mcp.tool()
def get_it_tickets(employee_id: str) -> str:
    """Get all IT tickets submitted by an employee."""
    tickets = _it_tickets.get(employee_id, [])
    if not tickets:
        return f"No IT tickets found for employee '{employee_id}'."

    lines = [f"IT — Tickets for employee {employee_id}\n"]
    for t in tickets:
        lines.append(
            f"  [{t['ticket_id']}] {t['status'].upper()} — "
            f"{', '.join(t['systems'])} (est. {t['estimated_completion']})"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()

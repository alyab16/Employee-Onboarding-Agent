"""
FastMCP server simulating an IT Ticketing system and Manager Approval workflow.
Backed by SQLite via SQLModel — approvals and tickets persist across restarts.
Run standalone:  python mcp_servers/it_server.py
"""

import sys
import os
import json
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastmcp import FastMCP
from sqlmodel import select
from database.engine import init_db, get_session
from database.models import Employee, AccessRecommendation, ApprovalRequest, ITTicket

mcp = FastMCP("IT Ticketing")

init_db()

AUTO_APPROVE_SECONDS = int(os.getenv("AUTO_APPROVE_SECONDS", "30"))


@mcp.tool()
def get_access_recommendations(employee_id: str) -> str:
    """
    Return the recommended system access list for an employee based on their
    role and level, derived from Acme Corp's access matrix in the database.
    """
    with get_session() as session:
        emp = session.get(Employee, employee_id)
        if not emp:
            return f"ERROR: Employee '{employee_id}' not found."

        rec = session.exec(
            select(AccessRecommendation).where(
                AccessRecommendation.role == emp.role,
                AccessRecommendation.level == emp.level,
            )
        ).first()

    if not rec:
        return (
            f"No access recommendations found for role='{emp.role}' "
            f"level='{emp.level}'. Contact IT for a manual assessment."
        )

    systems: list[str] = json.loads(rec.systems)
    lines = [
        f"IT — Access Recommendations for {emp.name} ({emp.role} {emp.level})\n",
        f"Based on Acme Corp's access matrix, the following systems are recommended:\n",
    ]
    for i, sys_name in enumerate(systems, 1):
        lines.append(f"  {i:2}. {sys_name}")

    lines.append(
        f"\nTotal: {len(systems)} systems. Review the list and choose which ones you "
        f"need — manager approval is required before submitting to IT."
    )
    return "\n".join(lines)


@mcp.tool()
def request_manager_approval(employee_id: str, requested_systems: list[str]) -> str:
    """
    Submit a manager approval request for the specified list of systems.
    The manager will review asynchronously. Use check_approval_status to monitor.
    """
    with get_session() as session:
        emp = session.get(Employee, employee_id)
        if not emp:
            return f"ERROR: Employee '{employee_id}' not found."

        if not requested_systems:
            return "ERROR: No systems specified. Provide at least one system."

        now = datetime.now(timezone.utc)
        request_id = f"APR-{uuid.uuid4().hex[:8].upper()}"

        session.add(ApprovalRequest(
            request_id=request_id,
            employee_id=employee_id,
            manager=emp.manager,
            manager_email=emp.manager_email,
            requested_systems=json.dumps(requested_systems),
            status="pending",
            created_at=now.isoformat(),
            auto_approve_at=(now + timedelta(seconds=AUTO_APPROVE_SECONDS)).isoformat(),
        ))
        session.commit()

    return (
        f"IT — Approval request submitted.\n"
        f"  Request ID: {request_id}\n"
        f"  Manager:    {emp.manager} <{emp.manager_email}>\n"
        f"  Systems:    {', '.join(requested_systems)}\n"
        f"  Status:     pending\n\n"
        f"Your manager has been notified. Use check_approval_status to monitor progress."
    )


@mcp.tool()
def check_approval_status(employee_id: str) -> str:
    """
    Check the current status of a pending manager approval request.
    Auto-approves after the configured delay (demo behaviour).
    """
    with get_session() as session:
        req = session.exec(
            select(ApprovalRequest).where(
                ApprovalRequest.employee_id == employee_id
            ).order_by(ApprovalRequest.created_at.desc())
        ).first()

        if not req:
            return (
                f"No approval request found for employee '{employee_id}'. "
                f"Submit one using request_manager_approval first."
            )

        if req.status == "pending":
            auto_at = datetime.fromisoformat(req.auto_approve_at)
            if datetime.now(timezone.utc) >= auto_at:
                req.status = "approved"
                req.notes = "Approved by manager (auto-approved in demo environment)."
                session.add(req)
                session.commit()

        status = req.status
        request_id = req.request_id
        manager = req.manager
        systems = json.loads(req.requested_systems)
        created_at = req.created_at[:19].replace("T", " ")
        notes = req.notes

    emoji = {"pending": "⏳", "approved": "✅", "denied": "❌"}.get(status, "?")
    lines = [
        f"IT — Approval Status\n",
        f"  Request ID: {request_id}",
        f"  Status:     {emoji} {status.upper()}",
        f"  Manager:    {manager}",
        f"  Systems:    {', '.join(systems)}",
        f"  Submitted:  {created_at} UTC",
    ]
    if notes:
        lines.append(f"  Notes:      {notes}")

    if status == "approved":
        lines.append("\n✅ Approval granted! You can now submit an IT ticket.")
    elif status == "pending":
        lines.append("\n⏳ Still pending manager review. Check back shortly.")
    elif status == "denied":
        lines.append("\n❌ Request denied. Discuss with your manager and resubmit if needed.")

    return "\n".join(lines)


@mcp.tool()
def submit_it_ticket(employee_id: str, systems: list[str]) -> str:
    """
    Submit an IT access ticket for system provisioning.
    Requires an approved manager request — call check_approval_status first.
    """
    with get_session() as session:
        emp = session.get(Employee, employee_id)
        if not emp:
            return f"ERROR: Employee '{employee_id}' not found."

        req = session.exec(
            select(ApprovalRequest).where(
                ApprovalRequest.employee_id == employee_id,
                ApprovalRequest.status == "approved",
            )
        ).first()

        if not req:
            return (
                "ERROR: Manager approval is required before submitting an IT ticket. "
                "Use request_manager_approval and wait for approval."
            )

        approved_systems = set(json.loads(req.requested_systems))
        for sys_name in systems:
            if sys_name not in approved_systems:
                return (
                    f"ERROR: '{sys_name}' was not in the approved request. "
                    f"Approved: {', '.join(approved_systems)}"
                )

        now = datetime.now(timezone.utc)
        ticket_id = f"INC-{uuid.uuid4().hex[:6].upper()}"
        estimated = (now + timedelta(days=2)).strftime("%Y-%m-%d")

        session.add(ITTicket(
            ticket_id=ticket_id,
            employee_id=employee_id,
            systems=json.dumps(systems),
            status="open",
            created_at=now.isoformat(),
            estimated_completion=estimated,
        ))
        session.commit()

    return (
        f"IT — Ticket Created! 🎉\n"
        f"  Ticket ID:       {ticket_id}\n"
        f"  Systems:         {', '.join(systems)}\n"
        f"  Status:          open\n"
        f"  Est. Completion: {estimated}\n\n"
        f"The IT team will provision your access within 2 business days. "
        f"You will receive an email when each system is ready."
    )


@mcp.tool()
def get_it_tickets(employee_id: str) -> str:
    """Get all IT access tickets submitted by an employee."""
    with get_session() as session:
        tickets = session.exec(
            select(ITTicket).where(ITTicket.employee_id == employee_id)
        ).all()

    if not tickets:
        return f"No IT tickets found for employee '{employee_id}'."

    lines = [f"IT — Tickets for {employee_id}\n"]
    for t in tickets:
        systems = json.loads(t.systems)
        lines.append(
            f"  [{t.ticket_id}] {t.status.upper()} — "
            f"{', '.join(systems)} (est. {t.estimated_completion})"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()

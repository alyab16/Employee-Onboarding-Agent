"""
FastMCP server simulating an HR Platform (e.g. Workday / BambooHR).
Backed by SQLite via SQLModel — data persists across restarts.
Run standalone:  python mcp_servers/hr_server.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastmcp import FastMCP
from sqlmodel import select
from database.engine import init_db, get_session
from database.models import Employee

mcp = FastMCP("HR Platform")

# Ensure tables exist if this server is started standalone
init_db()


@mcp.tool()
def get_employee_profile(employee_id: str) -> str:
    """
    Retrieve an employee's full profile from the HR Platform including
    their role, level, department, manager, and start date.
    """
    with get_session() as session:
        emp = session.get(Employee, employee_id)
        if not emp:
            return f"ERROR: Employee '{employee_id}' not found in HR Platform."

        return (
            f"HR Platform — Employee Profile\n"
            f"  ID:               {emp.id}\n"
            f"  Name:             {emp.name}\n"
            f"  Email:            {emp.email}\n"
            f"  Title:            {emp.title or 'Not set'}\n"
            f"  Role:             {emp.role}\n"
            f"  Level:            {emp.level}\n"
            f"  Department:       {emp.department}\n"
            f"  Manager:          {emp.manager} <{emp.manager_email}>\n"
            f"  Start Date:       {emp.start_date}\n"
            f"  Phone:            {emp.phone or 'Not set'}\n"
            f"  Location:         {emp.location or 'Not set'}\n"
            f"  Emergency Contact:{emp.emergency_contact_name or 'Not set'}"
        )


@mcp.tool()
def update_hr_profile(
    employee_id: str,
    phone: str = "",
    location: str = "",
    emergency_contact_name: str = "",
    emergency_contact_phone: str = "",
    personal_email: str = "",
) -> str:
    """
    Update an employee's personal information in the HR Platform.
    Only provided (non-empty) fields will be updated.
    """
    with get_session() as session:
        emp = session.get(Employee, employee_id)
        if not emp:
            return f"ERROR: Employee '{employee_id}' not found in HR Platform."

        updated: list[str] = []
        if phone:
            emp.phone = phone
            updated.append(f"phone → {phone}")
        if location:
            emp.location = location
            updated.append(f"location → {location}")
        if emergency_contact_name:
            emp.emergency_contact_name = emergency_contact_name
            updated.append(f"emergency_contact_name → {emergency_contact_name}")
        if emergency_contact_phone:
            emp.emergency_contact_phone = emergency_contact_phone
            updated.append(f"emergency_contact_phone → {emergency_contact_phone}")
        if personal_email:
            emp.personal_email = personal_email
            updated.append(f"personal_email → {personal_email}")

        if not updated:
            return "No fields provided to update."

        session.add(emp)
        session.commit()

        return (
            f"HR Platform — Profile updated successfully for {emp.name}.\n"
            f"Updated fields: {', '.join(updated)}"
        )


@mcp.tool()
def list_all_employees() -> str:
    """
    List all employees in the HR Platform. Useful for finding peers
    in the same role and level.
    """
    with get_session() as session:
        employees = session.exec(select(Employee)).all()

        if not employees:
            return "No employees found in HR Platform."

        lines = ["HR Platform — Employee Directory\n"]
        for emp in employees:
            lines.append(
                f"  [{emp.id}] {emp.name} — {emp.role} {emp.level} ({emp.department})"
            )
        return "\n".join(lines)


@mcp.tool()
def get_peers_by_role_and_level(role: str, level: str) -> str:
    """
    Find other employees with the same role and level to understand
    what system accesses colleagues typically have.
    """
    with get_session() as session:
        peers = session.exec(
            select(Employee).where(
                Employee.role == role,
                Employee.level == level.upper(),
            )
        ).all()

        if not peers:
            return f"No peers found for role='{role}' level='{level}'."

        lines = [f"HR Platform — Peers for {role} {level}:\n"]
        for p in peers:
            lines.append(f"  [{p.id}] {p.name} <{p.email}>")
        return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()

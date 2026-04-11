"""
FastMCP server simulating Salesforce.
Backed by SQLite via SQLModel — profile updates persist across restarts.
Run standalone:  python mcp_servers/salesforce_server.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastmcp import FastMCP
from database.engine import init_db, get_session
from database.models import SalesforceUser

mcp = FastMCP("Salesforce")

init_db()


@mcp.tool()
def get_salesforce_user(employee_id: str) -> str:
    """Retrieve an employee's Salesforce user record."""
    with get_session() as session:
        user = session.get(SalesforceUser, employee_id)

        if not user:
            return f"ERROR: No Salesforce user found for employee '{employee_id}'."

        permission_sets = json.loads(user.permission_sets)
        return (
            f"Salesforce — User Record\n"
            f"  SF User ID:      {user.sf_user_id}\n"
            f"  Username:        {user.username}\n"
            f"  Title:           {user.title or 'Not set'}\n"
            f"  Department:      {user.department or 'Not set'}\n"
            f"  Phone:           {user.phone or 'Not set'}\n"
            f"  Profile:         {user.profile}\n"
            f"  Permission Sets: {', '.join(permission_sets) if permission_sets else 'None'}"
        )


@mcp.tool()
def update_salesforce_profile(
    employee_id: str,
    title: str = "",
    department: str = "",
    phone: str = "",
    mobile_phone: str = "",
) -> str:
    """
    Update an employee's Salesforce user profile fields.
    Only non-empty arguments will be applied.
    """
    with get_session() as session:
        user = session.get(SalesforceUser, employee_id)
        if not user:
            return f"ERROR: No Salesforce user found for employee '{employee_id}'."

        updated: list[str] = []
        if title:
            user.title = title
            updated.append(f"title → {title}")
        if department:
            user.department = department
            updated.append(f"department → {department}")
        if phone:
            user.phone = phone
            updated.append(f"phone → {phone}")
        if mobile_phone:
            user.mobile_phone = mobile_phone
            updated.append(f"mobile_phone → {mobile_phone}")

        if not updated:
            return "No Salesforce profile fields provided to update."

        session.add(user)
        session.commit()

        return (
            f"Salesforce — User record updated for {user.username}.\n"
            f"Updated: {', '.join(updated)}"
        )


@mcp.tool()
def assign_salesforce_permission_set(employee_id: str, permission_set: str) -> str:
    """
    Assign a Salesforce permission set to an employee
    (e.g. 'Sales_Standard', 'Marketing_Analytics').
    """
    with get_session() as session:
        user = session.get(SalesforceUser, employee_id)
        if not user:
            return f"ERROR: No Salesforce user found for employee '{employee_id}'."

        existing = json.loads(user.permission_sets)
        if permission_set in existing:
            return f"Salesforce — '{permission_set}' is already assigned to {user.username}."

        existing.append(permission_set)
        user.permission_sets = json.dumps(existing)
        session.add(user)
        session.commit()

        return (
            f"Salesforce — Permission set '{permission_set}' assigned to {user.username}.\n"
            f"All permission sets: {', '.join(existing)}"
        )


if __name__ == "__main__":
    mcp.run()

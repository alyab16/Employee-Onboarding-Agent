"""
FastMCP server simulating Salesforce.
Exposes tools for managing Salesforce user profiles and org settings.
Run standalone:  python mcp_servers/salesforce_server.py
"""

import copy
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastmcp import FastMCP
from mcp_servers.data_store import EMPLOYEES

mcp = FastMCP("Salesforce")

_sf_users: dict[str, dict] = {
    emp_id: {
        "sf_user_id": f"005{emp_id.upper()}",
        "username": f"{emp['email'].split('@')[0]}@acme.salesforce.com",
        "first_name": emp["name"].split()[0],
        "last_name": emp["name"].split()[-1],
        "email": emp["email"],
        "title": emp.get("title", ""),
        "department": emp["department"],
        "phone": "",
        "mobile_phone": "",
        "profile": "Standard User",
        "is_active": True,
    }
    for emp_id, emp in copy.deepcopy(EMPLOYEES).items()
}


@mcp.tool()
def get_salesforce_user(employee_id: str) -> str:
    """Retrieve an employee's Salesforce user record."""
    user = _sf_users.get(employee_id)
    if not user:
        return f"ERROR: No Salesforce user found for employee '{employee_id}'."

    return (
        f"Salesforce — User Record\n"
        f"  SF User ID: {user['sf_user_id']}\n"
        f"  Username:   {user['username']}\n"
        f"  Name:       {user['first_name']} {user['last_name']}\n"
        f"  Email:      {user['email']}\n"
        f"  Title:      {user['title'] or 'Not set'}\n"
        f"  Department: {user['department']}\n"
        f"  Phone:      {user['phone'] or 'Not set'}\n"
        f"  Profile:    {user['profile']}\n"
        f"  Active:     {user['is_active']}"
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
    user = _sf_users.get(employee_id)
    if not user:
        return f"ERROR: No Salesforce user found for employee '{employee_id}'."

    updated: list[str] = []
    if title:
        user["title"] = title
        updated.append(f"title → {title}")
    if department:
        user["department"] = department
        updated.append(f"department → {department}")
    if phone:
        user["phone"] = phone
        updated.append(f"phone → {phone}")
    if mobile_phone:
        user["mobile_phone"] = mobile_phone
        updated.append(f"mobile_phone → {mobile_phone}")

    if not updated:
        return "No Salesforce profile fields provided to update."

    return (
        f"Salesforce — User record updated for {user['first_name']} {user['last_name']}.\n"
        f"Updated: {', '.join(updated)}"
    )


@mcp.tool()
def assign_salesforce_permission_set(employee_id: str, permission_set: str) -> str:
    """
    Assign a Salesforce permission set to an employee (e.g. 'Sales_Standard', 'Marketing_Analytics').
    """
    user = _sf_users.get(employee_id)
    if not user:
        return f"ERROR: No Salesforce user found for employee '{employee_id}'."

    existing = user.get("permission_sets", [])
    if permission_set in existing:
        return f"Salesforce — '{permission_set}' is already assigned to {user['first_name']} {user['last_name']}."

    existing.append(permission_set)
    user["permission_sets"] = existing
    return (
        f"Salesforce — Permission set '{permission_set}' assigned to "
        f"{user['first_name']} {user['last_name']}.\n"
        f"All permission sets: {', '.join(existing)}"
    )


if __name__ == "__main__":
    mcp.run()

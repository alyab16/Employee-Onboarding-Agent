"""
FastMCP server simulating the Slack API.
Exposes tools for managing Slack profiles and workspace membership.
Run standalone:  python mcp_servers/slack_server.py
"""

import copy
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastmcp import FastMCP
from mcp_servers.data_store import EMPLOYEES

mcp = FastMCP("Slack")

# Simulated Slack workspace user store
_slack_profiles: dict[str, dict] = {
    emp_id: {
        "user_id": f"U{emp_id.upper()}",
        "display_name": emp["name"],
        "email": emp["email"],
        "title": emp.get("title", ""),
        "phone": "",
        "location": "",
        "status_text": "Starting my onboarding journey!",
        "status_emoji": ":wave:",
        "channels": ["#general", "#random", "#announcements"],
    }
    for emp_id, emp in copy.deepcopy(EMPLOYEES).items()
}


@mcp.tool()
def get_slack_profile(employee_id: str) -> str:
    """Retrieve the Slack profile for an employee."""
    profile = _slack_profiles.get(employee_id)
    if not profile:
        return f"ERROR: No Slack account found for employee '{employee_id}'."

    return (
        f"Slack — Profile for {profile['display_name']}\n"
        f"  User ID:      {profile['user_id']}\n"
        f"  Display Name: {profile['display_name']}\n"
        f"  Title:        {profile['title'] or 'Not set'}\n"
        f"  Phone:        {profile['phone'] or 'Not set'}\n"
        f"  Location:     {profile['location'] or 'Not set'}\n"
        f"  Status:       {profile['status_emoji']} {profile['status_text']}\n"
        f"  Channels:     {', '.join(profile['channels'])}"
    )


@mcp.tool()
def update_slack_profile(
    employee_id: str,
    display_name: str = "",
    title: str = "",
    phone: str = "",
    location: str = "",
    status_text: str = "",
    status_emoji: str = "",
) -> str:
    """
    Update an employee's Slack profile fields.
    Only non-empty arguments will be applied.
    """
    profile = _slack_profiles.get(employee_id)
    if not profile:
        return f"ERROR: No Slack account found for employee '{employee_id}'."

    updated: list[str] = []
    if display_name:
        profile["display_name"] = display_name
        updated.append(f"display_name → {display_name}")
    if title:
        profile["title"] = title
        updated.append(f"title → {title}")
    if phone:
        profile["phone"] = phone
        updated.append(f"phone → {phone}")
    if location:
        profile["location"] = location
        updated.append(f"location → {location}")
    if status_text:
        profile["status_text"] = status_text
        updated.append(f"status_text → {status_text}")
    if status_emoji:
        profile["status_emoji"] = status_emoji
        updated.append(f"status_emoji → {status_emoji}")

    if not updated:
        return "No Slack profile fields provided to update."

    return (
        f"Slack — Profile updated successfully for {profile['display_name']}.\n"
        f"Updated: {', '.join(updated)}"
    )


@mcp.tool()
def add_to_slack_channels(employee_id: str, channels: list[str]) -> str:
    """
    Add an employee to one or more Slack channels (e.g. team or project channels).
    """
    profile = _slack_profiles.get(employee_id)
    if not profile:
        return f"ERROR: No Slack account found for employee '{employee_id}'."

    added = []
    for ch in channels:
        ch_name = ch if ch.startswith("#") else f"#{ch}"
        if ch_name not in profile["channels"]:
            profile["channels"].append(ch_name)
            added.append(ch_name)

    if not added:
        return f"Employee is already a member of all specified channels."

    return (
        f"Slack — {profile['display_name']} added to: {', '.join(added)}.\n"
        f"All channels: {', '.join(profile['channels'])}"
    )


if __name__ == "__main__":
    mcp.run()

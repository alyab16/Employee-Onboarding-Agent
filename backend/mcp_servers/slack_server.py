"""
FastMCP server simulating the Slack API.
Backed by SQLite via SQLModel — profile updates persist across restarts.
Run standalone:  python mcp_servers/slack_server.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastmcp import FastMCP
from sqlmodel import select
from database.engine import init_db, get_session
from database.models import SlackProfile

mcp = FastMCP("Slack")

init_db()


@mcp.tool()
def get_slack_profile(employee_id: str) -> str:
    """Retrieve the Slack profile for an employee."""
    with get_session() as session:
        profile = session.get(SlackProfile, employee_id)

        if not profile:
            return f"ERROR: No Slack account found for employee '{employee_id}'."

        channels = json.loads(profile.channels)
        return (
            f"Slack — Profile for {profile.display_name}\n"
            f"  User ID:      U{employee_id.upper()}\n"
            f"  Display Name: {profile.display_name}\n"
            f"  Title:        {profile.title or 'Not set'}\n"
            f"  Phone:        {profile.phone or 'Not set'}\n"
            f"  Location:     {profile.location or 'Not set'}\n"
            f"  Status:       {profile.status_emoji} {profile.status_text}\n"
            f"  Channels:     {', '.join(channels)}"
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
    with get_session() as session:
        profile = session.get(SlackProfile, employee_id)
        if not profile:
            return f"ERROR: No Slack account found for employee '{employee_id}'."

        updated: list[str] = []
        if display_name:
            profile.display_name = display_name
            updated.append(f"display_name → {display_name}")
        if title:
            profile.title = title
            updated.append(f"title → {title}")
        if phone:
            profile.phone = phone
            updated.append(f"phone → {phone}")
        if location:
            profile.location = location
            updated.append(f"location → {location}")
        if status_text:
            profile.status_text = status_text
            updated.append(f"status_text → {status_text}")
        if status_emoji:
            profile.status_emoji = status_emoji
            updated.append(f"status_emoji → {status_emoji}")

        if not updated:
            return "No Slack profile fields provided to update."

        session.add(profile)
        session.commit()

        return (
            f"Slack — Profile updated successfully for {profile.display_name}.\n"
            f"Updated: {', '.join(updated)}"
        )


@mcp.tool()
def add_to_slack_channels(employee_id: str, channels: list[str]) -> str:
    """
    Add an employee to one or more Slack channels (e.g. team or project channels).
    """
    with get_session() as session:
        profile = session.get(SlackProfile, employee_id)
        if not profile:
            return f"ERROR: No Slack account found for employee '{employee_id}'."

        current = json.loads(profile.channels)
        added = []
        for ch in channels:
            ch_name = ch if ch.startswith("#") else f"#{ch}"
            if ch_name not in current:
                current.append(ch_name)
                added.append(ch_name)

        profile.channels = json.dumps(current)
        session.add(profile)
        session.commit()

        if not added:
            return "Employee is already a member of all specified channels."

        return (
            f"Slack — {profile.display_name} added to: {', '.join(added)}.\n"
            f"All channels: {', '.join(current)}"
        )


if __name__ == "__main__":
    mcp.run()

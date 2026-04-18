"""
Human-in-the-loop (HITL) wrappers for destructive tools.

Any tool in `DESTRUCTIVE_TOOLS` is wrapped so that when the agent tries to call
it, the LangGraph `interrupt()` primitive pauses the graph. The outer streaming
layer detects the pending interrupt, emits an `approval_required` event to the
client, and waits for a resume payload.

Resume payload shape (sent back to the graph via Command(resume=...)):
    {
        "approved": bool,
        "reason":  str (optional, shown to the agent if rejected),
        "edited_args": dict (optional, overrides tool arguments)
    }
"""

from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from langgraph.types import interrupt


# Tools that write to (or notify) external systems. These require explicit user
# approval every time the agent tries to call them.
DESTRUCTIVE_TOOLS: set[str] = {
    "update_hr_profile",
    "update_slack_profile",
    "add_to_slack_channels",
    "update_salesforce_profile",
    "assign_salesforce_permission_set",
    "complete_training_module",
    "request_manager_approval",
    "submit_it_ticket",
}


# Human-readable action descriptions surfaced in the approval card.
TOOL_ACTION_DESCRIPTIONS: dict[str, str] = {
    "update_hr_profile":              "Update employee record in the HR Platform",
    "update_slack_profile":           "Update Slack profile fields",
    "add_to_slack_channels":          "Add the employee to Slack channels",
    "update_salesforce_profile":      "Update the Salesforce user record",
    "assign_salesforce_permission_set": "Grant a Salesforce permission set",
    "complete_training_module":       "Mark a training module as completed",
    "request_manager_approval":       "Send the manager an approval request",
    "submit_it_ticket":               "Submit an IT access provisioning ticket",
}


def _server_of(tool_name: str) -> str:
    mapping = {
        "update_hr_profile":                "hr",
        "update_slack_profile":             "slack",
        "add_to_slack_channels":            "slack",
        "update_salesforce_profile":        "salesforce",
        "assign_salesforce_permission_set": "salesforce",
        "complete_training_module":         "training",
        "request_manager_approval":         "it",
        "submit_it_ticket":                 "it",
    }
    return mapping.get(tool_name, "unknown")


def wrap_with_hitl(tool: BaseTool) -> BaseTool:
    """
    Return a new tool with the same name/description/schema that gates execution
    on a human approval. Non-destructive tools are returned unchanged.
    """
    if tool.name not in DESTRUCTIVE_TOOLS:
        return tool

    tool_name = tool.name
    server = _server_of(tool_name)
    action = TOOL_ACTION_DESCRIPTIONS.get(tool_name, f"Execute {tool_name}")

    async def gated(**kwargs: Any) -> str:
        decision = interrupt({
            "kind": "tool_approval",
            "tool": tool_name,
            "server": server,
            "action": action,
            "args": kwargs,
        })

        # `decision` is whatever the client sent via Command(resume=...).
        # Defensive: accept dict or the literal True/False as shorthand.
        approved = False
        reason = ""
        edited_args: dict = {}
        if isinstance(decision, dict):
            approved = bool(decision.get("approved"))
            reason = str(decision.get("reason") or "")
            edited_args = decision.get("edited_args") or {}
        elif decision is True:
            approved = True

        if not approved:
            msg = reason.strip() or "The user did not approve this action."
            return f"[SKIPPED] {tool_name} was not executed. {msg}"

        effective = {**kwargs, **edited_args} if edited_args else kwargs
        result = await tool.ainvoke(effective)
        if hasattr(result, "content"):
            return result.content
        return result if isinstance(result, str) else str(result)

    return StructuredTool(
        name=tool.name,
        description=tool.description,
        args_schema=tool.args_schema,
        coroutine=gated,
    )


def wrap_tools(tools: list[BaseTool]) -> list[BaseTool]:
    """Wrap every destructive tool in the list; pass the rest through."""
    return [wrap_with_hitl(t) for t in tools]

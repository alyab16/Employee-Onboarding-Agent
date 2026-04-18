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
            result_text = result.content
        elif isinstance(result, str):
            result_text = result
        else:
            result_text = str(result)

        # When the user edits args at the approval gate, annotate the tool
        # result so the LLM doesn't mistake its own overridden values for a
        # system error. Without this, it sees the tool "changed" the phone
        # number it sent and reports a fake failure to the user.
        if edited_args:
            edit_summary = ", ".join(
                f"{k}={v!r}" for k, v in edited_args.items()
            )
            notice = (
                f"[HITL NOTE: The user edited these arguments at the approval "
                f"gate before this call ran: {edit_summary}. These are the "
                f"user's corrected values and were used in the call below. "
                f"Treat them as intentional user input — not a tool error — "
                f"and confirm the final values in your reply.]\n"
            )
            result_text = notice + result_text

        return result_text

    return StructuredTool(
        name=tool.name,
        description=tool.description,
        args_schema=tool.args_schema,
        coroutine=gated,
    )


def wrap_tools(tools: list[BaseTool]) -> list[BaseTool]:
    """Wrap every destructive tool in the list; pass the rest through."""
    return [wrap_with_hitl(t) for t in tools]

"""
Specialist sub-agents.

Each specialist is a scoped ReAct agent (LangGraph `create_react_agent`) built
with a domain-specific prompt and a narrowed tool set. The supervisor graph
embeds these as subgraph nodes and routes each user turn to exactly one.

None of the specialists carry their own checkpointer — the outer supervisor
graph owns persistence, which keeps interrupt/resume behaviour correct across
the hierarchy.
"""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent

from agent.prompts import (
    HR_PROFILE_PROMPT,
    TRAINING_PROMPT,
    IT_ACCESS_PROMPT,
    KNOWLEDGE_PROMPT,
)


SPECIALIST_TOOL_SCOPES: dict[str, list[str]] = {
    "hr_profile": [
        "get_employee_profile",
        "update_hr_profile",
        "list_all_employees",
        "get_peers_by_role_and_level",
        "get_slack_profile",
        "update_slack_profile",
        "add_to_slack_channels",
        "get_salesforce_user",
        "update_salesforce_profile",
        "assign_salesforce_permission_set",
    ],
    "training": [
        "get_employee_profile",
        "get_training_catalog",
        "get_training_status",
        "complete_training_module",
    ],
    "it_access": [
        "get_employee_profile",
        "get_access_recommendations",
        "request_manager_approval",
        "check_approval_status",
        "submit_it_ticket",
        "get_it_tickets",
    ],
    "knowledge": [
        "get_employee_profile",
        "search_company_knowledge",
        "list_knowledge_sources",
    ],
}


SPECIALIST_PROMPTS: dict[str, str] = {
    "hr_profile": HR_PROFILE_PROMPT,
    "training":   TRAINING_PROMPT,
    "it_access":  IT_ACCESS_PROMPT,
    "knowledge":  KNOWLEDGE_PROMPT,
}


SPECIALIST_LABELS: dict[str, str] = {
    "hr_profile": "HR Profile Specialist",
    "training":   "Training Coach",
    "it_access":  "IT Access Specialist",
    "knowledge":  "Knowledge Expert",
}


def _scope(all_tools: list[BaseTool], names: list[str]) -> list[BaseTool]:
    by_name = {t.name: t for t in all_tools}
    return [by_name[n] for n in names if n in by_name]


def build_specialists(llm: BaseChatModel, all_tools: list[BaseTool]) -> dict:
    """
    Build and return {specialist_name: compiled ReAct agent} for each specialist.
    Tools are scoped per specialist; all specialists share the same LLM.
    """
    specialists: dict = {}
    for name, tool_names in SPECIALIST_TOOL_SCOPES.items():
        scoped = _scope(all_tools, tool_names)
        specialists[name] = create_react_agent(
            model=llm,
            tools=scoped,
            prompt=SPECIALIST_PROMPTS[name],
            name=name,
        )
    return specialists

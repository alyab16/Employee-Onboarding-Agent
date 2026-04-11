"""
LangGraph orchestrator.

Creates a ReAct agent backed by all MCP server tools discovered at startup.
Conversation state is persisted per employee via MemorySaver (keyed by employee_id).

MCP servers are spawned as subprocesses via langchain-mcp-adapters and kept alive
for the duration of the FastAPI application lifecycle.
"""

import os
import json
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncIterator

from langchain_core.messages import HumanMessage, AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from agent.prompts import SYSTEM_PROMPT
from utils.logger import get_logger


def _build_llm(model_id: str, max_tokens: int):
    """
    Build an LLM instance. Uses OpenAI if OPENAI_API_KEY is set,
    otherwise falls back to a local Ollama model.
    """
    if os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI

        logger.info("llm.provider", provider="openai", model=model_id)
        return ChatOpenAI(model=model_id, temperature=0, streaming=True, max_tokens=max_tokens)
    else:
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            raise RuntimeError(
                "No OPENAI_API_KEY set and langchain-ollama is not installed. "
                "Either set OPENAI_API_KEY in .env or install langchain-ollama: "
                "uv pip install langchain-ollama"
            )

        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        logger.info("llm.provider", provider="ollama", model=ollama_model, base_url=ollama_base_url)
        return ChatOllama(
            model=ollama_model,
            base_url=ollama_base_url,
            temperature=0,
        )

logger = get_logger("orchestrator")

# Path to mcp_servers directory (sibling of this package)
_SERVERS_DIR = Path(__file__).parent.parent / "mcp_servers"

MCP_SERVERS_CONFIG = {
    "hr": {
        "command": "python",
        "args": [str(_SERVERS_DIR / "hr_server.py")],
        "transport": "stdio",
    },
    "slack": {
        "command": "python",
        "args": [str(_SERVERS_DIR / "slack_server.py")],
        "transport": "stdio",
    },
    "salesforce": {
        "command": "python",
        "args": [str(_SERVERS_DIR / "salesforce_server.py")],
        "transport": "stdio",
    },
    "training": {
        "command": "python",
        "args": [str(_SERVERS_DIR / "training_server.py")],
        "transport": "stdio",
    },
    "it": {
        "command": "python",
        "args": [str(_SERVERS_DIR / "it_server.py")],
        "transport": "stdio",
    },
}


class OnboardingOrchestrator:
    """
    Manages the LangGraph agent lifecycle and streaming interface.

    The agent is created once at startup with all MCP tools loaded.
    MemorySaver provides per-employee conversation persistence (thread_id = employee_id).
    """

    def __init__(self, agent, mcp_client: MultiServerMCPClient, tools: list):
        self._agent = agent
        self._mcp_client = mcp_client
        self._tools = tools
        logger.info("orchestrator.ready", tool_count=len(tools), tools=[t.name for t in tools])

    async def stream(
        self, employee_id: str, user_message: str
    ) -> AsyncIterator[dict]:
        """
        Run one conversation turn and yield structured SSE events:
          - {"type": "tool_call",   "tool": str, "server": str, "input": dict}
          - {"type": "tool_result", "tool": str, "output": str}
          - {"type": "text_delta",  "content": str}
          - {"type": "done"}
          - {"type": "error",       "message": str}
        """
        config = {"configurable": {"thread_id": employee_id}}

        # On the very first turn, prepend employee context so the agent knows whom to onboard
        state = await self._agent.aget_state(config)
        existing_messages = state.values.get("messages", [])
        is_first_turn = len(existing_messages) == 0

        content = (
            f"[Employee ID: {employee_id}]\n\n{user_message}"
            if is_first_turn
            else user_message
        )

        logger.info(
            "orchestrator.stream.start",
            employee_id=employee_id,
            first_turn=is_first_turn,
            message_preview=user_message[:80],
        )

        try:
            async for event in self._agent.astream_events(
                {"messages": [HumanMessage(content=content)]},
                config=config,
                version="v2",
            ):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, "content") and chunk.content:
                        raw = chunk.content
                        # LangGraph may return content blocks [{type, text, id}] instead of a string
                        if isinstance(raw, list):
                            text = "".join(
                                block.get("text", "") if isinstance(block, dict) else str(block)
                                for block in raw
                            )
                        else:
                            text = str(raw)
                        if text:
                            yield {"type": "text_delta", "content": text}

                elif kind == "on_tool_start":
                    tool_name = event.get("name", "unknown")
                    raw_input = event["data"].get("input", {})
                    # Ensure input is JSON-serializable
                    if not isinstance(raw_input, (dict, list, str)):
                        raw_input = str(raw_input)
                    server = _infer_server(tool_name)
                    logger.info("orchestrator.tool_call", tool=tool_name, server=server)
                    yield {
                        "type": "tool_call",
                        "tool": tool_name,
                        "server": server,
                        "input": raw_input,
                    }

                elif kind == "on_tool_end":
                    tool_name = event.get("name", "unknown")
                    output = event["data"].get("output", "")
                    # output may be a LangChain ToolMessage — extract .content
                    if hasattr(output, "content"):
                        output_str = output.content
                    elif isinstance(output, str):
                        output_str = output
                    else:
                        output_str = str(output)
                    logger.info("orchestrator.tool_result", tool=tool_name, output_len=len(output_str))
                    yield {
                        "type": "tool_result",
                        "tool": tool_name,
                        "output": output_str,
                    }

        except Exception as exc:
            logger.error("orchestrator.stream.error", error=str(exc), exc_info=True)
            yield {"type": "error", "message": str(exc)}

        yield {"type": "done"}

    async def get_history(self, employee_id: str) -> list[dict]:
        """Return the conversation history for a given employee."""
        config = {"configurable": {"thread_id": employee_id}}
        state = await self._agent.aget_state(config)
        messages = state.values.get("messages", [])
        history = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage) and msg.content:
                history.append({"role": "assistant", "content": msg.content})
        return history


def _infer_server(tool_name: str) -> str:
    """Map a tool name to the MCP server that provides it."""
    mapping = {
        "get_employee_profile": "hr",
        "update_hr_profile": "hr",
        "list_all_employees": "hr",
        "get_peers_by_role_and_level": "hr",
        "get_slack_profile": "slack",
        "update_slack_profile": "slack",
        "add_to_slack_channels": "slack",
        "get_salesforce_user": "salesforce",
        "update_salesforce_profile": "salesforce",
        "assign_salesforce_permission_set": "salesforce",
        "get_training_catalog": "training",
        "get_training_status": "training",
        "complete_training_module": "training",
        "get_access_recommendations": "it",
        "request_manager_approval": "it",
        "check_approval_status": "it",
        "submit_it_ticket": "it",
        "get_it_tickets": "it",
    }
    return mapping.get(tool_name, "unknown")


@asynccontextmanager
async def create_orchestrator() -> AsyncIterator[OnboardingOrchestrator]:
    """
    Async context manager that starts all MCP server subprocesses,
    loads their tools, builds the LangGraph agent, and yields the orchestrator.
    Cleans up subprocesses on exit.

    Note: as of langchain-mcp-adapters 0.1.0, MultiServerMCPClient is no longer
    an async context manager — tools are fetched via await client.get_tools().
    """
    model_id = os.getenv("MODEL_ID", "gpt-4o-mini")
    max_tokens = int(os.getenv("MAX_TOKENS", "4096"))

    llm = _build_llm(model_id, max_tokens)
    checkpointer = MemorySaver()

    logger.info("orchestrator.mcp.starting", servers=list(MCP_SERVERS_CONFIG.keys()))

    mcp_client = MultiServerMCPClient(MCP_SERVERS_CONFIG)
    tools = await mcp_client.get_tools()
    logger.info("orchestrator.mcp.tools_loaded", count=len(tools))

    agent = create_react_agent(
        model=llm,
        tools=tools,
        checkpointer=checkpointer,
        prompt=SYSTEM_PROMPT,
    )

    yield OnboardingOrchestrator(agent=agent, mcp_client=mcp_client, tools=tools)

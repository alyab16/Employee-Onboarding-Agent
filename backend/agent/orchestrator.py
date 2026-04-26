"""
LangGraph orchestrator — supervisor + specialists + human-in-the-loop.

Responsibilities:
  - Spawn MCP server subprocesses and discover their tools.
  - Wrap destructive tools so they pause for human approval (HITL).
  - Build four scoped specialist ReAct agents + a supervisor StateGraph.
  - Stream structured SSE events to the API layer:
        text_delta | tool_call | tool_result | agent_handoff |
        approval_required | done | error
  - Resume interrupted graph runs with an approval decision.

Per-employee conversation state is persisted via MemorySaver (thread_id =
employee_id). Interrupt state is checkpointed the same way, so approvals
survive across separate HTTP turns.
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncIterator, Any

from langchain_core.messages import HumanMessage, AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from agent.knowledge_tools import search_company_knowledge, list_knowledge_sources
from agent.hitl import wrap_tools
from agent.specialists import build_specialists, SPECIALIST_LABELS
from agent.supervisor import build_supervisor_graph
from utils.logger import get_logger


logger = get_logger("orchestrator")

_SERVERS_DIR = Path(__file__).parent.parent / "mcp_servers"

# Forward the parent process env to MCP stdio subprocesses. Without this the
# MCP client ships only a minimal env and children miss DB_PATH/CHROMA_PATH,
# causing each subprocess to open its own SQLite file at the default path —
# so the backend's seeded DB and the MCP tools' DB end up disjoint.
_MCP_ENV = os.environ.copy()

MCP_SERVERS_CONFIG = {
    "hr":         {"command": "python", "args": [str(_SERVERS_DIR / "hr_server.py")],         "transport": "stdio", "env": _MCP_ENV},
    "slack":      {"command": "python", "args": [str(_SERVERS_DIR / "slack_server.py")],      "transport": "stdio", "env": _MCP_ENV},
    "salesforce": {"command": "python", "args": [str(_SERVERS_DIR / "salesforce_server.py")], "transport": "stdio", "env": _MCP_ENV},
    "training":   {"command": "python", "args": [str(_SERVERS_DIR / "training_server.py")],   "transport": "stdio", "env": _MCP_ENV},
    "it":         {"command": "python", "args": [str(_SERVERS_DIR / "it_server.py")],         "transport": "stdio", "env": _MCP_ENV},
}

KNOWLEDGE_TOOLS = [search_company_knowledge, list_knowledge_sources]


TOOL_TO_SERVER: dict[str, str] = {
    "get_employee_profile":             "hr",
    "update_hr_profile":                "hr",
    "list_all_employees":               "hr",
    "get_peers_by_role_and_level":      "hr",
    "get_slack_profile":                "slack",
    "update_slack_profile":             "slack",
    "add_to_slack_channels":            "slack",
    "get_salesforce_user":              "salesforce",
    "update_salesforce_profile":        "salesforce",
    "assign_salesforce_permission_set": "salesforce",
    "get_training_catalog":             "training",
    "get_training_status":              "training",
    "complete_training_module":         "training",
    "get_access_recommendations":       "it",
    "request_manager_approval":         "it",
    "check_approval_status":            "it",
    "submit_it_ticket":                 "it",
    "get_it_tickets":                   "it",
    "search_company_knowledge":         "knowledge",
    "list_knowledge_sources":           "knowledge",
}


def _build_llm(model_id: str, max_tokens: int):
    """OpenAI if OPENAI_API_KEY is set, else Ollama."""
    if os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI

        logger.info("llm.provider", provider="openai", model=model_id)
        return ChatOpenAI(model=model_id, temperature=0, streaming=True, max_tokens=max_tokens)

    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        raise RuntimeError(
            "No OPENAI_API_KEY set and langchain-ollama is not installed."
        )

    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    logger.info("llm.provider", provider="ollama", model=ollama_model)
    return ChatOllama(model=ollama_model, base_url=ollama_base_url, temperature=0)


def _extract_text(raw: Any) -> str:
    """LangGraph chunks may be string or content-block list; coerce to str."""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in raw
        )
    return str(raw) if raw else ""


class OnboardingOrchestrator:
    """
    Manages the supervisor graph lifecycle and streaming / resume interface.

    All write-capable tools are wrapped with `interrupt()` so the user must
    approve every destructive action. When the graph pauses, an
    `approval_required` event is emitted and the stream ends; the API layer
    picks it back up via `resume()`.
    """

    def __init__(
        self,
        graph,
        checkpointer,
        mcp_client: MultiServerMCPClient,
        tools: list,
        specialists: dict,
    ):
        self._graph = graph
        self._checkpointer = checkpointer
        self._mcp_client = mcp_client
        self._tools = tools
        self._specialists = specialists
        self._real_tool_names = {t.name for t in tools}
        logger.info(
            "orchestrator.ready",
            tool_count=len(tools),
            specialists=list(specialists.keys()),
        )

    # ---------------------------------------------------------------- public

    async def stream(
        self,
        employee_id: str,
        user_message: str,
        thread_id: str | None = None,
    ) -> AsyncIterator[dict]:
        """Run one user turn; yield SSE events until idle or interrupted."""
        config = {"configurable": {"thread_id": thread_id or employee_id}}

        state = await self._graph.aget_state(config)
        existing = (state.values or {}).get("messages", []) if state else []
        is_first_turn = len(existing) == 0

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

        graph_input = {"messages": [HumanMessage(content=content)]}
        async for event in self._emit_events(graph_input, config, employee_id):
            yield event

    async def resume(
        self,
        employee_id: str,
        decision: dict,
        thread_id: str | None = None,
    ) -> AsyncIterator[dict]:
        """Resume an interrupted run with the user's approval decision."""
        config = {"configurable": {"thread_id": thread_id or employee_id}}
        logger.info(
            "orchestrator.resume.start",
            employee_id=employee_id,
            approved=bool(decision.get("approved")),
        )
        async for event in self._emit_events(Command(resume=decision), config, employee_id):
            yield event

    async def reset_thread(self, employee_id: str) -> None:
        """
        Wipe all checkpointed state for an employee's thread. Called by the
        frontend "Restart" button so the agent's memory matches what the user
        sees in the UI; otherwise the supervisor sees stale history (including
        possibly a pending interrupt) and behaves unpredictably.
        """
        thread_id = employee_id

        if hasattr(self._checkpointer, "adelete_thread"):
            await self._checkpointer.adelete_thread(thread_id)
        elif hasattr(self._checkpointer, "delete_thread"):
            self._checkpointer.delete_thread(thread_id)
        else:
            # Fallback for older MemorySaver: clear internal dicts directly.
            for attr in ("storage", "writes", "blobs"):
                d = getattr(self._checkpointer, attr, None)
                if isinstance(d, dict):
                    d.pop(thread_id, None)

        logger.info("orchestrator.thread.reset", employee_id=employee_id)

    async def get_history(self, employee_id: str) -> list[dict]:
        """Return the visible conversation history for an employee."""
        config = {"configurable": {"thread_id": employee_id}}
        state = await self._graph.aget_state(config)
        messages = (state.values or {}).get("messages", []) if state else []

        history: list[dict] = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                # Strip the [Employee ID: ...] prefix injected on the first turn.
                text = msg.content
                if isinstance(text, str) and text.startswith("[Employee ID:"):
                    text = text.split("\n\n", 1)[-1]
                history.append({"role": "user", "content": text})
            elif isinstance(msg, AIMessage) and msg.content:
                history.append({
                    "role": "assistant",
                    "content": msg.content,
                    "specialist": msg.additional_kwargs.get("specialist") if msg.additional_kwargs else None,
                })
        return history

    # --------------------------------------------------------------- private

    async def _emit_events(self, graph_input: Any, config: dict, employee_id: str) -> AsyncIterator[dict]:
        last_specialist: str | None = None

        try:
            async for event in self._graph.astream_events(graph_input, config, version="v2"):
                meta = event.get("metadata") or {}
                node = meta.get("langgraph_node")
                kind = event["event"]

                # Emit a handoff banner the first time we see a new specialist.
                if node in SPECIALIST_LABELS and node != last_specialist:
                    yield {
                        "type": "agent_handoff",
                        "specialist": node,
                        "label": SPECIALIST_LABELS[node],
                    }
                    last_specialist = node

                # Supervisor-owned events (structured-output LLM calls, etc.)
                # never reach the user.
                if node == "supervisor":
                    continue

                if kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    text = _extract_text(getattr(chunk, "content", "")) if chunk else ""
                    if text:
                        yield {"type": "text_delta", "content": text}

                elif kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    # Skip events for the supervisor's structured-output schema
                    # and for subgraph entry (name matches a specialist).
                    if tool_name not in self._real_tool_names:
                        continue
                    raw_input = event["data"].get("input", {}) or {}
                    if not isinstance(raw_input, (dict, list, str)):
                        raw_input = str(raw_input)
                    server = TOOL_TO_SERVER.get(tool_name, "unknown")
                    logger.info("orchestrator.tool_call", tool=tool_name, server=server)
                    yield {
                        "type": "tool_call",
                        "tool": tool_name,
                        "server": server,
                        "input": raw_input,
                    }

                elif kind == "on_tool_end":
                    tool_name = event.get("name", "")
                    if tool_name not in self._real_tool_names:
                        continue
                    output = event["data"].get("output", "")
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
            return

        # After the stream idles, check for a pending interrupt. If present,
        # surface it to the client and STOP — the stream resumes on /resume.
        pending = await self._pending_interrupts(config)
        if pending:
            for item in pending:
                logger.info("orchestrator.interrupt.pending", employee_id=employee_id, payload=item)
                yield {"type": "approval_required", **item}
            yield {"type": "awaiting_approval"}
            return

        yield {"type": "done"}

    async def _pending_interrupts(self, config: dict) -> list[dict]:
        """Return serialised interrupt payloads blocking the current run."""
        state = await self._graph.aget_state(config)
        if not state:
            return []

        pending: list[dict] = []
        for task in state.tasks or []:
            for intr in getattr(task, "interrupts", None) or []:
                value = getattr(intr, "value", None) or {}
                if not isinstance(value, dict):
                    value = {"payload": value}
                entry = {"interrupt_id": getattr(intr, "id", None), **value}
                pending.append(entry)
        return pending


@asynccontextmanager
async def create_orchestrator() -> AsyncIterator[OnboardingOrchestrator]:
    """
    Start MCP subprocesses, discover tools, wrap destructive ones with HITL,
    build specialists + supervisor graph, and yield an orchestrator.
    """
    model_id = os.getenv("MODEL_ID", "gpt-4o-mini")
    max_tokens = int(os.getenv("MAX_TOKENS", "4096"))

    llm = _build_llm(model_id, max_tokens)
    checkpointer = MemorySaver()

    logger.info("orchestrator.mcp.starting", servers=list(MCP_SERVERS_CONFIG.keys()))
    mcp_client = MultiServerMCPClient(MCP_SERVERS_CONFIG)
    mcp_tools = await mcp_client.get_tools()
    logger.info("orchestrator.mcp.tools_loaded", count=len(mcp_tools))

    all_tools_raw = mcp_tools + KNOWLEDGE_TOOLS
    all_tools = wrap_tools(all_tools_raw)
    logger.info(
        "orchestrator.all_tools",
        count=len(all_tools),
        mcp=len(mcp_tools),
        knowledge=len(KNOWLEDGE_TOOLS),
    )

    specialists = build_specialists(llm, all_tools)
    graph = build_supervisor_graph(llm, specialists, checkpointer=checkpointer)

    yield OnboardingOrchestrator(
        graph=graph,
        checkpointer=checkpointer,
        mcp_client=mcp_client,
        tools=all_tools,
        specialists=specialists,
    )

"""
Supervisor StateGraph.

Outer multi-agent orchestration:

    START → supervisor → <one_specialist> ─┐
              ▲                            │
              └────────────────────────────┘
                      (loop until FINISH or hop cap)

The supervisor node uses an LLM with structured output to pick the next
specialist (or FINISH). It never produces user-visible text; all assistant
output comes from the specialists. Each specialist completes its turn, appends
its messages to shared state, and returns control to the supervisor, which may
route once more (to cover multi-domain requests) or end the run.

A soft hop cap (`MAX_HOPS_PER_TURN`) prevents runaway routing loops.
"""

import warnings
from typing import Literal

from pydantic import BaseModel, Field
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.types import Command

from agent.prompts import SUPERVISOR_PROMPT
from agent.specialists import SPECIALIST_LABELS

# LangChain's `with_structured_output` attaches the parsed pydantic object to an
# internal `parsed` field whose declared type is narrower than the runtime value,
# so pydantic v2 emits a harmless UserWarning every time the supervisor routes.
# The warning is cosmetic — filter it at the source.
warnings.filterwarnings(
    "ignore",
    message=r".*Pydantic serializer warnings.*",
    category=UserWarning,
    module=r"pydantic\.main",
)


SPECIALIST_NAMES = tuple(SPECIALIST_LABELS.keys())
MAX_HOPS_PER_TURN = 3


class Route(BaseModel):
    """Supervisor routing decision."""
    next: Literal["hr_profile", "training", "it_access", "knowledge", "FINISH"] = Field(
        description="Which specialist should handle the latest user turn, or FINISH."
    )
    reasoning: str = Field(description="One sentence justifying the choice.")


class SupervisorState(MessagesState):
    """Shared state for the outer supervisor graph."""
    current_specialist: str | None


def _hops_since_last_human(messages: list) -> int:
    """
    Count finalised specialist responses since the most recent HumanMessage.
    A finalised response is an AIMessage with text content and no pending tool_calls.
    """
    count = 0
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return count
        if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
            count += 1
    return count


def build_supervisor_graph(
    llm: BaseChatModel,
    specialists: dict,
    checkpointer: BaseCheckpointSaver,
):
    """
    Compile the outer supervisor graph.

    Args:
        llm: the chat model used by the supervisor to pick a route.
        specialists: {name: compiled ReAct agent}. Keys must match SPECIALIST_NAMES.
        checkpointer: persistence for interrupt/resume across HTTP turns.
    """
    router_llm = llm.with_structured_output(Route)

    async def supervisor_node(state: SupervisorState) -> Command:
        hops = _hops_since_last_human(state["messages"])
        if hops >= MAX_HOPS_PER_TURN:
            # Safety net — end the turn even if the LLM would keep routing.
            return Command(goto=END, update={"current_specialist": None})

        decision: Route = await router_llm.ainvoke(
            [SystemMessage(content=SUPERVISOR_PROMPT)] + state["messages"]
        )

        if decision.next == "FINISH":
            return Command(goto=END, update={"current_specialist": None})

        return Command(
            goto=decision.next,
            update={"current_specialist": decision.next},
        )

    def _make_specialist_node(name: str, agent):
        async def node(state: SupervisorState) -> Command:
            prior_len = len(state["messages"])
            result = await agent.ainvoke({"messages": state["messages"]})
            new_msgs = result["messages"][prior_len:]

            # Tag each new message with the specialist that produced it so the
            # frontend can show which agent handled the turn.
            for msg in new_msgs:
                if hasattr(msg, "additional_kwargs"):
                    msg.additional_kwargs.setdefault("specialist", name)

            return Command(
                goto="supervisor",
                update={"messages": new_msgs, "current_specialist": None},
            )
        node.__name__ = f"{name}_node"
        return node

    graph = StateGraph(SupervisorState)
    graph.add_node("supervisor", supervisor_node)
    for name in SPECIALIST_NAMES:
        if name not in specialists:
            raise ValueError(f"Missing specialist '{name}' in build_supervisor_graph")
        graph.add_node(name, _make_specialist_node(name, specialists[name]))

    graph.add_edge(START, "supervisor")
    return graph.compile(checkpointer=checkpointer)

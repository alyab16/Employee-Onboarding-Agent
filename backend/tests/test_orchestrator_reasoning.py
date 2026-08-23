import unittest
from types import SimpleNamespace

from langchain_core.messages import AIMessage

from agent.orchestrator import OnboardingOrchestrator


class FakeGraph:
    def __init__(self, events=None, state=None):
        self._events = events or []
        self._state = state

    async def astream_events(self, graph_input, config, version):
        for event in self._events:
            yield event

    async def aget_state(self, config):
        return self._state


def model_event(kind, run_id, content=""):
    return {
        "event": kind,
        "run_id": run_id,
        "metadata": {"langgraph_node": "hr_profile"},
        "data": {"chunk": SimpleNamespace(content=content)},
    }


def build_orchestrator(graph):
    orchestrator = OnboardingOrchestrator.__new__(OnboardingOrchestrator)
    orchestrator._graph = graph
    orchestrator._real_tool_names = set()
    return orchestrator


class OrchestratorReasoningTests(unittest.IsolatedAsyncioTestCase):
    async def test_stream_never_emits_thinking_content(self):
        graph = FakeGraph(
            events=[
                model_event("on_chat_model_stream", "call-1", "<thi"),
                model_event("on_chat_model_stream", "call-1", "nking>private"),
                model_event("on_chat_model_stream", "call-1", "</thinking>Hello"),
                model_event("on_chat_model_end", "call-1"),
            ]
        )
        orchestrator = build_orchestrator(graph)

        events = [
            event
            async for event in orchestrator._emit_events({}, {}, "emp001")
        ]
        text_events = [event for event in events if event["type"] == "text_delta"]

        self.assertEqual(
            text_events,
            [{"type": "text_delta", "content": "Hello"}],
        )
        self.assertEqual(events[-1], {"type": "done"})

    async def test_unterminated_thinking_does_not_hide_next_model_call(self):
        graph = FakeGraph(
            events=[
                model_event("on_chat_model_stream", "call-1", "<thinking>private"),
                model_event("on_chat_model_end", "call-1"),
                model_event("on_chat_model_stream", "call-2", "Visible answer"),
                model_event("on_chat_model_end", "call-2"),
            ]
        )
        orchestrator = build_orchestrator(graph)

        events = [
            event
            async for event in orchestrator._emit_events({}, {}, "emp001")
        ]
        text_events = [event for event in events if event["type"] == "text_delta"]

        self.assertEqual(
            text_events,
            [{"type": "text_delta", "content": "Visible answer"}],
        )

    async def test_history_excludes_thinking_only_messages(self):
        state = SimpleNamespace(
            values={
                "messages": [
                    AIMessage(content="<thinking>tool plan</thinking>"),
                    AIMessage(content="<thinking>private</thinking>Final answer"),
                ]
            }
        )
        orchestrator = build_orchestrator(FakeGraph(state=state))

        history = await orchestrator.get_history("emp001")

        self.assertEqual(
            history,
            [{"role": "assistant", "content": "Final answer", "specialist": None}],
        )


if __name__ == "__main__":
    unittest.main()

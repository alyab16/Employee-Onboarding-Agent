"""
Chat API endpoints.

POST /api/chat          → SSE stream of agent events
GET  /api/chat/history  → Conversation history for an employee
"""

import json
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from utils.logger import get_logger

logger = get_logger("api.chat")
router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    employee_id: str
    message: str


async def _sse_event(data: dict) -> str:
    """Format a dict as a Server-Sent Events data line."""
    return f"data: {json.dumps(data)}\n\n"


@router.post("")
async def chat(request: Request, body: ChatRequest):
    """
    Send a message to the onboarding agent and receive a streaming SSE response.

    Event types emitted:
      - text_delta   → partial assistant token
      - tool_call    → agent is calling an MCP tool
      - tool_result  → result returned from MCP server
      - done         → stream complete
      - error        → something went wrong
    """
    orchestrator = request.app.state.orchestrator

    if not body.employee_id or not body.message.strip():
        raise HTTPException(status_code=400, detail="employee_id and message are required.")

    logger.info("api.chat.request", employee_id=body.employee_id, message_len=len(body.message))

    async def event_generator():
        try:
            async for event in orchestrator.stream(body.employee_id, body.message):
                yield await _sse_event(event)
        except Exception as exc:
            logger.error("api.chat.stream_error", error=str(exc), exc_info=True)
            yield await _sse_event({"type": "error", "message": "Internal server error."})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/history")
async def get_history(request: Request, employee_id: str):
    """Return the full conversation history for an employee."""
    orchestrator = request.app.state.orchestrator
    history = await orchestrator.get_history(employee_id)
    return {"employee_id": employee_id, "messages": history}

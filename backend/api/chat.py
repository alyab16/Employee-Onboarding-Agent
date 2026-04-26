"""
Chat API endpoints.

POST /api/chat           → SSE stream; runs one turn of the supervisor graph.
POST /api/chat/resume    → SSE stream; resumes an interrupted run with an
                           approval decision (HITL).
GET  /api/chat/history   → Visible conversation history for an employee.
"""

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from utils.logger import get_logger

logger = get_logger("api.chat")
router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    employee_id: str
    message: str


class ResumeRequest(BaseModel):
    employee_id: str
    approved: bool
    reason: str = ""
    edited_args: dict[str, Any] = Field(default_factory=dict)


async def _sse_event(data: dict) -> str:
    """Format a dict as a single Server-Sent Events data frame."""
    return f"data: {json.dumps(data)}\n\n"


@router.post("")
async def chat(request: Request, body: ChatRequest):
    """
    Send a message to the supervisor and receive a streaming SSE response.

    Event types emitted:
      - agent_handoff      → supervisor routed to a specialist
      - text_delta         → partial assistant token from a specialist
      - tool_call          → agent is invoking a tool
      - tool_result        → tool returned
      - approval_required  → destructive tool is gated; client must POST /resume
      - awaiting_approval  → terminator indicating the stream paused on approval
      - done               → stream completed normally
      - error              → something went wrong
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


@router.post("/resume")
async def resume(request: Request, body: ResumeRequest):
    """
    Resume an interrupted run with the user's approval decision.
    Emits the same SSE event shapes as /api/chat.
    """
    orchestrator = request.app.state.orchestrator

    if not body.employee_id:
        raise HTTPException(status_code=400, detail="employee_id is required.")

    logger.info(
        "api.chat.resume",
        employee_id=body.employee_id,
        approved=body.approved,
    )

    decision = {
        "approved": body.approved,
        "reason": body.reason,
        "edited_args": body.edited_args or {},
    }

    async def event_generator():
        try:
            async for event in orchestrator.resume(body.employee_id, decision):
                yield await _sse_event(event)
        except Exception as exc:
            logger.error("api.chat.resume_error", error=str(exc), exc_info=True)
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
    """Return the full visible conversation history for an employee."""
    orchestrator = request.app.state.orchestrator
    history = await orchestrator.get_history(employee_id)
    return {"employee_id": employee_id, "messages": history}


@router.delete("/history")
async def reset_history(request: Request, employee_id: str):
    """
    Wipe checkpointed conversation state for an employee. The frontend's
    "Restart" button calls this so backend memory matches the cleared UI;
    otherwise the next turn runs against stale history (including any pending
    HITL interrupt) and the agent can silently produce no response.
    """
    if not employee_id:
        raise HTTPException(status_code=400, detail="employee_id is required.")
    orchestrator = request.app.state.orchestrator
    logger.info("api.chat.reset", employee_id=employee_id)
    await orchestrator.reset_thread(employee_id)
    return {"employee_id": employee_id, "reset": True}

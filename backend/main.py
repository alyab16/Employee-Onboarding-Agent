"""
Acme Corp — Employee Onboarding Agent
FastAPI application entry point.

Architecture:
  - 5 FastMCP servers (HR, Slack, Salesforce, Training, IT) started as subprocesses
  - langchain-mcp-adapters loads all tools at startup via MultiServerMCPClient
  - LangGraph ReAct agent orchestrates tool calls with per-employee state (MemorySaver)
  - SSE streaming endpoint delivers real-time agent events to the Next.js frontend
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent.orchestrator import create_orchestrator
from api.chat import router as chat_router
from api.admin import router as admin_router
from utils.logger import get_logger, setup_logging

load_dotenv()
setup_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan:
      startup  → launch MCP subprocesses, load tools, build LangGraph agent
      shutdown → gracefully terminate MCP subprocesses
    """
    logger.info("app.startup", model=os.getenv("MODEL_ID", "gpt-4o-mini"))
    async with create_orchestrator() as orchestrator:
        app.state.orchestrator = orchestrator
        logger.info("app.ready")
        yield
    logger.info("app.shutdown")


app = FastAPI(
    title="Employee Onboarding Agent",
    description="AI-powered HR onboarding assistant using LangGraph + FastMCP",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the Next.js dev server
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(admin_router)


@app.get("/health")
async def health():
    return {"status": "ok"}

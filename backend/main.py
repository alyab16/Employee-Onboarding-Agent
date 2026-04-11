"""
Acme Corp — Employee Onboarding Agent
FastAPI application entry point.

Startup sequence:
  1. init_db()          — create SQLite tables (no-op if already exist)
  2. seed_all()         — populate tables from mock data (no-op if already seeded)
  3. init_vector_store()— index knowledge docs into ChromaDB (skips if docs unchanged)
  4. create_orchestrator() — spawn 6 FastMCP subprocesses, load tools, build LangGraph agent
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.engine import init_db
from database.seed import seed_all
from knowledge.vector_store import init_vector_store
from agent.orchestrator import create_orchestrator
from api.chat import router as chat_router
from api.admin import router as admin_router
from utils.logger import get_logger, setup_logging

load_dotenv()
setup_logging()
logger = get_logger("main")


def _configure_langsmith() -> None:
    """
    Enable LangSmith tracing when LANGCHAIN_API_KEY is set in .env.
    All env vars are read automatically by the LangChain SDK — we just
    log whether tracing is active so it's visible at startup.
    """
    if os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true" and os.getenv("LANGCHAIN_API_KEY"):
        project = os.getenv("LANGCHAIN_PROJECT", "employee-onboarding-agent")
        logger.info("langsmith.tracing_enabled", project=project)
    else:
        logger.info("langsmith.tracing_disabled", hint="Set LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY to enable")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_langsmith()
    logger.info("app.startup", model=os.getenv("MODEL_ID", "gpt-4o-mini"))

    # 1. Database
    logger.info("app.db.init")
    init_db()

    # 2. Seed structured data
    logger.info("app.db.seed")
    seed_all()

    # 3. Vector store (skips rebuild if docs unchanged)
    logger.info("app.vectorstore.init")
    init_vector_store()

    # 4. MCP servers + LangGraph agent
    async with create_orchestrator() as orchestrator:
        app.state.orchestrator = orchestrator
        logger.info("app.ready")
        yield

    logger.info("app.shutdown")


app = FastAPI(
    title="Employee Onboarding Agent",
    description="AI-powered HR onboarding assistant — LangGraph + FastMCP + SQLite + ChromaDB",
    version="1.0.0",
    lifespan=lifespan,
)

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

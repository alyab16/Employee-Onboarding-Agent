"""
SQLModel engine shared across all processes that import this module.
Each MCP subprocess gets its own engine instance pointing to the same file.
"""

from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session

DB_PATH = Path(__file__).parent.parent / "data.db"
_engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})


def get_engine():
    return _engine


def init_db():
    """Create all tables (no-op if they already exist)."""
    SQLModel.metadata.create_all(_engine)


def get_session() -> Session:
    """Return a new session. Caller is responsible for closing it."""
    return Session(_engine, expire_on_commit=False)

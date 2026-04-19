"""
SQLModel engine shared across all processes that import this module.
Each MCP subprocess gets its own engine instance pointing to the same file.
"""

import os
from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.exc import OperationalError

# DB_PATH defaults to <repo>/backend/data.db for local dev. When running in
# Docker, DB_PATH is set to a path inside a mounted volume (e.g. /app/data/data.db)
# so the SQLite file survives container restarts.
DB_PATH = Path(os.getenv("DB_PATH") or (Path(__file__).parent.parent / "data.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
_engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})


def get_engine():
    return _engine


def init_db():
    """
    Create all tables (no-op if they already exist).

    The 5 MCP subprocesses all import this module at startup and race on
    ``create_all``. SQLAlchemy's ``checkfirst=True`` is not atomic with the
    CREATE statement, so two processes can both observe "tables missing"
    and the loser hits "table already exists". Swallow that one error and
    let any other OperationalError propagate.
    """
    try:
        SQLModel.metadata.create_all(_engine)
    except OperationalError as e:
        if "already exists" not in str(e).lower():
            raise


def get_session() -> Session:
    """Return a new session. Caller is responsible for closing it."""
    return Session(_engine, expire_on_commit=False)

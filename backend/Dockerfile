# syntax=docker/dockerfile:1.7

# ---- base ----------------------------------------------------------------
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Native deps used by chromadb, rank-bm25, tokenizers, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Ship uv from its official image (fast and always available).
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /usr/local/bin/

WORKDIR /app

# ---- deps (cached layer) -------------------------------------------------
# Only the lock files go in first so `uv sync` is cached whenever the
# application source changes but dependencies don't.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# ---- application ---------------------------------------------------------
COPY . .

# Writable directories that the app expects at runtime. docker-compose
# mounts named volumes over these so state survives container restarts.
RUN mkdir -p /app/data /app/chroma_db /app/logs

ENV DB_PATH=/app/data/data.db \
    CHROMA_PATH=/app/chroma_db \
    HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

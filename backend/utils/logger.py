"""
Logging setup: structlog for structured output.
- Console: pretty-printed in dev (TTY), JSON in prod
- File:    logs/app.log — rotating, JSON, always enabled
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog

LOGS_DIR = Path(__file__).parent.parent / "logs"


def setup_logging() -> None:
    LOGS_DIR.mkdir(exist_ok=True)

    shared_processors = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=shared_processors
        + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Console handler — pretty in dev, JSON in prod
    console_renderer = (
        structlog.dev.ConsoleRenderer(colors=True)
        if sys.stdout.isatty()
        else structlog.processors.JSONRenderer()
    )
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            console_renderer,
        ],
        foreign_pre_chain=shared_processors,
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    # File handler — always JSON, rotating (10 MB × 5 backups)
    file_formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
        foreign_pre_chain=shared_processors,
    )
    file_handler = RotatingFileHandler(
        filename=LOGS_DIR / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(file_formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)

    # Silence noisy third-party loggers
    for noisy in ("httpx", "httpcore", "chromadb", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)

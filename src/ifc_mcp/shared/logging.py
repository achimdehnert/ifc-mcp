"""Structured logging configuration.

Uses structlog for structured logging with JSON or console output.
"""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from ifc_mcp.shared.config import settings


def setup_logging() -> None:
    """Configure structured logging based on settings."""
    # Determine processors based on format
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ExtraAdder(),
    ]

    if settings.log_format == "json":
        # JSON format for production
        processors: list[Processor] = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Console format for development
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            ),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )

    # Reduce noise from libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.INFO)


def get_logger(name: str | None = None, **initial_context: Any) -> structlog.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)
        **initial_context: Initial context to bind to logger

    Returns:
        Bound structlog logger
    """
    logger = structlog.get_logger(name)
    if initial_context:
        logger = logger.bind(**initial_context)
    return logger


# Convenience alias
logger = get_logger("ifc_mcp")

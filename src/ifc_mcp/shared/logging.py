"""Structured logging configuration.

Uses structlog for structured, contextual logging.
"""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

_configured = False


def configure_logging(
    level: str = "INFO",
    log_format: str = "json",
    log_file: str | None = None,
) -> None:
    """Configure structured logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ("json" or "console")
        log_file: Optional log file path
    """
    global _configured
    if _configured:
        return

    # Shared processors
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper()))

    # Reduce noise from external libraries
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    _configured = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Bound structured logger
    """
    if not _configured:
        from ifc_mcp.shared.config import settings
        configure_logging(
            level=settings.log_level,
            log_format=settings.log_format,
            log_file=settings.log_file,
        )

    return structlog.get_logger(name)

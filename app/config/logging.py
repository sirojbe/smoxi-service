"""
Logging configuration for SMOXI Service using Loguru.

Provides a single entry point to configure sinks (console + rotating files).
Call `configure_logging()` once during application bootstrap.
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from app.config.settings import get_settings


def configure_logging(
    *,
    level: str | None = None,
    logs_dir: Path | None = None,
) -> None:
    """
    Configure Loguru sinks for the current process.

    Parameters
    ----------
    level:
        Optional log level override (e.g. ``DEBUG``, ``INFO``).
        Defaults to ``DEBUG`` in development and ``INFO`` otherwise.
    logs_dir:
        Optional directory for log files. Defaults to settings.logs_dir.
    """
    settings = get_settings()
    resolved_dir = logs_dir or settings.logs_dir
    resolved_dir.mkdir(parents=True, exist_ok=True)

    resolved_level = level or ("DEBUG" if settings.debug else "INFO")

    # Remove default sink so configuration is deterministic.
    logger.remove()

    # Console sink — human-readable for desktop development.
    logger.add(
        sys.stderr,
        level=resolved_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        enqueue=True,
        backtrace=settings.debug,
        diagnose=settings.debug,
    )

    # Rotating file sink — retained for support and diagnostics.
    logger.add(
        resolved_dir / "smoxi_{time:YYYY-MM-DD}.log",
        level=resolved_level,
        rotation="00:00",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=settings.debug,
    )


def get_logger(name: str | None = None):
    """
    Return a Loguru logger bound with an optional component name.

    Prefer this helper over importing ``logger`` directly when a named context
    improves traceability across modules.
    """
    if name:
        return logger.bind(component=name)
    return logger

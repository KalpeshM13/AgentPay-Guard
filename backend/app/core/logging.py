"""Logging configuration.

Provides a pre-configured logger for the application.
Supports both human-readable text output (with ANSI colours) and
structured JSON output for log aggregators.

Called once at startup by ``app/main.py``.
"""

import logging
import sys

from app.core.config import settings


class _ColourFormatter(logging.Formatter):
    """Adds ANSI colours for terminal readability (text mode only)."""

    COLOURS: dict[int, str] = {
        logging.DEBUG: "\033[36m",
        logging.INFO: "\033[32m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[1;31m",
    }
    RESET: str = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        colour = self.COLOURS.get(record.levelno, "")
        if colour:
            record.levelname = f"{colour}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging() -> None:
    """Configure the root logger.

    Must be called once before any logging output.  Idempotent on
    repeated calls (handlers are cleared first).
    """
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)

    # Clear any handlers attached by uvicorn or third-party libraries
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(settings.LOG_LEVEL)

    if settings.LOG_FORMAT == "json":
        handler.setFormatter(
            logging.Formatter(
                '{"time":"%(asctime)s","level":"%(levelname)s",'
                '"logger":"%(name)s","message":"%(message)s"}',
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
    else:
        handler.setFormatter(
            _ColourFormatter(
                "%(asctime)s  %(levelname)-18s  %(name)s  %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root.addHandler(handler)

    # Quiet noisy third-party loggers
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DB_ECHO else logging.WARNING
    )

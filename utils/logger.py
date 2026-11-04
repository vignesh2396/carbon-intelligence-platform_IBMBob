"""
utils/logger.py
───────────────────────────────────────────────────────────────────────────────
Purpose:  Structured JSON logger for all agent activity.
          Every agent decision, tool call, and LLM invocation is recorded
          with timestamp, agent name, action, inputs, and outputs.
          This provides the audit trail required by the security architecture.

Dependencies: Python standard library only (logging, json)
"""

import logging
import json
import os
from datetime import datetime, timezone
from typing import Any

# ── Configuration ─────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE  = os.getenv("LOG_FILE", "./logs/agent_activity.log")

# Ensure log directory exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


class StructuredFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level":     record.levelname,
            "agent":     getattr(record, "agent", "system"),
            "action":    getattr(record, "action", ""),
            "message":   record.getMessage(),
        }
        # Include any extra structured fields passed by the caller
        for key in ("inputs", "outputs", "confidence", "sources", "warning"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, default=str)


def get_logger(agent_name: str) -> logging.Logger:
    """
    Return a configured logger for the given agent name.

    Usage:
        log = get_logger("CarbonAccountingAgent")
        log.info("Calculating emissions", extra={"action": "calculate", "inputs": data})
    """
    logger = logging.getLogger(agent_name)
    if logger.handlers:
        return logger  # avoid duplicate handlers on re-import

    logger.setLevel(LOG_LEVEL)

    # File handler — structured JSON
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(StructuredFormatter())
    logger.addHandler(fh)

    # Console handler — human-readable during development
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(name)s] %(levelname)s — %(message)s",
        datefmt="%H:%M:%S"
    ))
    logger.addHandler(ch)

    return logger

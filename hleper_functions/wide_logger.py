import json
import logging
import os
import sys
import time
from typing import Any, Optional


def setup_logger(log_path: Optional[str] = None) -> logging.Logger:
    """
    Configure a logger that emits structured JSON messages.
    Always logs to console, and optionally to a file if log_path is provided.
    """
    logger = logging.getLogger("hb_monitor")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter("%(message)s")

        # 1. Always add Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 2. Optionally add File Handler
        if log_path:
            full_path = os.path.expanduser(log_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            file_handler = logging.FileHandler(full_path, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        logger.propagate = False
    return logger


def log_event(logger: logging.Logger, level: str, event: str, **fields: Any) -> None:
    """
    Emit a single-line JSON event with consistent fields for observability.
    """
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    payload = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "level": level.upper(),
        "event": event,
        **fields,
    }
    logger.log(level_map.get(level.upper(), logging.INFO), json.dumps(payload, ensure_ascii=False))



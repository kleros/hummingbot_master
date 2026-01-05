import json
import logging
import os
import sys
import time
from typing import Any, Optional


def setup_logger(log_path: Optional[str] = None) -> logging.Logger:
    """
    Configure a logger that emits structured JSON messages (wide event logs).
    """
    logger = logging.getLogger("hb_monitor")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        if log_path:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            handler = logging.FileHandler(log_path, encoding="utf-8")
        else:
            handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
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



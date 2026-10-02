"""Structured JSON logging with request_id and execution_id context propagation."""

import contextvars
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

# Context variables for request tracking
current_request_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_request_id", default=""
)
current_execution_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_execution_id", default=""
)

SENSITIVE_KEYS = {
    "authorization",
    "api_auth_token",
    "admin_auth_token",
    "password",
    "token",
    "secret",
}


def sanitize_dict(data: Any) -> Any:
    """Recursively scrub sensitive keys from log payloads."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if str(k).lower() in SENSITIVE_KEYS:
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, (dict, list)):
                sanitized[k] = sanitize_dict(v)
            else:
                sanitized[k] = v
        return sanitized
    elif isinstance(data, list):
        return [sanitize_dict(item) for item in data]
    return data


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON entries."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Inject context variables if available
        req_id = current_request_id.get("")
        if req_id:
            log_entry["request_id"] = req_id

        exec_id = current_execution_id.get("")
        if exec_id:
            log_entry["execution_id"] = exec_id

        # Attach custom extra properties passed to logger
        if hasattr(record, "event"):
            log_entry["event"] = record.event
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        if hasattr(record, "tool"):
            log_entry["tool"] = record.tool
        if hasattr(record, "status"):
            log_entry["status"] = record.status
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_entry["data"] = sanitize_dict(record.extra_data)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logging(log_level: str = "INFO") -> None:
    """Configure root logger with StructuredJsonFormatter."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers to prevent duplicate lines
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())
    root_logger.addHandler(handler)

    # Silence overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.INFO)


logger = logging.getLogger("copilot")

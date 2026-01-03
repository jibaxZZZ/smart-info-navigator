"""Production-ready logging configuration for Workflow Orchestrator.

This module provides:
- Environment-based log level configuration (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- JSON structured logging for production
- Human-readable text logging for development
- Multiple output destinations (stdout, file, both)
- Correlation IDs for request tracing
- Log rotation for file outputs
"""

import logging
import logging.handlers
import sys
import json
from datetime import datetime
from typing import Any, Dict
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging in production environments."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if present
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id

        # Add user ID if present
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter for development environments."""

    def __init__(self):
        """Initialize text formatter with color support."""
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "text",
    log_output: str = "stdout",
    log_file_path: str = "/var/log/workflow-orchestrator/app.log",
    log_max_bytes: int = 10485760,  # 10MB
    log_backup_count: int = 5,
) -> None:
    """Configure application logging based on environment settings.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ("text" for development, "json" for production)
        log_output: Output destination ("stdout", "file", "both")
        log_file_path: Path to log file (used when log_output is "file" or "both")
        log_max_bytes: Maximum size of log file before rotation
        log_backup_count: Number of backup log files to keep

    Example:
        >>> setup_logging(log_level="DEBUG", log_format="json", log_output="both")
    """
    # Get numeric log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Select formatter
    if log_format.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()

    # Add stdout handler
    if log_output in ("stdout", "both"):
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(numeric_level)
        stdout_handler.setFormatter(formatter)
        root_logger.addHandler(stdout_handler)

    # Add file handler with rotation
    if log_output in ("file", "both"):
        # Ensure log directory exists
        log_path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=log_max_bytes,
            backupCount=log_backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Log initial configuration
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "extra_fields": {
                "log_level": log_level,
                "log_format": log_format,
                "log_output": log_output,
            }
        },
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager for adding correlation IDs and extra fields to logs."""

    def __init__(self, **extra_fields: Any):
        """Initialize log context with extra fields.

        Args:
            **extra_fields: Key-value pairs to add to all log records in this context
        """
        self.extra_fields = extra_fields
        self.old_factory = logging.getLogRecordFactory()

    def __enter__(self):
        """Enter context and set up record factory."""

        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.extra_fields.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore original record factory."""
        logging.setLogRecordFactory(self.old_factory)

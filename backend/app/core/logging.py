"""Structured JSON logging configuration.

Every log line includes request_id/correlation_id via contextvars bound
by the request-context middleware, satisfying the Logging Standards in
docs/07-master_prompt.md.
"""

import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level)
    numeric_level = logging.getLevelNamesMapping().get(log_level, logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)

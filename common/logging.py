import logging
from typing import Any


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_service_error(
    logger: logging.Logger,
    message: str,
    *,
    exc: Exception | None = None,
    **context: Any,
) -> None:
    extra = {'context': context} if context else None

    if exc is not None:
        logger.exception(message, extra=extra)
        return

    logger.error(message, extra=extra)

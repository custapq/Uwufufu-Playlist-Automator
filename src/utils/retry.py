"""
retry.py — Retry decorator with exponential backoff for Uwufufu-Automator
"""

from __future__ import annotations

import functools
import logging
import time
from typing import Callable, Tuple, Type

logger = logging.getLogger(__name__)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """Decorator that retries a function on failure with exponential backoff.

    Args:
        max_attempts: Total number of attempts before re-raising the exception.
        delay:        Initial wait time in seconds before the first retry.
        backoff:      Multiplier applied to delay after each failed attempt.
        exceptions:   Exception types that trigger a retry.

    Example::

        @retry(max_attempts=3, delay=2.0, exceptions=(requests.RequestException,))
        def search_youtube(query: str) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_attempts:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__name__, max_attempts, exc,
                        )
                        raise
                    logger.warning(
                        "%s attempt %d/%d failed: %s — retrying in %.1fs",
                        func.__name__, attempt, max_attempts, exc, current_delay,
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator

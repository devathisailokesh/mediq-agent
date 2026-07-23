"""
Exponential backoff retry utility.

Each retry doubles the wait time:
    attempt 1 fails → wait base_delay * 2^0 = 2s
    attempt 2 fails → wait base_delay * 2^1 = 4s
    attempt 3 fails → wait base_delay * 2^2 = 8s
    ...

Usage:
    from src.utils.retry import retry_with_backoff

    result = retry_with_backoff(
        fn=lambda: some_api_call(),
        max_retries=3,
        base_delay=2.0,
        label="Groq LLM",
    )
"""

import time
from typing import Any, Callable, Tuple, Type

from logs.logger import get_logger

logger = get_logger(__name__)


def retry_with_backoff(
    fn: Callable[[], Any],
    max_retries: int = 3,
    base_delay: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    label: str = "operation",
) -> Any:
    """
    Call fn() and retry with exponential backoff on failure.

    Wait time formula:  base_delay * (2 ** attempt_index)
        attempt 1 → base_delay * 1  = 2s
        attempt 2 → base_delay * 2  = 4s
        attempt 3 → base_delay * 4  = 8s

    Args:
        fn: Zero-argument callable to execute and retry.
        max_retries: Total number of attempts (including the first call).
        base_delay: Base wait time in seconds before the first retry.
        exceptions: Tuple of exception types to catch and retry on.
                    Any other exception propagates immediately.
        label: Human-readable name shown in log lines for easier tracing.

    Returns:
        Any: The return value of fn() on success.

    Raises:
        RuntimeError: If all attempts are exhausted without success.
        Exception: Any exception NOT in the exceptions tuple propagates immediately.
    """
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.debug("[%s] Attempt %d/%d", label, attempt, max_retries)
            result = fn()
            if attempt > 1:
                logger.info("[%s] Succeeded on attempt %d", label, attempt)
            return result

        except exceptions as exc:
            last_exc = exc
            wait = base_delay * (2 ** (attempt - 1))

            if attempt < max_retries:
                logger.warning(
                    "[%s] Attempt %d/%d failed: %s — retrying in %.1fs",
                    label,
                    attempt,
                    max_retries,
                    exc,
                    wait,
                )
                time.sleep(wait)
            else:
                logger.error(
                    "[%s] All %d attempts exhausted. Last error: %s",
                    label,
                    max_retries,
                    exc,
                )

    raise RuntimeError(
        f"[{label}] Failed after {max_retries} attempts. Last error: {last_exc}"
    )

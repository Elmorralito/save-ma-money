"""Retry policies and transient-error classification for AI integrations.

Provides bounded exponential backoff with jitter across all AI transports:
- Local AI CLI sidecar & subprocess execution
- Built-in / LAN local model servers (Ollama & OpenAI-compatible)
- Direct Cloud APIs (OpenAI, Anthropic, Gemini)

Permanent errors (400/401/403/404/422, missing CLI binary, SSRF guardrail denials)
are never retried.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

import httpx

logger = logging.getLogger(__name__)
_SAFE_LOG_LABEL_RE = re.compile(r"[^A-Za-z0-9_.:-]")

T = TypeVar("T")

RETRYABLE_HTTP_STATUS_CODES: frozenset[int] = frozenset({408, 429, 500, 502, 503, 504})


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Bounded exponential backoff retry policy."""

    max_attempts: int = 3
    base_delay_seconds: float = 0.35
    max_delay_seconds: float = 4.0
    jitter_ratio: float = 0.25
    retryable_status_codes: frozenset[int] = RETRYABLE_HTTP_STATUS_CODES

    def compute_delay(self, attempt: int, *, retry_after: float | None = None) -> float:
        """Compute backoff delay in seconds for 1-based ``attempt``."""
        if retry_after is not None and retry_after > 0:
            return min(retry_after, self.max_delay_seconds)
        raw = min(self.base_delay_seconds * (2 ** max(0, attempt - 1)), self.max_delay_seconds)
        if self.jitter_ratio <= 0:
            return raw
        spread = raw * self.jitter_ratio
        return max(0.0, raw + random.uniform(-spread, spread))


DISCOVERY_RETRY_POLICY = RetryPolicy(max_attempts=3, base_delay_seconds=0.25, max_delay_seconds=2.0)
CHAT_RETRY_POLICY = RetryPolicy(max_attempts=3, base_delay_seconds=0.5, max_delay_seconds=4.0)
CLI_RETRY_POLICY = RetryPolicy(max_attempts=2, base_delay_seconds=0.4, max_delay_seconds=2.0)


def extract_retry_after(exc: BaseException) -> float | None:
    """Parse numeric ``Retry-After`` header from an ``HTTPStatusError`` if present."""
    if not isinstance(exc, httpx.HTTPStatusError):
        return None
    raw = exc.response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        val = float(raw.strip())
    except ValueError:
        return None
    return val if val > 0 else None


def is_retryable_http_error(
    exc: BaseException,
    *,
    retryable_status_codes: frozenset[int] = RETRYABLE_HTTP_STATUS_CODES,
) -> bool:
    """Return True only for transient transport errors or retryable HTTP status codes."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in retryable_status_codes
    return isinstance(
        exc,
        (
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
            httpx.RemoteProtocolError,
            httpx.NetworkError,
        ),
    )


def is_retryable_cli_error(exc: BaseException) -> bool:
    """Return True for transient local CLI subprocess failures (never missing binary)."""
    if isinstance(exc, (TimeoutError, OSError)):
        return True
    msg = str(exc).lower()
    if "not found in path" in msg or "permission" in msg or "unauthorized" in msg:
        return False
    return "timed out" in msg or "exited with code" in msg


async def execute_with_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    policy: RetryPolicy,
    is_retryable: Callable[[BaseException], bool],
    label: str,
    sleep_fn: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    """Execute an async operation with bounded exponential backoff on transient failures."""
    attempts = max(1, policy.max_attempts)
    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except BaseException as exc:  # noqa: BLE001
            if isinstance(exc, (asyncio.CancelledError, KeyboardInterrupt)):
                raise
            last_exc = exc
            if attempt >= attempts or not is_retryable(exc):
                raise
            delay = policy.compute_delay(attempt, retry_after=extract_retry_after(exc))
            safe_label = _SAFE_LOG_LABEL_RE.sub("_", label.replace("\r", "_").replace("\n", "_"))[:64]
            logger.warning(
                "AI integration transient failure on %s (attempt %d/%d, %s); retrying in %.2fs",
                safe_label,
                attempt,
                attempts,
                type(exc).__name__,
                delay,
            )
            await sleep_fn(delay)
    assert last_exc is not None  # pragma: no cover - loop always returns or raises
    raise last_exc


__all__ = [
    "CHAT_RETRY_POLICY",
    "CLI_RETRY_POLICY",
    "DISCOVERY_RETRY_POLICY",
    "RETRYABLE_HTTP_STATUS_CODES",
    "RetryPolicy",
    "execute_with_retry",
    "extract_retry_after",
    "is_retryable_cli_error",
    "is_retryable_http_error",
]

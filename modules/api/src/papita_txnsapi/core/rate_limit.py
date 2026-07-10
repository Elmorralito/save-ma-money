"""In-memory sliding-window rate limiter for auth endpoints (B0 single-instance).

Thread-safe per-key counter suitable for single-process deployments. Tracks request
timestamps in a sliding window and exposes standard ``X-RateLimit-*`` header values via
``RateLimitResult``. Disabled or bypassed when limits are non-positive.

Key exports:
    RateLimitResult: Immutable outcome of a limit check.
    InMemoryRateLimiter: Process-wide singleton limiter (``MetaSingleton``).
    get_rate_limiter: Accessor for the shared limiter instance.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass

from papita_txnsmodel.utils.classutils import MetaSingleton


@dataclass(frozen=True)
class RateLimitResult:
    """Immutable outcome of a single rate-limit check.

    Attributes:
        allowed: Whether the request is permitted under the current window.
        limit: Configured maximum requests allowed per window.
        remaining: Requests still available when ``allowed`` is ``True``; ``0`` when denied.
        reset_at: Unix epoch seconds when the oldest event in the window expires.
    """

    allowed: bool
    limit: int
    remaining: int
    reset_at: int


class InMemoryRateLimiter(metaclass=MetaSingleton):
    """Thread-safe per-key sliding-window request counter.

    Maintains monotonic timestamps per limit key under a process-wide lock. One instance
    is shared across all auth rate-limit dependencies.
    """

    def __init__(self) -> None:
        self._events: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def reset(self) -> None:
        """Clear all per-key event buckets.

        Intended for test isolation only; not for production traffic management.

        Returns:
            None.
        """
        with self._lock:
            self._events.clear()

    def check(self, key: str, *, limit: int, window_seconds: int = 60) -> RateLimitResult:
        """Evaluate whether ``key`` is within ``limit`` requests for the sliding window.

        Prunes expired timestamps, records the current request when allowed, and
        computes remaining quota and reset time for response headers.

        Args:
            key: Opaque identifier (typically scope plus client IP).
            limit: Maximum requests permitted per window; non-positive limits always allow.
            window_seconds: Sliding window length in seconds.

        Returns:
            ``RateLimitResult`` describing allowance, quota, and reset epoch.
        """
        if limit <= 0:
            epoch_now = int(time.time())
            return RateLimitResult(allowed=True, limit=limit, remaining=limit, reset_at=epoch_now + window_seconds)

        monotonic_now = time.monotonic()
        window_start = monotonic_now - window_seconds

        with self._lock:
            bucket = self._events[key]
            self._events[key] = [stamp for stamp in bucket if stamp > window_start]
            bucket = self._events[key]
            allowed = len(bucket) < limit
            if allowed:
                bucket.append(monotonic_now)
            remaining = max(0, limit - len(bucket))
            oldest = bucket[0] if bucket else monotonic_now
            reset_at = int(time.time()) + max(1, int(window_seconds - (monotonic_now - oldest)))

        return RateLimitResult(
            allowed=allowed,
            limit=limit,
            remaining=remaining if allowed else 0,
            reset_at=reset_at,
        )


def get_rate_limiter() -> InMemoryRateLimiter:
    """Return the process-wide ``InMemoryRateLimiter`` singleton.

    Returns:
        Shared limiter instance used by auth rate-limit dependencies.
    """
    return InMemoryRateLimiter()

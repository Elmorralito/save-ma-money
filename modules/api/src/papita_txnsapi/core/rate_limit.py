"""In-memory sliding-window rate limiter for auth endpoints (B0 single-instance)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass

from papita_txnsmodel.utils.classutils import MetaSingleton


@dataclass(frozen=True)
class RateLimitResult:
    """Outcome of a rate-limit check."""

    allowed: bool
    limit: int
    remaining: int
    reset_at: int


class InMemoryRateLimiter(metaclass=MetaSingleton):
    """Thread-safe per-key sliding window counter."""

    def __init__(self) -> None:
        self._events: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def reset(self) -> None:
        """Clear all counters (tests only)."""
        with self._lock:
            self._events.clear()

    def check(self, key: str, *, limit: int, window_seconds: int = 60) -> RateLimitResult:
        """Return whether ``key`` is within ``limit`` requests per window."""
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
    """Return the process-wide rate limiter singleton."""
    return InMemoryRateLimiter()

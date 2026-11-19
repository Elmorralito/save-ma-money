"""Sliding-window rate limiters for auth and tenant API quotas (B0 + Redis).

Thread-safe in-memory limiter for single-process deployments, plus a Redis-backed
limiter for multi-replica consistency when ``REDIS_RATE_LIMIT_ENABLED`` is set.
The Redis path uses a single Lua script so prune/check/incr cannot race under load.
Cache and tenant API rate-limit paths **fail open** on Redis errors by default.
Auth IP limits may optionally **fail closed** via ``AUTH_RATE_LIMIT_FAIL_CLOSED``.
JWT denylist uses a separate fail-closed policy when Redis is required
(see :mod:`session_store`). In-memory limits are per-process — enable Redis
rate limits for multi-worker / multi-replica deployments.

Key exports:
    RateLimitResult: Immutable outcome of a limit check.
    InMemoryRateLimiter: Process-wide singleton limiter (``MetaSingleton``).
    RedisRateLimiter: Distributed sliding-window limiter via atomic Lua + ZSET.
    bind_rate_limiters: Attach cached Redis limiters to ``app.state`` at lifespan.
    get_rate_limiter: Accessor for the shared in-memory limiter instance.
    get_rate_limiter_for_request: Factory selecting Redis vs in-memory (app-state cache).
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from redis import Redis
from redis.exceptions import RedisError

from papita_txnsapi.core.redis_keys import redis_key
from papita_txnsmodel.utils.classutils import MetaSingleton

if TYPE_CHECKING:
    from fastapi import Request

    from papita_txnsapi.config.settings import Settings

logger = logging.getLogger(__name__)

# Atomic prune → count → optional ZADD → expire. Returns {allowed, count_after, oldest_score}.
_RATE_LIMIT_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window_start = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local window_seconds = tonumber(ARGV[4])
local member = ARGV[5]

redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
local count = redis.call('ZCARD', key)
local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
local oldest_score = now
if #oldest >= 2 then
  oldest_score = tonumber(oldest[2])
end

local allowed = 0
local count_after = count
if count < limit then
  redis.call('ZADD', key, now, member)
  redis.call('EXPIRE', key, window_seconds)
  count_after = count + 1
  allowed = 1
  if count == 0 then
    oldest_score = now
  end
end

return {allowed, count_after, tostring(oldest_score)}
"""


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


class RateLimiter(Protocol):
    """Protocol for rate limiters used by auth dependencies."""

    def check(self, key: str, *, limit: int, window_seconds: int = 60) -> RateLimitResult:
        """Evaluate whether ``key`` is within ``limit`` for the sliding window."""


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


class RedisRateLimiter:
    """Distributed sliding-window limiter using an atomic Lua script over a ZSET.

    By default fails open on Redis errors (allow + log). Pass ``fail_closed=True``
    for auth IP limits when ``AUTH_RATE_LIMIT_FAIL_CLOSED`` is enabled.
    """

    def __init__(self, client: Redis, *, fail_closed: bool = False) -> None:
        self._client = client
        self._fail_closed = fail_closed
        # Prefer EVALSHA via register_script; fall back to EVAL for clients that
        # support Lua but not SCRIPT LOAD (e.g. some FakeRedis builds).
        self._script = client.register_script(_RATE_LIMIT_LUA)

    def _eval_limit(
        self,
        namespaced: str,
        *,
        epoch_now: float,
        window_start: float,
        limit: int,
        window_seconds: int,
        member: str,
    ) -> list:
        """Run the atomic rate-limit script (EVALSHA, with EVAL fallback)."""
        args = [
            f"{epoch_now:.6f}",
            f"{window_start:.6f}",
            str(limit),
            str(window_seconds),
            member,
        ]
        try:
            return self._script(keys=[namespaced], args=args)
        except RedisError as exc:
            if "evalsha" not in str(exc).lower() and "noscript" not in str(exc).lower():
                raise
            return self._client.eval(_RATE_LIMIT_LUA, 1, namespaced, *args)

    def check(self, key: str, *, limit: int, window_seconds: int = 60) -> RateLimitResult:
        """Evaluate whether ``key`` is within ``limit`` using Redis ZSET timestamps.

        Args:
            key: Opaque identifier (typically scope plus client IP).
            limit: Maximum requests permitted per window; non-positive limits always allow.
            window_seconds: Sliding window length in seconds.

        Returns:
            ``RateLimitResult`` describing allowance, quota, and reset epoch.
        """
        epoch_now = time.time()
        if limit <= 0:
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset_at=int(epoch_now) + window_seconds,
            )

        namespaced = redis_key("ratelimit", key)
        window_start = epoch_now - window_seconds
        member = f"{epoch_now:.6f}:{id(self)}"

        try:
            raw = self._eval_limit(
                namespaced,
                epoch_now=epoch_now,
                window_start=window_start,
                limit=limit,
                window_seconds=window_seconds,
                member=member,
            )
            allowed_flag = int(raw[0])
            count_after = int(raw[1])
            oldest_score = float(raw[2])
            allowed = allowed_flag == 1
            remaining = max(0, limit - count_after) if allowed else 0
            reset_at = int(oldest_score) + window_seconds
            return RateLimitResult(
                allowed=allowed,
                limit=limit,
                remaining=remaining,
                reset_at=max(int(epoch_now) + 1, reset_at),
            )
        except RedisError:
            if self._fail_closed:
                logger.exception("Redis rate limit check failed; failing closed for key scope")
                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_at=int(epoch_now) + window_seconds,
                )
            # Fail open by default (availability over strict throttling).
            logger.exception("Redis rate limit check failed; failing open for key scope")
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset_at=int(epoch_now) + window_seconds,
            )


def get_rate_limiter() -> InMemoryRateLimiter:
    """Return the process-wide ``InMemoryRateLimiter`` singleton.

    Returns:
        Shared limiter instance used by auth rate-limit dependencies.
    """
    return InMemoryRateLimiter()


def bind_rate_limiters(app: object, settings: Settings) -> None:
    """Attach process-scoped Redis rate limiters to ``app.state`` when enabled.

    Caches one fail-open limiter (tenant/health) and one fail-closed limiter
    (optional auth IP policy) so each request reuses the registered Lua script
    instead of constructing a new ``RedisRateLimiter``.

    Args:
        app: FastAPI application (expects ``app.state.redis``).
        settings: Application settings with Redis rate-limit flags.
    """
    state = getattr(app, "state", None)
    if state is None:
        return
    state.rate_limiter = None
    state.rate_limiter_fail_closed = None
    if not (settings.REDIS_ENABLED and settings.REDIS_RATE_LIMIT_ENABLED):
        return
    client = getattr(state, "redis", None)
    if not isinstance(client, Redis):
        return
    state.rate_limiter = RedisRateLimiter(client, fail_closed=False)
    state.rate_limiter_fail_closed = RedisRateLimiter(client, fail_closed=True)


def get_rate_limiter_for_request(
    request: Request,
    settings: Settings,
    *,
    fail_closed: bool = False,
) -> RateLimiter:
    """Select Redis or in-memory limiter based on settings and app state.

    Prefer limiters bound on ``app.state`` (lifespan). Lazily bind when Redis is
    present but lifespan has not attached limiters yet (common in unit tests).

    Args:
        request: Incoming request (reads ``app.state.redis`` / cached limiters).
        settings: Application settings with Redis rate-limit flags.
        fail_closed: When using Redis, deny on Redis errors instead of allowing.

    Returns:
        ``RedisRateLimiter`` when enabled and a client is available; otherwise
        the in-memory singleton.
    """
    if settings.REDIS_ENABLED and settings.REDIS_RATE_LIMIT_ENABLED:
        client = getattr(request.app.state, "redis", None)
        if isinstance(client, Redis):
            attr = "rate_limiter_fail_closed" if fail_closed else "rate_limiter"
            cached = getattr(request.app.state, attr, None)
            if isinstance(cached, RedisRateLimiter):
                return cached
            limiter = RedisRateLimiter(client, fail_closed=fail_closed)
            setattr(request.app.state, attr, limiter)
            return limiter
    return get_rate_limiter()

"""Cache-aside helpers for tenant-scoped Redis caching (PPT-043).

Uses per-tenant, per-namespace version counters so mutations invalidate related
entries without SCAN/DELETE of hashed keys. Keys are namespaced as
``papita:{env}:{owner_id}:…`` (see :mod:`redis_keys`). Cache reads/writes
**fail open** (miss / skip) on Redis errors.

Per-route TTLs (not a single global default): accounts 60s, categories 300s,
reports 120–300s (default 180s), transactions 15s.

Key exports:
    CacheNamespace: Logical cache groups (accounts, categories, reports, transactions).
    build_cache_key: Compose ``papita:{env}:{owner_id}:{route}:v{version}:{hash}``.
    get_cache_version / bump_cache_versions: Version counter helpers.
    cache_get_json / cache_set_json: JSON get/set with TTL.
    get_versioned_cached_json / set_versioned_cached_json: Versioned read/write;
        miss fills should pass ``version`` from get into set to skip a Redis RTT.
    ttl_for_namespace: Resolve TTL from settings or defaults.
"""

from __future__ import annotations

import hashlib
import json
import logging
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Mapping
from uuid import UUID

from redis import Redis
from redis.exceptions import RedisError

from papita_txnsapi.core.redis_keys import redis_key

if TYPE_CHECKING:
    from papita_txnsapi.config.settings import Settings

logger = logging.getLogger(__name__)

# Fallback TTLs when settings fields are unavailable (per-route, not global).
_DEFAULT_TTL_SECONDS: dict[str, int] = {
    "accounts": 60,
    "categories": 300,
    "reports": 180,
    "transactions": 15,
}


class CacheNamespace(StrEnum):
    """Logical cache groups invalidated together after mutations."""

    ACCOUNTS = "accounts"
    CATEGORIES = "categories"
    REPORTS = "reports"
    TRANSACTIONS = "transactions"


def version_key(owner_id: UUID | str, namespace: CacheNamespace | str) -> str:
    """Return the Redis key for a tenant namespace version counter."""
    return redis_key(owner_id, "cache_ver", namespace)


def get_cache_version(client: Redis | None, owner_id: UUID | str, namespace: CacheNamespace | str) -> int:
    """Read the current cache version for ``owner_id`` + ``namespace``.

    Args:
        client: Redis client, or ``None`` (returns ``0``).
        owner_id: Tenant primary key.
        namespace: Cache namespace.

    Returns:
        Integer version (``0`` when missing or Redis unavailable).
    """
    if client is None:
        return 0
    try:
        raw = client.get(version_key(owner_id, namespace))
    except RedisError:
        logger.exception("Redis cache version read failed")
        return 0
    if raw is None:
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def bump_cache_versions(
    client: Redis | None,
    owner_id: UUID | str | None,
    *namespaces: CacheNamespace | str,
) -> None:
    """Increment version counters so prior hashed keys become unreachable.

    Args:
        client: Redis client, or ``None`` to no-op.
        owner_id: Tenant primary key; no-op when ``None``.
        namespaces: One or more namespaces to invalidate.
    """
    if client is None or owner_id is None or not namespaces:
        return
    try:
        pipe = client.pipeline()
        for namespace in namespaces:
            pipe.incr(version_key(owner_id, namespace))
        pipe.execute()
    except RedisError:
        logger.exception("Redis cache version bump failed for owner %s", owner_id)


def build_cache_key(
    owner_id: UUID | str,
    route: str,
    params: Mapping[str, Any] | None = None,
    *,
    version: int = 0,
) -> str:
    """Build a tenant-scoped, versioned cache key for a route and parameters.

    Args:
        owner_id: Authenticated tenant primary key (JWT ``sub`` / owner id).
        route: Stable route label (e.g. ``accounts:list``).
        params: Optional query/path parameters included in the hash.
        version: Namespace version from :func:`get_cache_version`.

    Returns:
        Key of the form ``papita:{env}:{owner_id}:{route}:v{version}:{sha256}``.
    """
    payload = json.dumps(params or {}, sort_keys=True, default=str, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]
    return redis_key(owner_id, route, f"v{version}", digest)


def cache_get_json(client: Redis | None, key: str) -> dict[str, Any] | None:
    """Fetch a JSON object from Redis.

    Args:
        client: Redis client, or ``None`` to skip (cache miss).
        key: Full cache key from :func:`build_cache_key`.

    Returns:
        Deserialized mapping on hit; ``None`` on miss, disabled client, or error.
    """
    if client is None:
        return None
    try:
        raw = client.get(key)
    except RedisError:
        logger.exception("Redis cache get failed for key prefix %s", key.split(":", 1)[0])
        return None
    if raw is None:
        return None
    try:
        loaded = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        logger.warning("Invalid JSON in cache for key hash segment")
        return None
    if not isinstance(loaded, dict):
        return None
    return loaded


def cache_set_json(
    client: Redis | None,
    key: str,
    value: Mapping[str, Any],
    *,
    ttl_seconds: int,
) -> bool:
    """Store a JSON-serializable mapping in Redis with a TTL.

    Args:
        client: Redis client, or ``None`` to skip.
        key: Full cache key from :func:`build_cache_key`.
        value: Mapping to serialize (typically ``model_dump(mode=\"json\")``).
        ttl_seconds: Expiration in seconds; non-positive skips the write.

    Returns:
        ``True`` when the write succeeded; ``False`` when skipped or on error.
    """
    if client is None or ttl_seconds <= 0:
        return False
    try:
        payload = json.dumps(value, default=str, separators=(",", ":"))
        client.setex(key, ttl_seconds, payload)
        return True
    except (TypeError, RedisError):
        logger.exception("Redis cache set failed for key prefix %s", key.split(":", 1)[0])
        return False


def ttl_for_namespace(settings: Settings | None, namespace: CacheNamespace | str) -> int:
    """Resolve cache TTL seconds for a namespace from settings or defaults.

    Args:
        settings: Optional application settings with per-namespace TTL fields.
        namespace: Cache namespace.

    Returns:
        Positive TTL in seconds.
    """
    ns = namespace if isinstance(namespace, CacheNamespace) else CacheNamespace(str(namespace))
    if settings is not None:
        if ns is CacheNamespace.ACCOUNTS:
            return max(1, settings.REDIS_CACHE_TTL_ACCOUNTS_SECONDS)
        if ns is CacheNamespace.CATEGORIES:
            return max(1, settings.REDIS_CACHE_TTL_CATEGORIES_SECONDS)
        if ns is CacheNamespace.REPORTS:
            return max(1, settings.REDIS_CACHE_TTL_REPORTS_SECONDS)
        if ns is CacheNamespace.TRANSACTIONS:
            return max(1, settings.REDIS_CACHE_TTL_TRANSACTIONS_SECONDS)
    return _DEFAULT_TTL_SECONDS.get(ns.value, 60)


def get_versioned_cached_json(
    client: Redis | None,
    owner_id: UUID | str,
    namespace: CacheNamespace,
    route: str,
    params: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, str, int]:
    """Read a versioned cache entry.

    Args:
        client: Redis client or ``None``.
        owner_id: Tenant id.
        namespace: Cache namespace for version lookup.
        route: Route label.
        params: Query/path parameters.

    Returns:
        ``(payload, status, version)`` where ``status`` is ``HIT`` / ``MISS`` /
        ``BYPASS``. Pass ``version`` to :func:`set_versioned_cached_json` on miss
        fills so the set path skips a second version read.
    """
    if client is None:
        return None, "BYPASS", 0
    version = get_cache_version(client, owner_id, namespace)
    key = build_cache_key(owner_id, route, params, version=version)
    cached = cache_get_json(client, key)
    if cached is None:
        return None, "MISS", version
    return cached, "HIT", version


def set_versioned_cached_json(
    client: Redis | None,
    owner_id: UUID | str,
    namespace: CacheNamespace,
    route: str,
    params: Mapping[str, Any] | None,
    *,
    value: Mapping[str, Any],
    ttl_seconds: int,
    version: int | None = None,
) -> bool:
    """Write a versioned cache entry under a namespace version.

    Args:
        client: Redis client or ``None``.
        owner_id: Tenant id.
        namespace: Cache namespace for key versioning.
        route: Route label matching the get path.
        params: Query/path parameters matching the get path.
        value: JSON-serializable payload to store.
        ttl_seconds: Expiration in seconds.
        version: Optional version from a prior :func:`get_versioned_cached_json`
            call. When omitted, the current counter is read (extra Redis RTT).
            Reusing a pre-bump version is safe: after ``bump_cache_versions`` the
            write lands on an unreachable key and the next read misses.

    Returns:
        ``True`` when the write succeeded; ``False`` when skipped or on error.
    """
    if client is None:
        return False
    resolved_version = get_cache_version(client, owner_id, namespace) if version is None else version
    key = build_cache_key(owner_id, route, params, version=resolved_version)
    return cache_set_json(client, key, value, ttl_seconds=ttl_seconds)

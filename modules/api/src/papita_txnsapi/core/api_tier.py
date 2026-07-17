"""API subscription tier helpers for tenant rate limits (PPT-043).

Tiers follow the API README Free / Pro / Enterprise matrix. Until billing lands,
the default tier comes from settings; optional per-tenant overrides can be stored
in Redis at ``papita:{env}:{owner_id}:api_tier``.

Key exports:
    ApiTier: Allowed plan names.
    TierLimits: Per-minute and per-day quotas.
    resolve_api_tier: Resolve tier for an owner.
    limits_for_tier: Map tier to numeric limits from settings.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from redis import Redis
from redis.exceptions import RedisError

from papita_txnsapi.core.redis_keys import redis_key

if TYPE_CHECKING:
    from papita_txnsapi.config.settings import Settings


class ApiTier(StrEnum):
    """Supported API rate-limit tiers."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass(frozen=True, slots=True)
class TierLimits:
    """Numeric quotas for a tier.

    Attributes:
        per_minute: Max requests per rolling 60s window; ``0`` or negative = unlimited.
        per_day: Max requests per rolling 24h window; ``0`` or negative = unlimited.
    """

    per_minute: int
    per_day: int

    @property
    def unlimited(self) -> bool:
        """Whether both windows are unlimited."""
        return self.per_minute <= 0 and self.per_day <= 0


def resolve_api_tier(
    settings: Settings,
    owner_id: UUID | str,
    redis: Redis | None = None,
) -> ApiTier:
    """Resolve the API tier for a tenant.

    Prefers Redis override ``papita:{env}:{owner_id}:api_tier`` when present and
    valid; otherwise uses ``settings.API_RATE_LIMIT_DEFAULT_TIER``.

    Args:
        settings: Application settings with default tier.
        owner_id: Authenticated tenant id.
        redis: Optional Redis client for per-tenant overrides.

    Returns:
        Resolved :class:`ApiTier`.
    """
    if redis is not None:
        try:
            raw = redis.get(redis_key(owner_id, "api_tier"))
            if isinstance(raw, str):
                try:
                    return ApiTier(raw)
                except ValueError:
                    pass
        except RedisError:
            pass
    try:
        return ApiTier(settings.API_RATE_LIMIT_DEFAULT_TIER)
    except ValueError:
        return ApiTier.FREE


def limits_for_tier(settings: Settings, tier: ApiTier) -> TierLimits:
    """Return configured minute/day limits for ``tier``.

    Args:
        settings: Application settings with tier quota fields.
        tier: Resolved API tier.

    Returns:
        :class:`TierLimits` for enforcement.
    """
    if tier is ApiTier.ENTERPRISE:
        return TierLimits(per_minute=0, per_day=0)
    if tier is ApiTier.PRO:
        return TierLimits(
            per_minute=settings.API_RATE_LIMIT_PRO_PER_MINUTE,
            per_day=settings.API_RATE_LIMIT_PRO_PER_DAY,
        )
    return TierLimits(
        per_minute=settings.API_RATE_LIMIT_FREE_PER_MINUTE,
        per_day=settings.API_RATE_LIMIT_FREE_PER_DAY,
    )

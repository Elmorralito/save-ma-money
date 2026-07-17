"""Queue / pub-sub broker scaffold for Redis (PPT-043 P3).

Interface-only placeholders for background jobs and cache-invalidation
broadcasts. No worker fleet is deployed in this issue.

Key exports:
    BrokerSettings: Feature flags for future broker wiring.
    RedisBroker: Minimal enqueue / publish stubs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from redis import Redis
from redis.exceptions import RedisError

from papita_txnsapi.core.redis_keys import redis_key

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BrokerSettings:
    """Broker feature flags (scaffold).

    Attributes:
        enabled: Whether broker operations should attempt Redis writes.
        default_queue: Default list key for simple LPUSH enqueue (env-prefixed).
    """

    enabled: bool = False
    default_queue: str = ""  # resolved to papita:{env}:jobs when empty


class RedisBroker:
    """Minimal Redis list / pub-sub scaffold.

    Args:
        client: Optional Redis client.
        settings: Broker feature flags.
    """

    def __init__(self, client: Redis | None, settings: BrokerSettings | None = None) -> None:
        self._client = client
        self._settings = settings or BrokerSettings()

    @property
    def available(self) -> bool:
        """Whether broker writes can run."""
        return bool(self._settings.enabled and self._client is not None)

    def enqueue(self, payload: str, *, queue: str | None = None) -> bool:
        """Push a job payload onto a Redis list (scaffold).

        Args:
            payload: Opaque job payload string.
            queue: Optional queue key override.

        Returns:
            ``True`` when LPUSH succeeded; ``False`` when disabled or on error.
        """
        if not self.available or self._client is None:
            return False
        key = queue or self._settings.default_queue or redis_key("jobs")
        try:
            self._client.lpush(key, payload)
            return True
        except RedisError:
            logger.exception("Broker enqueue failed")
            return False

    def publish(self, channel: str, message: str) -> bool:
        """Publish a message on a Redis channel (scaffold).

        Args:
            channel: Pub/sub channel name (env-prefixed when not already namespaced).
            message: Message body.

        Returns:
            ``True`` when PUBLISH succeeded; ``False`` when disabled or on error.
        """
        if not self.available or self._client is None:
            return False
        channel_key = channel if channel.startswith("papita:") else redis_key("channel", channel)
        try:
            self._client.publish(channel_key, message)
            return True
        except RedisError:
            logger.exception("Broker publish failed")
            return False

"""Environment-scoped Redis key namespacing (PPT-043 hardening).

All Redis keys use ``papita:{env}:…`` so local / staging / production (or shared
managed Redis) do not collide. ``env`` follows :data:`PAPITA_ENV`
(``local`` | ``staging`` | ``production``).

Key exports:
    redis_key: Join path segments under the ``papita:{env}:`` prefix.
    redis_key_prefix: Return the bare ``papita:{env}:`` prefix string.
"""

from __future__ import annotations

from papita_txnsapi.config.environment import active_environment, normalize_environment_name


def redis_key_prefix(*, env: str | None = None) -> str:
    """Return the Redis key prefix ``papita:{env}:``.

    Args:
        env: Optional environment name; defaults to active ``PAPITA_ENV``.

    Returns:
        Prefix including the trailing colon.
    """
    name = normalize_environment_name(env) if env is not None else active_environment()
    return f"papita:{name}:"


def redis_key(*parts: object, env: str | None = None) -> str:
    """Build a fully namespaced Redis key.

    Args:
        parts: Path segments joined with ``:`` (e.g. ``owner_id``, ``cache_ver``, ``accounts``).
        env: Optional environment override for the ``papita:{env}:`` prefix.

    Returns:
        Key of the form ``papita:{env}:{part}:{part}:…``.
    """
    suffix = ":".join(str(part) for part in parts)
    return f"{redis_key_prefix(env=env)}{suffix}"

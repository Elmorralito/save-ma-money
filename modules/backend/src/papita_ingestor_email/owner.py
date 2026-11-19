"""Trusted owner resolution for email ingestion (PPT-082 / #176).

Owner identity is env-configured only — never taken from MIME headers or parsers.
"""

from __future__ import annotations

from uuid import UUID

from papita_txnsmodel.access.users.dto import UsersDTO


def users_dto_for_owner_id(owner_id: UUID) -> UsersDTO:
    """Build a trusted ``UsersDTO`` keyed only by ``id`` for bridge scoping.

    Uses ``model_construct`` so placeholder profile fields are not validated as
    a real local-auth user (password/username are irrelevant to ingest).

    Args:
        owner_id: Tenant user UUID from ``PAPITA_INGESTOR_OWNER_ID``. Must exist
            in ``users`` for live persist/DLQ foreign keys.

    Returns:
        ``UsersDTO`` with the given ``id``.

    Raises:
        ValueError: When ``owner_id`` is missing.
    """
    if owner_id is None:
        raise ValueError("owner_id is required")
    return UsersDTO.model_construct(
        id=owner_id,
        username="ingest_owner",
        email="ingest_owner@local.invalid",
        password=None,
        auth_provider="local",
    )


__all__ = ["users_dto_for_owner_id"]

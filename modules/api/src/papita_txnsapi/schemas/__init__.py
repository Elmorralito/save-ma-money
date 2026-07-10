"""Pydantic request/response schemas for the Papita Transactions API.

This package defines API-facing Pydantic models only — no database access or
business logic. Schemas validate inbound JSON, shape outbound responses, and
delegate persistence to ``papita_txnsmodel`` DTOs via converter helpers in
``schemas.converters`` and domain-specific ``to_*_dto`` / ``from_dto`` methods.

Public symbols are re-exported here so routers and tests can import from
``papita_txnsapi.schemas`` without reaching into submodules.
"""

from papita_txnsapi.schemas.auth import RegisterRequest, TokenResponse, UserResponse
from papita_txnsapi.schemas.common import DeferredResponse, ErrorDetail, PaginatedResponse
from papita_txnsapi.schemas.converters import api_slug_to_enum, enum_to_api_slug

__all__ = [
    "DeferredResponse",
    "ErrorDetail",
    "PaginatedResponse",
    "RegisterRequest",
    "TokenResponse",
    "UserResponse",
    "api_slug_to_enum",
    "enum_to_api_slug",
]

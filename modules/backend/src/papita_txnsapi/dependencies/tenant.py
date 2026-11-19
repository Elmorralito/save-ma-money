"""Tenant context helper for protected routes.

Exposes the authenticated owner as a small Pydantic wrapper so routers can access
tenant identity without repeating ``UsersDTO`` field access patterns.

Key exports:
    TenantContext: Owner-scoped context with a convenience ``owner_id`` property.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from papita_txnsmodel.access.users.dto import UsersDTO


class TenantContext(BaseModel):
    """Owner-scoped context passed into tenant-aware route handlers.

    Attributes:
        owner: Authenticated tenant owner DTO resolved from the JWT ``sub`` claim.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    owner: UsersDTO

    @property
    def owner_id(self):
        """Return the tenant owner's primary-key UUID.

        Returns:
            Owner UUID from ``owner.id``.
        """
        return self.owner.id

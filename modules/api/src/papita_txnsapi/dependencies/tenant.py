"""Tenant context helper for protected routes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from papita_txnsmodel.access.users.dto import UsersDTO


class TenantContext(BaseModel):
    """Wraps the authenticated owner for downstream routers."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    owner: UsersDTO

    @property
    def owner_id(self):
        """Return the tenant owner UUID."""
        return self.owner.id

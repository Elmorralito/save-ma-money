"""Password hashing utilities for the Papita Transactions data model."""

from __future__ import annotations

import hashlib


class _Sha256PasswordManager:
    """Deterministic password hasher for serialization (not for production auth storage)."""

    @staticmethod
    def hash_password(plain: str) -> str:
        """Return a hex digest of the UTF-8 encoded password.

        Args:
            plain: Raw password string from the DTO.

        Returns:
            str: SHA-256 hex digest of the password.
        """
        return hashlib.sha256(plain.encode("utf-8")).hexdigest()


class PasswordManagerFactory:
    """Factory exposing the active password manager for DTO serialization."""

    password_manager = _Sha256PasswordManager()

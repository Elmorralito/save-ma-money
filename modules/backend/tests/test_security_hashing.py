"""Tests for papita_txnsapi.core.security.hashing."""

import pytest

from papita_txnsapi.core.security.hashing import Argon2PasswordManager, PasswordManagerFactory


@pytest.fixture(autouse=True)
def reset_password_manager_factory() -> None:
    """Clear singleton factory state so tests do not depend on order."""
    PasswordManagerFactory().reset()
    yield
    PasswordManagerFactory().reset()


def test_argon2_hash_and_verify_roundtrip() -> None:
    manager = Argon2PasswordManager()
    password = "secret-password"
    hashed = manager.hash_password(password)
    assert manager.verify_password(password, hashed) is True
    assert manager.verify_password("wrong-password", hashed) is False


def test_argon2_get_salt_from_hash() -> None:
    manager = Argon2PasswordManager()
    hashed = manager.hash_password("x")
    salt = manager.get_salt(hashed)
    assert isinstance(salt, str)
    assert len(salt) > 0


def test_password_manager_factory_returns_argon2() -> None:
    factory = PasswordManagerFactory()
    pm = factory.get_password_manager(keyword="argon2")
    assert isinstance(pm, Argon2PasswordManager)


def test_password_manager_property_initializes_with_default_keyword() -> None:
    factory = PasswordManagerFactory()
    pm = factory.password_manager
    assert isinstance(pm, Argon2PasswordManager)
    assert factory.password_manager is pm


def test_get_password_manager_requires_keyword_when_empty() -> None:
    factory = PasswordManagerFactory()
    with pytest.raises(ValueError, match="not specified"):
        factory.get_password_manager()

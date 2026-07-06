"""Unit tests for UsersService authentication methods."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.users import UsersService

VALID_PASSWORD = "SecurePass1!"
VALID_EMAIL = "user@example.local"


def _stored_user(**overrides) -> UsersDTO:
    """Build a partial UsersDTO for repository lookup mocks."""
    defaults = {
        "id": uuid.uuid4(),
        "username": "johndoe",
        "email": VALID_EMAIL,
        "password": "$argon2$hash",
        "active": True,
        "deleted_at": None,
    }
    defaults.update(overrides)
    return UsersDTO.model_construct(**defaults)


@pytest.fixture
def users_service():
    """UsersService with a mocked repository."""
    with patch("papita_txnsmodel.services.users.UsersRepository"):
        service = UsersService()
        mock_repo = MagicMock()
        mock_repo.get_record_from_attributes = MagicMock(return_value=None)
        mock_repo.upsert_record = MagicMock()
        service._repository = mock_repo
        yield service, mock_repo


class TestEnsurePasswordManager:
    """Tests for password manager bootstrap."""

    @patch("papita_txnsmodel.services.users.PasswordManagerFactory")
    def test_ensure_password_manager_calls_argon2(self, mock_factory_cls):
        """ensure_password_manager initializes Argon2 via the factory."""
        factory = MagicMock()
        mock_factory_cls.return_value = factory

        UsersService.ensure_password_manager()

        factory.get_password_manager.assert_called_once_with(keyword="argon2")


class TestBuildLoginProbe:
    """Tests for login identifier probe construction."""

    def test_build_login_probe_returns_none_for_blank_identifier(self):
        """Blank identifiers do not produce a repository probe."""
        assert UsersService._build_login_probe("") is None
        assert UsersService._build_login_probe("   ") is None

    def test_build_login_probe_normalizes_email(self):
        """Email probes are lowercased."""
        probe = UsersService._build_login_probe("User@Example.local")
        assert probe.email == "user@example.local"

    def test_build_login_probe_preserves_username_case(self):
        """Username probes keep case sensitivity."""
        probe = UsersService._build_login_probe("JohnDoe")
        assert probe.username == "JohnDoe"


class TestLookupByIdentifier:
    """Tests for repository lookup helpers."""

    def test_lookup_by_identifier_returns_inactive_user_when_not_required(self, users_service):
        """Registration uniqueness checks include inactive users."""
        service, repo = users_service
        inactive_user = _stored_user(active=False)
        repo.get_record_from_attributes.return_value = inactive_user

        result = service._lookup_by_identifier("johndoe", require_active=False)

        assert result is inactive_user

    def test_lookup_by_identifier_excludes_inactive_user_for_auth(self, users_service):
        """Authentication lookups exclude inactive users."""
        service, repo = users_service
        repo.get_record_from_attributes.return_value = _stored_user(active=False)

        assert service._lookup_by_identifier("johndoe", require_active=True) is None

    def test_lookup_by_identifier_excludes_soft_deleted_user_for_auth(self, users_service):
        """Authentication lookups exclude soft-deleted users."""
        from datetime import datetime

        service, repo = users_service
        repo.get_record_from_attributes.return_value = _stored_user(
            active=True,
            deleted_at=datetime(2026, 1, 1),
        )

        assert service._lookup_by_identifier("johndoe", require_active=True) is None


class TestVerifyCredentials:
    """Tests for credential verification."""

    @patch.object(UsersService, "ensure_password_manager")
    @patch("papita_txnsmodel.services.users.PasswordManagerFactory")
    def test_verify_credentials_success_by_username(self, mock_factory_cls, _mock_ensure, users_service):
        """Valid username + password returns the user DTO."""
        service, repo = users_service
        stored_user = _stored_user()
        repo.get_record_from_attributes.return_value = stored_user

        password_manager = MagicMock()
        password_manager.verify_password.return_value = True
        mock_factory_cls.return_value.password_manager = password_manager

        result = service.verify_credentials("johndoe", VALID_PASSWORD)

        assert result is stored_user
        password_manager.verify_password.assert_called_once_with(VALID_PASSWORD, "$argon2$hash")

    @patch.object(UsersService, "ensure_password_manager")
    @patch("papita_txnsmodel.services.users.PasswordManagerFactory")
    def test_verify_credentials_success_by_email(self, mock_factory_cls, _mock_ensure, users_service):
        """Email identifier is normalized to lowercase for lookup."""
        service, repo = users_service
        stored_user = _stored_user()
        repo.get_record_from_attributes.return_value = stored_user
        mock_factory_cls.return_value.password_manager.verify_password.return_value = True

        service.verify_credentials("User@Example.local", VALID_PASSWORD)

        lookup_probe = repo.get_record_from_attributes.call_args[0][0]
        assert lookup_probe.email == "user@example.local"

    @patch.object(UsersService, "ensure_password_manager")
    def test_verify_credentials_unknown_user(self, _mock_ensure, users_service):
        """Unknown identifier returns None."""
        service, repo = users_service
        repo.get_record_from_attributes.return_value = None

        assert service.verify_credentials("nobody", VALID_PASSWORD) is None

    @patch.object(UsersService, "ensure_password_manager")
    def test_verify_credentials_empty_password(self, _mock_ensure, users_service):
        """Empty password short-circuits before repository lookup."""
        service, repo = users_service

        assert service.verify_credentials("johndoe", "") is None
        repo.get_record_from_attributes.assert_not_called()

    @patch.object(UsersService, "ensure_password_manager")
    @patch("papita_txnsmodel.services.users.PasswordManagerFactory")
    def test_verify_credentials_wrong_password(self, mock_factory_cls, _mock_ensure, users_service):
        """Wrong password returns None (same as unknown user)."""
        service, repo = users_service
        repo.get_record_from_attributes.return_value = _stored_user()
        mock_factory_cls.return_value.password_manager.verify_password.return_value = False

        assert service.verify_credentials("johndoe", "WrongPass1!") is None

    @patch.object(UsersService, "ensure_password_manager")
    def test_verify_credentials_inactive_user(self, _mock_ensure, users_service):
        """Inactive users cannot authenticate."""
        service, repo = users_service
        repo.get_record_from_attributes.return_value = _stored_user(active=False)

        assert service.verify_credentials("johndoe", VALID_PASSWORD) is None


class TestRegister:
    """Tests for user registration."""

    @patch.object(UsersService, "ensure_password_manager")
    @patch.object(UsersService, "create")
    def test_register_success(self, mock_create, _mock_ensure, users_service):
        """Register creates a user when username and email are unique."""
        service, repo = users_service
        repo.get_record_from_attributes.return_value = None
        expected = _stored_user(password="hash")
        mock_create.return_value = expected

        result = service.register(username="johndoe", email=VALID_EMAIL, password=VALID_PASSWORD)

        assert result is expected
        mock_create.assert_called_once()

    @patch.object(UsersService, "ensure_password_manager")
    @patch.object(UsersService, "create")
    def test_register_rejects_duplicate_inactive_username(self, mock_create, _mock_ensure, users_service):
        """Inactive usernames remain reserved for registration."""
        service, repo = users_service
        repo.get_record_from_attributes.return_value = _stored_user(active=False)

        with pytest.raises(ValueError, match="Username already registered"):
            service.register(username="johndoe", email="new@example.local", password=VALID_PASSWORD)

        mock_create.assert_not_called()

    @patch.object(UsersService, "ensure_password_manager")
    @patch.object(UsersService, "_lookup_by_identifier")
    def test_register_duplicate_username(self, mock_lookup, _mock_ensure, users_service):
        """Duplicate username raises ValueError."""
        service, _repo = users_service
        mock_lookup.return_value = _stored_user()

        with pytest.raises(ValueError, match="Username already registered"):
            service.register(username="johndoe", email="new@example.local", password=VALID_PASSWORD)

    @patch.object(UsersService, "ensure_password_manager")
    @patch.object(UsersService, "_lookup_by_identifier")
    def test_register_duplicate_email(self, mock_lookup, _mock_ensure, users_service):
        """Duplicate email raises ValueError."""
        service, _repo = users_service

        def lookup_side_effect(identifier: str, *, require_active: bool = False) -> UsersDTO | None:
            del require_active
            return _stored_user() if "@" in identifier else None

        mock_lookup.side_effect = lookup_side_effect

        with pytest.raises(ValueError, match="Email already registered"):
            service.register(username="newuser", email="taken@example.local", password=VALID_PASSWORD)

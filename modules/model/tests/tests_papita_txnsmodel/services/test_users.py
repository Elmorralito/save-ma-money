"""Unit tests for UsersService authentication methods."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.users import UsersService


@pytest.fixture
def users_service():
    """UsersService with a mocked repository."""
    with patch("papita_txnsmodel.services.users.UsersRepository") as repo_cls:
        service = UsersService()
        service._repository = MagicMock()
        service._repository.get_record_from_attributes = MagicMock(return_value=None)
        service._repository.upsert_record = MagicMock()
        yield service, service._repository


class TestEnsurePasswordManager:
    """Tests for password manager bootstrap."""

    @patch("papita_txnsmodel.services.users.PasswordManagerFactory")
    def test_ensure_password_manager_calls_argon2(self, mock_factory_cls):
        """ensure_password_manager initializes Argon2 via the factory."""
        factory = MagicMock()
        mock_factory_cls.return_value = factory

        UsersService.ensure_password_manager()

        factory.get_password_manager.assert_called_once_with(keyword="argon2")


class TestVerifyCredentials:
    """Tests for credential verification."""

    @patch.object(UsersService, "ensure_password_manager")
    @patch("papita_txnsmodel.services.users.PasswordManagerFactory")
    def test_verify_credentials_success_by_username(self, mock_factory_cls, _mock_ensure, users_service):
        """Valid username + password returns the user DTO."""
        service, repo = users_service
        user_id = uuid.uuid4()
        stored_user = UsersDTO.model_construct(
            id=user_id,
            username="johndoe",
            email="user@example.com",
            password="$argon2$hash",
            active=True,
            deleted_at=None,
        )
        repo.get_record_from_attributes.return_value = stored_user

        password_manager = MagicMock()
        password_manager.verify_password.return_value = True
        mock_factory_cls.return_value.password_manager = password_manager

        result = service.verify_credentials("johndoe", "SecurePass1!")

        assert result is stored_user
        password_manager.verify_password.assert_called_once_with("SecurePass1!", "$argon2$hash")

    @patch.object(UsersService, "ensure_password_manager")
    @patch("papita_txnsmodel.services.users.PasswordManagerFactory")
    def test_verify_credentials_success_by_email(self, mock_factory_cls, _mock_ensure, users_service):
        """Email identifier is normalized to lowercase for lookup."""
        service, repo = users_service
        stored_user = UsersDTO.model_construct(
            id=uuid.uuid4(),
            username="johndoe",
            email="user@example.com",
            password="$argon2$hash",
            active=True,
            deleted_at=None,
        )
        repo.get_record_from_attributes.return_value = stored_user
        mock_factory_cls.return_value.password_manager.verify_password.return_value = True

        service.verify_credentials("User@Example.com", "SecurePass1!")

        lookup_probe = repo.get_record_from_attributes.call_args[0][0]
        assert lookup_probe.email == "user@example.com"

    @patch.object(UsersService, "ensure_password_manager")
    def test_verify_credentials_unknown_user(self, _mock_ensure, users_service):
        """Unknown identifier returns None."""
        service, repo = users_service
        repo.get_record_from_attributes.return_value = None

        assert service.verify_credentials("nobody", "SecurePass1!") is None

    @patch.object(UsersService, "ensure_password_manager")
    @patch("papita_txnsmodel.services.users.PasswordManagerFactory")
    def test_verify_credentials_wrong_password(self, mock_factory_cls, _mock_ensure, users_service):
        """Wrong password returns None (same as unknown user)."""
        service, repo = users_service
        repo.get_record_from_attributes.return_value = UsersDTO.model_construct(
            id=uuid.uuid4(),
            username="johndoe",
            email="user@example.com",
            password="$argon2$hash",
            active=True,
            deleted_at=None,
        )
        mock_factory_cls.return_value.password_manager.verify_password.return_value = False

        assert service.verify_credentials("johndoe", "WrongPass1!") is None

    @patch.object(UsersService, "ensure_password_manager")
    def test_verify_credentials_inactive_user(self, _mock_ensure, users_service):
        """Inactive users cannot authenticate."""
        service, repo = users_service
        repo.get_record_from_attributes.return_value = UsersDTO.model_construct(
            id=uuid.uuid4(),
            username="johndoe",
            email="user@example.com",
            password="$argon2$hash",
            active=False,
            deleted_at=None,
        )

        assert service.verify_credentials("johndoe", "SecurePass1!") is None


class TestRegister:
    """Tests for user registration."""

    @patch.object(UsersService, "ensure_password_manager")
    @patch.object(UsersService, "create")
    def test_register_success(self, mock_create, _mock_ensure, users_service):
        """Register creates a user when username and email are unique."""
        service, repo = users_service
        repo.get_record_from_attributes.return_value = None
        expected = UsersDTO.model_construct(
            id=uuid.uuid4(), username="johndoe", email="user@example.com", password="hash"
        )
        mock_create.return_value = expected

        result = service.register(username="johndoe", email="user@example.local", password="SecurePass1!")

        assert result is expected
        mock_create.assert_called_once()

    @patch.object(UsersService, "ensure_password_manager")
    @patch.object(UsersService, "_find_by_login_identifier")
    def test_register_duplicate_username(self, mock_find, _mock_ensure, users_service):
        """Duplicate username raises ValueError."""
        service, _repo = users_service
        mock_find.return_value = UsersDTO.model_construct(id=uuid.uuid4())

        with pytest.raises(ValueError, match="Username already registered"):
            service.register(username="johndoe", email="new@example.local", password="SecurePass1!")

    @patch.object(UsersService, "ensure_password_manager")
    @patch.object(UsersService, "_find_by_login_identifier")
    def test_register_duplicate_email(self, mock_find, _mock_ensure, users_service):
        """Duplicate email raises ValueError."""
        service, repo = users_service
        mock_find.return_value = None
        repo.get_record_from_attributes.return_value = UsersDTO.model_construct(id=uuid.uuid4())

        with pytest.raises(ValueError, match="Email already registered"):
            service.register(username="newuser", email="taken@example.local", password="SecurePass1!")

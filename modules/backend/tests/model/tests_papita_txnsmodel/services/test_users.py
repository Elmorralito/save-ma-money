"""Unit tests for UsersService authentication methods."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import ProviderType
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
        "auth_provider": "local",
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


class TestGetByEmail:
    """Tests for email lookup used by local Supabase login subject resolution."""

    def test_get_by_email_returns_none_for_blank(self, users_service):
        """Blank emails short-circuit without a repository call."""
        service, repo = users_service
        assert service.get_by_email("") is None
        assert service.get_by_email("   ") is None
        repo.get_record_from_attributes.assert_not_called()

    def test_get_by_email_normalizes_and_looks_up(self, users_service):
        """Emails are lowercased before lookup."""
        service, repo = users_service
        stored = _stored_user(email="user@example.local")
        repo.get_record_from_attributes.return_value = stored

        result = service.get_by_email("User@Example.local")

        assert result is stored
        repo.get_record_from_attributes.assert_called_once()


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
    def test_verify_credentials_rejects_supabase_user(self, _mock_ensure, users_service):
        """Supabase-managed rows cannot authenticate via local password verify."""
        service, repo = users_service
        repo.get_record_from_attributes.return_value = _stored_user(
            auth_provider="supabase",
            password=None,
        )

        assert service.verify_credentials("johndoe", VALID_PASSWORD) is None

    @patch.object(UsersService, "ensure_password_manager")
    def test_verify_credentials_inactive_user(self, _mock_ensure, users_service):
        """Inactive users cannot authenticate."""
        service, repo = users_service
        repo.get_record_from_attributes.return_value = _stored_user(active=False)

        assert service.verify_credentials("johndoe", VALID_PASSWORD) is None

    @patch.object(UsersService, "ensure_password_manager")
    @patch("papita_txnsmodel.services.users.PasswordManagerFactory")
    def test_verify_credentials_rehashes_outdated_argon2_hash(self, mock_factory_cls, _mock_ensure, users_service):
        """Successful login upgrades Argon2 parameters when the stored hash is weak."""
        from papita_txnsmodel.utils.hashutils import Argon2PasswordManager

        service, repo = users_service
        weak_manager = Argon2PasswordManager(time_cost=2)
        strong_manager = Argon2PasswordManager(time_cost=3)
        old_hash = weak_manager.hash_password(VALID_PASSWORD)
        stored_user = _stored_user(password=old_hash)
        repo.get_record_from_attributes.return_value = stored_user

        mock_factory_cls.return_value.password_manager = strong_manager

        result = service.verify_credentials("johndoe", VALID_PASSWORD)

        assert result is not None
        assert result.password != old_hash
        repo.upsert_record.assert_called_once()


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
        created_arg = mock_create.call_args.kwargs["obj"]
        assert created_arg.auth_provider == "local"
        assert created_arg.password is not None

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


class TestEnsureFromAuthSubject:
    """Provision-on-first-seen must not revive soft-deleted tenants."""

    @patch.object(UsersService, "create")
    @patch.object(UsersService, "get_owner", return_value=None)
    def test_rejects_inactive_primary_key(self, _mock_get_owner, mock_create, users_service):
        """Inactive rows for the Auth subject must not be upserted back to active."""
        service, repo = users_service
        subject = uuid.uuid4()
        repo.get_record_by_id.return_value = _stored_user(id=subject, active=False, auth_provider="supabase")

        with pytest.raises(ValueError, match="User is inactive or deleted"):
            service.ensure_from_auth_subject(subject=subject, email="john@example.local")

        mock_create.assert_not_called()
        assert repo.get_record_by_id.call_args.kwargs.get("include_deleted") is True

    @patch.object(UsersService, "create")
    @patch.object(UsersService, "get_owner", return_value=None)
    def test_rejects_soft_deleted_primary_key(self, _mock_get_owner, mock_create, users_service):
        """Soft-deleted Auth subjects stay banned across login/OAuth."""
        from datetime import datetime, timezone

        service, repo = users_service
        subject = uuid.uuid4()
        repo.get_record_by_id.return_value = _stored_user(
            id=subject,
            active=False,
            deleted_at=datetime.now(timezone.utc),
            auth_provider="supabase",
        )

        with pytest.raises(ValueError, match="User is inactive or deleted"):
            service.ensure_from_auth_subject(subject=subject, email="john@example.local")

        mock_create.assert_not_called()
        assert repo.get_record_by_id.call_args.kwargs.get("include_deleted") is True

    @patch.object(UsersService, "create")
    @patch.object(UsersService, "_lookup_by_identifier", return_value=None)
    def test_refreshes_profile_fields_on_existing(self, _mock_lookup, mock_create, users_service):
        """Return visits update display_name / phone / provider when provided."""
        service, _repo = users_service
        subject = uuid.uuid4()
        existing = _stored_user(
            id=subject,
            email="john@example.local",
            password=None,
            auth_provider="supabase",
            display_name=None,
            phone=None,
            provider_type=ProviderType.EMAIL,
        )
        updated = _stored_user(
            id=subject,
            email="john@example.local",
            password=None,
            auth_provider="supabase",
            display_name="John Doe",
            phone="+15551212",
            provider_type=ProviderType.GOOGLE,
        )
        mock_create.return_value = updated
        with patch.object(UsersService, "get_owner", return_value=existing):
            result = service.ensure_from_auth_subject(
                subject=subject,
                email="john@example.local",
                display_name="John Doe",
                phone="+15551212",
                provider_type=ProviderType.GOOGLE,
            )
        assert result is updated
        mock_create.assert_called_once()
        written = mock_create.call_args.kwargs["obj"]
        assert written.display_name == "John Doe"
        assert written.phone == "+15551212"
        assert written.provider_type == ProviderType.GOOGLE

    @patch.object(UsersService, "create")
    def test_skips_provider_refresh_when_omitted(self, mock_create, users_service):
        """Password/login return visits must not overwrite OAuth provider_type."""
        service, _repo = users_service
        subject = uuid.uuid4()
        existing = _stored_user(
            id=subject,
            email="john@example.local",
            password=None,
            auth_provider="supabase",
            display_name="Ada",
            provider_type=ProviderType.GOOGLE,
        )
        with patch.object(UsersService, "get_owner", return_value=existing):
            result = service.ensure_from_auth_subject(subject=subject, email="john@example.local")
        assert result is existing
        mock_create.assert_not_called()

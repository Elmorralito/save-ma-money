"""Unit tests for the base service module in the Papita Transactions system.

This test suite validates the BaseService class which provides common CRUD operations
for all services. All database connections and repository operations are mocked to
ensure test isolation and prevent actual database access.
"""

import uuid
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.access.base.repository import BaseRepository
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.services.base import BaseService


@pytest.fixture
def mock_repository():
    """Provide a mocked BaseRepository instance for service testing."""
    repository = MagicMock(spec=BaseRepository)
    repository.upsert_record = MagicMock()
    repository.hard_delete_records = MagicMock(return_value=pd.DataFrame([]))
    repository.soft_delete_records = MagicMock(return_value=pd.DataFrame([]))
    repository.get_record_by_id = MagicMock(return_value=None)
    repository.get_record_from_attributes = MagicMock(return_value=None)
    repository.get_records = MagicMock(return_value=pd.DataFrame([]))
    repository.get_records_from_attributes = MagicMock(return_value=pd.DataFrame([]))
    repository.upsert_records = MagicMock(return_value=0)
    return repository


@pytest.fixture
def mock_dto():
    """Provide a mocked TableDTO instance for testing."""
    dto = MagicMock(spec=TableDTO)
    dto.id = uuid.uuid4()
    dto.owner = None
    dto.model_fields_set = {"id", "owner"}
    dto.model_validate = MagicMock(return_value=dto)
    dto.model_construct = MagicMock(return_value=dto)
    return dto


@pytest.fixture
def service(mock_repository):
    """Provide a BaseService instance with mocked repository for testing."""
    with patch("papita_txnsmodel.services.base.BaseRepository", return_value=mock_repository):
        svc = BaseService()
        svc._repository = mock_repository
        return svc


class TestValidate:
    """Test suite for BaseService._validate method."""

    def test_validate_initializes_repository(self, mock_repository):
        """Test that _validate initializes the repository instance."""
        with patch("papita_txnsmodel.services.base.BaseRepository", return_value=mock_repository):
            service = BaseService()

        assert service._repository is not None
        assert hasattr(service._repository, "upsert_record")

    def test_validate_normalizes_on_conflict_do_enum(self, mock_repository):
        """Test that _validate converts OnUpsertConflictDo enum to proper format."""
        with patch("papita_txnsmodel.services.base.BaseRepository", return_value=mock_repository):
            service = BaseService(on_conflict_do=OnUpsertConflictDo.UPDATE)

        assert service.on_conflict_do == OnUpsertConflictDo.UPDATE

    def test_validate_normalizes_on_conflict_do_string(self, mock_repository):
        """Test that _validate converts string on_conflict_do to enum."""
        with patch("papita_txnsmodel.services.base.BaseRepository", return_value=mock_repository):
            service = BaseService(on_conflict_do="update")

        assert service.on_conflict_do == OnUpsertConflictDo.UPDATE


class TestCheckExpectedDtoType:
    """Test suite for BaseService.check_expected_dto_type method."""

    def test_check_expected_dto_type_raises_error_when_dto_type_not_class(self, service):
        """Test that check_expected_dto_type raises TypeError when dto_type is not a class."""
        service.dto_type = "not_a_class"
        dto = MagicMock(spec=TableDTO)

        with pytest.raises(TypeError, match="Expected type not properly configured"):
            service.check_expected_dto_type(dto)

    def test_check_expected_dto_type_raises_error_when_dto_is_none(self, service):
        """Test that check_expected_dto_type raises TypeError when dto is None."""
        with pytest.raises(TypeError, match="Provided DTO is not a class or instance."):
            service.check_expected_dto_type(None)

    def test_check_expected_dto_type_returns_type_for_valid_dto_instance(self, service, mock_dto):
        """Test that check_expected_dto_type returns correct type for valid DTO instance."""
        result = service.check_expected_dto_type(mock_dto)

        assert result == mock_dto.__class__

    def test_check_expected_dto_type_returns_type_for_valid_dto_class(self, service):
        """Test that check_expected_dto_type returns correct type for valid DTO class."""
        result = service.check_expected_dto_type(TableDTO)

        assert result == TableDTO

    def test_check_expected_dto_type_raises_error_for_incompatible_type(self, service):
        """Test that check_expected_dto_type raises TypeError for incompatible DTO type."""
        incompatible_dto = MagicMock()
        incompatible_dto.__class__ = type("IncompatibleDTO", (), {})

        with pytest.raises(TypeError, match="The type.*of the DTO differ from the expected"):
            service.check_expected_dto_type(incompatible_dto)


class TestClose:
    """Test suite for BaseService.close method."""

    def test_close_calls_connector_close(self, service):
        """Test that close calls the connector's close method."""
        mock_connector = MagicMock(spec=SQLDatabaseConnector)
        service.connector = mock_connector

        service.close()

        mock_connector.close.assert_called_once()


class TestCreate:
    """Test suite for BaseService.create method."""

    def test_create_with_dto_calls_upsert_record(self, service, mock_dto, mock_repository):
        """Test that create calls repository upsert_record when given a DTO."""
        service._repository = mock_repository

        result = service.create(obj=mock_dto)

        assert result == mock_dto
        mock_repository.upsert_record.assert_called_once_with(mock_dto, owner=None)

    def test_create_with_dict_validates_and_calls_upsert_record(self, service, mock_dto, mock_repository):
        """Test that create validates dict and calls repository upsert_record."""
        service._repository = mock_repository
        service.dto_type.model_validate = MagicMock(return_value=mock_dto)
        obj_dict = {"id": uuid.uuid4()}

        result = service.create(obj=obj_dict)

        assert result == mock_dto
        service.dto_type.model_validate.assert_called_once_with(
            obj_dict, strict=False, context={"by_alias": False, "by_name": True}
        )
        mock_repository.upsert_record.assert_called_once_with(mock_dto, owner=None)

    def test_create_removes_db_session_from_kwargs(self, service, mock_dto, mock_repository):
        """Test that create removes _db_session from kwargs before calling repository."""
        service._repository = mock_repository

        service.create(obj=mock_dto, _db_session=MagicMock(), other_param="value")

        call_kwargs = mock_repository.upsert_record.call_args[1]
        assert "_db_session" not in call_kwargs
        assert "other_param" in call_kwargs


class TestDelete:
    """Test suite for BaseService.delete method."""

    def test_delete_with_hard_true_calls_hard_delete_records(self, service, mock_dto, mock_repository):
        """Test that delete calls hard_delete_records when hard is True."""
        service._repository = mock_repository
        expected_df = pd.DataFrame({"id": [uuid.uuid4()]})
        mock_repository.hard_delete_records.return_value = expected_df

        result = service.delete(obj=mock_dto, hard=True)

        assert isinstance(result, pd.DataFrame)
        mock_repository.hard_delete_records.assert_called_once()
        mock_repository.soft_delete_records.assert_not_called()

    def test_delete_with_hard_false_calls_soft_delete_records(self, service, mock_dto, mock_repository):
        """Test that delete calls soft_delete_records when hard is False."""
        service._repository = mock_repository
        expected_df = pd.DataFrame({"id": [uuid.uuid4()]})
        mock_repository.soft_delete_records.return_value = expected_df

        result = service.delete(obj=mock_dto, hard=False)

        assert isinstance(result, pd.DataFrame)
        mock_repository.soft_delete_records.assert_called_once()
        mock_repository.hard_delete_records.assert_not_called()

    def test_delete_with_dict_validates_before_deleting(self, service, mock_dto, mock_repository):
        """Test that delete validates dict before calling repository delete methods."""
        service._repository = mock_repository
        service.dto_type.model_validate = MagicMock(return_value=mock_dto)
        obj_dict = {"id": uuid.uuid4()}

        service.delete(obj=obj_dict, hard=False)

        service.dto_type.model_validate.assert_called_once_with(
            obj_dict, strict=False, context={"by_alias": False, "by_name": True}
        )
        mock_repository.soft_delete_records.assert_called_once()

    def test_delete_removes_db_session_from_kwargs(self, service, mock_dto, mock_repository):
        """Test that delete removes _db_session from kwargs before calling repository."""
        service._repository = mock_repository

        service.delete(obj=mock_dto, hard=False, _db_session=MagicMock(), other_param="value")

        call_kwargs = mock_repository.soft_delete_records.call_args[1]
        assert "_db_session" not in call_kwargs
        assert "other_param" in call_kwargs


class TestGet:
    """Test suite for BaseService.get method."""

    def test_get_with_uuid_calls_get_record_by_id(self, service, mock_repository):
        """Test that get calls get_record_by_id when given a UUID."""
        service._repository = mock_repository
        test_id = uuid.uuid4()
        mock_dto = MagicMock(spec=TableDTO)
        mock_repository.get_record_by_id.return_value = mock_dto

        result = service.get(obj=test_id)

        assert result == mock_dto
        mock_repository.get_record_by_id.assert_called_once_with(test_id, owner=None, dto_type=service.dto_type)

    def test_get_with_uuid_returns_none_when_not_found(self, service, mock_repository):
        """Test that get returns None when UUID record is not found."""
        service._repository = mock_repository
        test_id = uuid.uuid4()
        mock_repository.get_record_by_id.return_value = None

        result = service.get(obj=test_id)

        assert result is None

    def test_get_with_dict_calls_get_record_from_attributes_when_not_found_by_id(self, service, mock_repository, mock_dto):
        """Test that get calls get_record_from_attributes when UUID lookup fails and obj is dict."""
        service._repository = mock_repository
        service.dto_type.model_construct = MagicMock(return_value=mock_dto)
        obj_dict = {"id": uuid.uuid4()}
        mock_repository.get_record_by_id.return_value = None
        mock_repository.get_record_from_attributes.return_value = mock_dto

        result = service.get(obj=obj_dict)

        assert result == mock_dto
        mock_repository.get_record_from_attributes.assert_called_once()

    def test_get_with_dto_calls_get_record_from_attributes_when_not_found_by_id(self, service, mock_repository, mock_dto):
        """Test that get calls get_record_from_attributes when UUID lookup fails and obj is DTO."""
        service._repository = mock_repository
        mock_repository.get_record_by_id.return_value = None
        mock_repository.get_record_from_attributes.return_value = mock_dto

        result = service.get(obj=mock_dto)

        assert result == mock_dto
        mock_repository.get_record_from_attributes.assert_called_once()


class TestGetOrCreate:
    """Test suite for BaseService.get_or_create method."""

    def test_get_or_create_returns_existing_record_when_found(self, service, mock_repository, mock_dto):
        """Test that get_or_create returns existing record when found by get."""
        service._repository = mock_repository
        test_id = uuid.uuid4()
        mock_repository.get_record_by_id.return_value = mock_dto

        result = service.get_or_create(obj=test_id)

        assert result == mock_dto
        mock_repository.get_record_by_id.assert_called_once()

    def test_get_or_create_raises_error_for_unsupported_type(self, service):
        """Test that get_or_create raises ValueError for unsupported input types."""
        with pytest.raises(ValueError, match="Input object not supported"):
            service.get_or_create(obj="not_supported")

    def test_get_or_create_raises_error_when_uuid_not_found(self, service, mock_repository):
        """Test that get_or_create raises ValueError when UUID does not exist."""
        service._repository = mock_repository
        test_id = uuid.uuid4()
        mock_repository.get_record_by_id.return_value = None

        with pytest.raises(ValueError, match="The id does not exist"):
            service.get_or_create(obj=test_id)

    def test_get_or_create_creates_record_when_dict_not_found(self, service, mock_repository, mock_dto):
        """Test that get_or_create creates record when dict is not found."""
        service._repository = mock_repository
        service.dto_type.model_validate = MagicMock(return_value=mock_dto)
        obj_dict = {"id": uuid.uuid4()}
        mock_repository.get_record_by_id.return_value = None
        mock_repository.get_record_from_attributes.return_value = None

        result = service.get_or_create(obj=obj_dict)

        assert result == mock_dto
        mock_repository.upsert_record.assert_called_once()


class TestGetRecords:
    """Test suite for BaseService.get_records method."""

    @patch("papita_txnsmodel.services.base.standardize_dataframe")
    def test_get_records_with_none_calls_get_records(self, mock_standardize, service, mock_repository):
        """Test that get_records calls repository get_records when dto is None."""
        service._repository = mock_repository
        expected_df = pd.DataFrame({"id": [uuid.uuid4()]})
        mock_repository.get_records.return_value = expected_df
        mock_standardize.return_value = expected_df

        result = service.get_records(dto=None)

        assert isinstance(result, pd.DataFrame)
        mock_repository.get_records.assert_called_once_with(owner=None, dto_type=service.dto_type)
        mock_standardize.assert_called_once()

    @patch("papita_txnsmodel.services.base.standardize_dataframe")
    def test_get_records_with_dict_calls_get_records_from_attributes(self, mock_standardize, service, mock_repository, mock_dto):
        """Test that get_records validates dict and calls get_records_from_attributes."""
        service._repository = mock_repository
        service.dto_type.model_validate = MagicMock(return_value=mock_dto)
        expected_df = pd.DataFrame({"id": [uuid.uuid4()]})
        mock_repository.get_records_from_attributes.return_value = expected_df
        mock_standardize.return_value = expected_df
        obj_dict = {"id": uuid.uuid4()}

        result = service.get_records(dto=obj_dict)

        assert isinstance(result, pd.DataFrame)
        service.dto_type.model_validate.assert_called_once_with(obj_dict, strict=True)
        mock_repository.get_records_from_attributes.assert_called_once()

    @patch("papita_txnsmodel.services.base.standardize_dataframe")
    def test_get_records_with_dto_calls_get_records_from_attributes(self, mock_standardize, service, mock_repository, mock_dto):
        """Test that get_records calls get_records_from_attributes when given a DTO."""
        service._repository = mock_repository
        expected_df = pd.DataFrame({"id": [uuid.uuid4()]})
        mock_repository.get_records_from_attributes.return_value = expected_df
        mock_standardize.return_value = expected_df

        result = service.get_records(dto=mock_dto)

        assert isinstance(result, pd.DataFrame)
        mock_repository.get_records_from_attributes.assert_called_once_with(mock_dto, owner=None)


class TestUpsertRecords:
    """Test suite for BaseService.upsert_records method."""

    @patch("papita_txnsmodel.services.base.standardize_dataframe")
    @patch("papita_txnsmodel.services.base.OnUpsertConflictDo")
    def test_upsert_records_calls_repository_upsert_records(self, mock_enum_class, mock_standardize, service, mock_repository):
        """Test that upsert_records standardizes DataFrame and calls repository upsert_records."""
        service._repository = mock_repository
        service.on_conflict_do = OnUpsertConflictDo.NOTHING

        def enum_converter(value):
            if isinstance(value, OnUpsertConflictDo):
                return value
            if isinstance(value, str):
                upper_value = value.upper()
                return OnUpsertConflictDo(upper_value)
            return value

        mock_enum_class.side_effect = enum_converter
        input_df = pd.DataFrame({"id": [uuid.uuid4()]})
        standardized_df = pd.DataFrame({"id": [uuid.uuid4()]})
        mock_standardize.return_value = standardized_df
        mock_repository.upsert_records.return_value = 1

        result = service.upsert_records(df=input_df)

        assert isinstance(result, pd.DataFrame)
        mock_standardize.assert_called_once_with(service.dto_type, input_df)
        mock_repository.upsert_records.assert_called_once()

    @patch("papita_txnsmodel.services.base.standardize_dataframe")
    @patch("papita_txnsmodel.services.base.OnUpsertConflictDo")
    def test_upsert_records_uses_default_on_conflict_do(self, mock_enum_class, mock_standardize, service, mock_repository):
        """Test that upsert_records uses service's default on_conflict_do when not provided."""
        service._repository = mock_repository
        service.on_conflict_do = OnUpsertConflictDo.UPDATE

        def enum_converter(value):
            if isinstance(value, OnUpsertConflictDo):
                return value
            if isinstance(value, str):
                upper_value = value.upper()
                return OnUpsertConflictDo(upper_value)
            return value

        mock_enum_class.side_effect = enum_converter
        input_df = pd.DataFrame({"id": [uuid.uuid4()]})
        standardized_df = pd.DataFrame({"id": [uuid.uuid4()]})
        mock_standardize.return_value = standardized_df
        mock_repository.upsert_records.return_value = 1

        service.upsert_records(df=input_df)

        call_kwargs = mock_repository.upsert_records.call_args[1]
        assert call_kwargs["on_conflict_do"] in (OnUpsertConflictDo.UPDATE, OnUpsertConflictDo.NOTHING)

    @patch("papita_txnsmodel.services.base.standardize_dataframe")
    @patch("papita_txnsmodel.services.base.OnUpsertConflictDo")
    def test_upsert_records_raises_error_when_tolerance_exceeded(self, mock_enum_class, mock_standardize, service, mock_repository):
        """Test that upsert_records raises RuntimeError when upsertions below tolerance threshold."""
        service._repository = mock_repository
        service.on_conflict_do = OnUpsertConflictDo.NOTHING
        service.missing_upsertions_tol = 0.1

        def enum_converter(value):
            if isinstance(value, OnUpsertConflictDo):
                return value
            if isinstance(value, str):
                upper_value = value.upper()
                return OnUpsertConflictDo(upper_value)
            return value

        mock_enum_class.side_effect = enum_converter
        input_df = pd.DataFrame({"id": [uuid.uuid4() for _ in range(10)]})
        standardized_df = pd.DataFrame({"id": [uuid.uuid4() for _ in range(10)]})
        mock_standardize.return_value = standardized_df
        mock_repository.upsert_records.return_value = 8

        with pytest.raises(RuntimeError, match="Not all records were correctly upserted"):
            service.upsert_records(df=input_df)

    @patch("papita_txnsmodel.services.base.standardize_dataframe")
    @patch("papita_txnsmodel.services.base.OnUpsertConflictDo")
    def test_upsert_records_removes_db_session_from_kwargs(self, mock_enum_class, mock_standardize, service, mock_repository):
        """Test that upsert_records removes _db_session from kwargs before calling repository."""
        service._repository = mock_repository
        service.on_conflict_do = OnUpsertConflictDo.NOTHING

        def enum_converter(value):
            if isinstance(value, OnUpsertConflictDo):
                return value
            if isinstance(value, str):
                upper_value = value.upper()
                return OnUpsertConflictDo(upper_value)
            return value

        mock_enum_class.side_effect = enum_converter
        input_df = pd.DataFrame({"id": [uuid.uuid4()]})
        standardized_df = pd.DataFrame({"id": [uuid.uuid4()]})
        mock_standardize.return_value = standardized_df
        mock_repository.upsert_records.return_value = 1

        service.upsert_records(df=input_df, _db_session=MagicMock(), other_param="value")

        call_kwargs = mock_repository.upsert_records.call_args[1]
        assert "_db_session" not in call_kwargs
        assert "other_param" in call_kwargs

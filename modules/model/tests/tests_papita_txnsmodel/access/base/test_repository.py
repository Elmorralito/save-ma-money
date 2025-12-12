"""Unit tests for the base repository module in the Papita Transactions system.

This test suite validates database repository operations including querying, inserting,
updating, deleting records, and upsert operations. All database connections and operations
are mocked to ensure test isolation and prevent actual database access.
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest
from sqlalchemy import inspect as db_inspector
from sqlmodel import Session, delete, update
from sqlmodel.sql.expression import Select

from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.access.base.repository import BaseRepository
from papita_txnsmodel.database.upsert import OnUpsertConflictDo, UpserterFactory
from papita_txnsmodel.model.base import BaseSQLModel


@pytest.fixture
def mock_session():
    """Provide a mocked SQLModel session for database operations testing."""
    session = MagicMock(spec=Session)
    session.exec = MagicMock()
    session.add = MagicMock()
    session.merge = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.refresh = MagicMock()
    return session


@pytest.fixture
def mock_dao():
    """Provide a mocked DAO (SQLModel) class for testing."""
    dao_class = MagicMock(spec=BaseSQLModel)
    dao_class.__tablename__ = "test_table"
    dao_class.id = MagicMock()
    return dao_class


@pytest.fixture
def mock_dto(mock_dao):
    """Provide a mocked DTO class for testing."""
    dto_class = MagicMock(spec=TableDTO)
    dto_class.__dao_type__ = mock_dao
    dto_class.standardized_dataframe = MagicMock()
    return dto_class


@pytest.fixture
def sample_dataframe():
    """Provide a sample DataFrame for repository operations testing."""
    return pd.DataFrame({"id": [uuid.uuid4(), uuid.uuid4()], "name": ["Alice", "Bob"], "value": [10, 20]})


@pytest.fixture
def repository():
    """Provide a BaseRepository instance for testing."""
    return BaseRepository()


@pytest.fixture
def mock_connector_connected():
    """Mock SQLDatabaseConnector.connected to return True for testing."""
    with patch("papita_txnsmodel.access.base.repository.SQLDatabaseConnector.connected", return_value=True):
        yield


class TestHardDeleteRecords:
    """Test suite for BaseRepository.hard_delete_records method."""

    @patch("papita_txnsmodel.access.base.repository.delete")
    @patch("papita_txnsmodel.access.base.repository.db_inspector")
    def test_hard_delete_records_deletes_matching_records(self, mock_inspector, mock_delete, repository, mock_dto, mock_session, sample_dataframe, mock_connector_connected):
        """Test that hard_delete_records permanently deletes records matching query filters."""
        mock_dao = MagicMock()
        mock_dto.__dao_type__ = mock_dao
        mock_pk_col = MagicMock()
        mock_pk_col.name = "id"
        mock_inspector_obj = MagicMock()
        mock_inspector_obj.primary_key = [mock_pk_col]
        mock_inspector.return_value = mock_inspector_obj
        repository.get_records = MagicMock(return_value=sample_dataframe)
        mock_statement = MagicMock()
        mock_statement.where.return_value = mock_statement
        mock_delete.return_value = mock_statement
        mock_exec_result = MagicMock()
        mock_session.exec.return_value = mock_exec_result

        result = repository.hard_delete_records(dto_type=mock_dto, _db_session=mock_session, _testing_=True)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        mock_session.exec.assert_called()
        mock_session.commit.assert_called_once()

    def test_hard_delete_records_returns_empty_when_no_records_found(self, repository, mock_dto, mock_session, mock_connector_connected):
        """Test that hard_delete_records returns empty DataFrame when no records match filters."""
        repository.get_records = MagicMock(return_value=pd.DataFrame([]))

        result = repository.hard_delete_records(dto_type=mock_dto, _db_session=mock_session, _testing_=True)

        assert isinstance(result, pd.DataFrame)
        assert result.empty
        mock_session.exec.assert_not_called()

    @patch("papita_txnsmodel.access.base.repository.db_inspector")
    def test_hard_delete_records_rolls_back_on_error(self, mock_inspector, repository, mock_dto, mock_session, sample_dataframe, mock_connector_connected):
        """Test that hard_delete_records rolls back transaction when deletion fails."""
        mock_dao = MagicMock()
        mock_dto.__dao_type__ = mock_dao
        mock_pk_col = MagicMock()
        mock_pk_col.name = "id"
        mock_inspector_obj = MagicMock()
        mock_inspector_obj.primary_key = [mock_pk_col]
        mock_inspector.return_value = mock_inspector_obj
        repository.get_records = MagicMock(return_value=sample_dataframe)
        mock_session.exec.side_effect = Exception("Database error")

        result = repository.hard_delete_records(dto_type=mock_dto, _db_session=mock_session, _testing_=True)

        assert isinstance(result, pd.DataFrame)
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()


class TestSoftDeleteRecords:
    """Test suite for BaseRepository.soft_delete_records method."""

    @patch("papita_txnsmodel.access.base.repository.update")
    @patch("papita_txnsmodel.access.base.repository.db_inspector")
    @patch("papita_txnsmodel.access.base.repository.datetime")
    def test_soft_delete_records_marks_records_as_deleted(self, mock_datetime, mock_inspector, mock_update, repository, mock_dto, mock_session, sample_dataframe, mock_connector_connected):
        """Test that soft_delete_records marks records as inactive with deletion timestamp."""
        mock_dao = MagicMock()
        mock_dto.__dao_type__ = mock_dao
        mock_pk_col = MagicMock()
        mock_pk_col.name = "id"
        mock_inspector_obj = MagicMock()
        mock_inspector_obj.primary_key = [mock_pk_col]
        mock_inspector.return_value = mock_inspector_obj
        mock_datetime.now.return_value = datetime(2023, 1, 1)
        repository.get_records = MagicMock(return_value=sample_dataframe)
        mock_statement = MagicMock()
        mock_statement.where.return_value = mock_statement
        mock_statement.values.return_value = mock_statement
        mock_update.return_value = mock_statement
        mock_exec_result = MagicMock()
        mock_session.exec.return_value = mock_exec_result

        result = repository.soft_delete_records(dto_type=mock_dto, _db_session=mock_session, _testing_=True)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        mock_session.exec.assert_called()
        mock_session.commit.assert_called_once()

    def test_soft_delete_records_returns_empty_when_no_records_found(self, repository, mock_dto, mock_session, mock_connector_connected):
        """Test that soft_delete_records returns empty DataFrame when no records match filters."""
        repository.get_records = MagicMock(return_value=pd.DataFrame([]))

        result = repository.soft_delete_records(dto_type=mock_dto, _db_session=mock_session, _testing_=True)

        assert isinstance(result, pd.DataFrame)
        assert result.empty
        mock_session.exec.assert_not_called()

    @patch("papita_txnsmodel.access.base.repository.db_inspector")
    def test_soft_delete_records_rolls_back_on_error(self, mock_inspector, repository, mock_dto, mock_session, sample_dataframe, mock_connector_connected):
        """Test that soft_delete_records rolls back transaction when update fails."""
        mock_dao = MagicMock()
        mock_dto.__dao_type__ = mock_dao
        mock_pk_col = MagicMock()
        mock_pk_col.name = "id"
        mock_inspector_obj = MagicMock()
        mock_inspector_obj.primary_key = [mock_pk_col]
        mock_inspector.return_value = mock_inspector_obj
        repository.get_records = MagicMock(return_value=sample_dataframe)
        mock_session.exec.side_effect = Exception("Database error")

        result = repository.soft_delete_records(dto_type=mock_dto, _db_session=mock_session, _testing_=True)

        assert isinstance(result, pd.DataFrame)
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()


class TestRunQuery:
    """Test suite for BaseRepository.run_query method."""

    def test_run_query_returns_dataframe_with_results(self, repository, mock_session, mock_connector_connected):
        """Test that run_query returns DataFrame containing query results."""
        mock_statement = MagicMock(spec=Select)
        mock_result = MagicMock()
        mock_result.all.return_value = [MagicMock(id=uuid.uuid4(), name="Test")]
        mock_session.exec.return_value = mock_result

        result = repository.run_query(mock_statement, _db_session=mock_session, _testing_=True)

        assert isinstance(result, pd.DataFrame)
        mock_session.exec.assert_called_once_with(mock_statement, params=None)

    def test_run_query_handles_query_parameters(self, repository, mock_session, mock_connector_connected):
        """Test that run_query correctly passes query parameters to session exec."""
        mock_statement = MagicMock(spec=Select)
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.exec.return_value = mock_result
        params = {"id": uuid.uuid4()}

        result = repository.run_query(mock_statement, _db_session=mock_session, params=params, _testing_=True)

        assert isinstance(result, pd.DataFrame)
        mock_session.exec.assert_called_once_with(mock_statement, params=params)

    def test_run_query_raises_type_error_for_invalid_session(self, repository, mock_connector_connected):
        """Test that run_query raises TypeError when session is not a Session object."""
        mock_statement = MagicMock(spec=Select)
        invalid_session = "not_a_session"

        with pytest.raises(TypeError, match="Session not supported"):
            repository.run_query(mock_statement, _db_session=invalid_session, _testing_=True)

    def test_run_query_returns_empty_dataframe_on_error(self, repository, mock_session, mock_connector_connected):
        """Test that run_query returns empty DataFrame when query execution fails."""
        mock_statement = MagicMock(spec=Select)
        mock_session.exec.side_effect = Exception("Query failed")

        result = repository.run_query(mock_statement, _db_session=mock_session, _testing_=True)

        assert isinstance(result, pd.DataFrame)
        assert result.empty


class TestUpsertRecord:
    """Test suite for BaseRepository.upsert_record method."""

    def test_upsert_record_raises_value_error_when_dto_has_no_id(self, repository, mock_dto, mock_session, mock_connector_connected):
        """Test that upsert_record raises ValueError when DTO has no ID."""
        mock_dto_instance = MagicMock()
        mock_dto_instance.id = None
        mock_dto_instance.to_dao = MagicMock()

        with pytest.raises(ValueError, match="There is no id in the DTO"):
            repository.upsert_record(mock_dto_instance, _db_session=mock_session, _testing_=True)

    @patch("papita_txnsmodel.access.base.repository.isinstance")
    def test_upsert_record_merges_record_when_not_found(self, mock_isinstance, repository, mock_dto, mock_session, mock_connector_connected):
        """Test that upsert_record merges record when record does not exist."""
        test_id = uuid.uuid4()
        mock_dto_instance = MagicMock()
        mock_dto_instance.id = test_id
        mock_dao = MagicMock()
        mock_dto_instance.to_dao.return_value = mock_dao
        repository.get_record_by_id = MagicMock(return_value=None)
        mock_dao.model_dump.return_value = {"id": test_id, "name": "Test"}
        mock_dto_instance.model_validate.return_value = mock_dto_instance
        mock_isinstance.return_value = False

        result = repository.upsert_record(mock_dto_instance, _db_session=mock_session, _testing_=True)

        mock_session.merge.assert_called_once_with(mock_dao)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_dao)
        assert result is not None

    @patch("papita_txnsmodel.access.base.repository.isinstance")
    def test_upsert_record_merges_existing_record_when_found(self, mock_isinstance, repository, mock_dto, mock_session, mock_connector_connected):
        """Test that upsert_record merges record when record already exists."""
        test_id = uuid.uuid4()
        mock_dto_instance = MagicMock()
        mock_dto_instance.id = test_id
        mock_dao = MagicMock()
        mock_dto_instance.to_dao.return_value = mock_dao
        repository.get_record_by_id = MagicMock(return_value=mock_dto_instance)
        mock_dao.model_dump.return_value = {"id": test_id, "name": "Test"}
        mock_dto_instance.model_validate.return_value = mock_dto_instance
        mock_isinstance.return_value = False

        result = repository.upsert_record(mock_dto_instance, _db_session=mock_session, _testing_=True)

        mock_session.merge.assert_called_once_with(mock_dao)
        mock_session.commit.assert_called_once()
        assert result is not None

    def test_upsert_record_rolls_back_on_error(self, repository, mock_dto, mock_session, mock_connector_connected):
        """Test that upsert_record rolls back transaction when upsert fails."""
        test_id = uuid.uuid4()
        mock_dto_instance = MagicMock()
        mock_dto_instance.id = test_id
        mock_dao = MagicMock()
        mock_dto_instance.to_dao.return_value = mock_dao
        repository.get_record_by_id = MagicMock(return_value=None)
        mock_session.merge.side_effect = Exception("Database error")

        result = repository.upsert_record(mock_dto_instance, _db_session=mock_session, _testing_=True)

        assert result is None
        mock_session.rollback.assert_called_once()


class TestUpsertRecords:
    """Test suite for BaseRepository.upsert_records method."""

    @patch("papita_txnsmodel.access.base.repository.UpserterFactory")
    @patch("papita_txnsmodel.access.base.repository.db_inspector")
    def test_upsert_records_calls_upserter_factory(self, mock_inspector, mock_factory, repository, mock_dto, mock_session, sample_dataframe, mock_connector_connected):
        """Test that upsert_records uses UpserterFactory to perform bulk upsert."""
        mock_dto.__dao_type__ = MagicMock()
        mock_dto.__dao_type__.__tablename__ = "test_table"
        mock_pk_col = MagicMock()
        mock_pk_col.name = "id"
        mock_inspector_obj = MagicMock()
        mock_inspector_obj.primary_key = [mock_pk_col]
        mock_inspector.return_value = mock_inspector_obj
        mock_upserter = MagicMock()
        mock_upserter.upsert.return_value = 2
        mock_factory.get_upserter.return_value = mock_upserter

        result = repository.upsert_records(mock_dto, sample_dataframe, _db_session=mock_session, _testing_=True)

        assert result == 2
        mock_factory.get_upserter.assert_called_once_with(mock_session)
        mock_upserter.upsert.assert_called_once()

    @patch("papita_txnsmodel.access.base.repository.UpserterFactory")
    @patch("papita_txnsmodel.access.base.repository.db_inspector")
    def test_upsert_records_passes_conflict_action_to_upserter(self, mock_inspector, mock_factory, repository, mock_dto, mock_session, sample_dataframe, mock_connector_connected):
        """Test that upsert_records correctly passes on_conflict_do parameter to upserter."""
        mock_dto.__dao_type__ = MagicMock()
        mock_dto.__dao_type__.__tablename__ = "test_table"
        mock_pk_col = MagicMock()
        mock_pk_col.name = "id"
        mock_inspector_obj = MagicMock()
        mock_inspector_obj.primary_key = [mock_pk_col]
        mock_inspector.return_value = mock_inspector_obj
        mock_upserter = MagicMock()
        mock_upserter.upsert.return_value = 2
        mock_factory.get_upserter.return_value = mock_upserter

        result = repository.upsert_records(
            mock_dto, sample_dataframe, _db_session=mock_session, on_conflict_do=OnUpsertConflictDo.UPDATE, _testing_=True
        )

        assert result == 2
        call_kwargs = mock_upserter.upsert.call_args[1]
        assert call_kwargs["on_conflict_do"] == OnUpsertConflictDo.UPDATE


class TestGetRecords:
    """Test suite for BaseRepository.get_records method."""

    @patch("papita_txnsmodel.access.base.repository.Select")
    def test_get_records_returns_dataframe_with_query_filters(self, mock_select, repository, mock_dto):
        """Test that get_records returns DataFrame with records matching query filters."""
        expected_df = pd.DataFrame({"id": [uuid.uuid4()], "name": ["Test"]})
        repository.run_query = MagicMock(return_value=expected_df)
        mock_statement = MagicMock()
        mock_statement.where.return_value = mock_statement
        mock_select.return_value = mock_statement
        mock_filter = MagicMock()

        result = repository.get_records(mock_filter, dto_type=mock_dto)

        assert isinstance(result, pd.DataFrame)
        repository.run_query.assert_called_once()

    @patch("papita_txnsmodel.access.base.repository.Select")
    def test_get_records_returns_empty_dataframe_when_no_results(self, mock_select, repository, mock_dto):
        """Test that get_records returns empty DataFrame when no records match filters."""
        repository.run_query = MagicMock(return_value=pd.DataFrame([]))
        mock_statement = MagicMock()
        mock_statement.where.return_value = mock_statement
        mock_select.return_value = mock_statement
        mock_filter = MagicMock()

        result = repository.get_records(mock_filter, dto_type=mock_dto)

        assert isinstance(result, pd.DataFrame)
        assert result.empty


class TestGetRecordsFromAttributes:
    """Test suite for BaseRepository.get_records_from_attributes method."""

    def test_get_records_from_attributes_constructs_filters_from_dto(self, repository, mock_dto):
        """Test that get_records_from_attributes constructs query filters from DTO attributes."""
        mock_dto_instance = MagicMock()
        mock_dto_instance.__dao_type__ = MagicMock()
        mock_dto_instance.model_fields_set = {"id", "name"}
        mock_dto_instance.id = uuid.uuid4()
        mock_dto_instance.name = "Test"
        repository.get_records = MagicMock(return_value=pd.DataFrame([]))

        result = repository.get_records_from_attributes(mock_dto_instance)

        assert isinstance(result, pd.DataFrame)
        repository.get_records.assert_called_once()


class TestGetRecordById:
    """Test suite for BaseRepository.get_record_by_id method."""

    def test_get_record_by_id_returns_record_when_found(self, repository, mock_dto):
        """Test that get_record_by_id returns DTO when record with given ID exists."""
        test_id = uuid.uuid4()
        mock_dto.__dao_type__ = MagicMock()
        mock_dto.__dao_type__.id = MagicMock()
        sample_df = pd.DataFrame({"id": [test_id], "name": ["Test"]})
        repository.get_records = MagicMock(return_value=sample_df)
        mock_standardized_df = pd.DataFrame({"id": [test_id], "name": ["Test"]})
        mock_dto.standardized_dataframe.return_value = mock_standardized_df

        result = repository.get_record_by_id(test_id, mock_dto)

        assert result is not None
        assert isinstance(result, dict)

    def test_get_record_by_id_returns_none_when_not_found(self, repository, mock_dto):
        """Test that get_record_by_id returns None when record with given ID does not exist."""
        test_id = uuid.uuid4()
        mock_dto.__dao_type__ = MagicMock()
        mock_dto.__dao_type__.id = MagicMock()
        repository.get_records = MagicMock(return_value=pd.DataFrame([]))

        result = repository.get_record_by_id(test_id, mock_dto)

        assert result is None

    def test_get_record_by_id_converts_string_to_uuid(self, repository, mock_dto):
        """Test that get_record_by_id converts string ID to UUID."""
        test_id_str = str(uuid.uuid4())
        test_id = uuid.UUID(test_id_str)
        mock_dto.__dao_type__ = MagicMock()
        mock_dto.__dao_type__.id = MagicMock()
        repository.get_records = MagicMock(return_value=pd.DataFrame([]))

        result = repository.get_record_by_id(test_id_str, mock_dto)

        assert result is None
        repository.get_records.assert_called_once()

    def test_get_record_by_id_raises_type_error_for_invalid_id_type(self, repository, mock_dto):
        """Test that get_record_by_id raises TypeError for unsupported ID types."""
        with pytest.raises(TypeError, match="Expected 'UUID'"):
            repository.get_record_by_id(12345, mock_dto)


class TestGetRecordFromAttributes:
    """Test suite for BaseRepository.get_record_from_attributes method."""

    def test_get_record_from_attributes_returns_first_matching_record(self, repository, mock_dto):
        """Test that get_record_from_attributes returns first record matching DTO attributes."""
        mock_dto_instance = MagicMock()
        sample_df = pd.DataFrame({"id": [uuid.uuid4()], "name": ["Test"]})
        repository.get_records_from_attributes = MagicMock(return_value=sample_df)
        mock_standardized_df = pd.DataFrame({"id": [uuid.uuid4()], "name": ["Test"]})
        mock_dto_instance.standardized_dataframe.return_value = mock_standardized_df

        result = repository.get_record_from_attributes(mock_dto_instance)

        assert result is not None
        assert isinstance(result, dict)

    def test_get_record_from_attributes_returns_none_when_no_match(self, repository, mock_dto):
        """Test that get_record_from_attributes returns None when no records match attributes."""
        mock_dto_instance = MagicMock()
        repository.get_records_from_attributes = MagicMock(return_value=pd.DataFrame([]))

        result = repository.get_record_from_attributes(mock_dto_instance)

        assert result is None

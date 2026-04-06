"""Service-layer foundation for the Papita Transactions data model.

Defines ``BaseService``, a Pydantic ``BaseModel`` that wires SQLModel DAO types to
``BaseRepository`` for create, read, update-style upsert, delete, and bulk upsert
flows. Callers typically hold a ``Session`` on the service (``db_session``) and
delegate persistence to the injected repository.

Key behaviors:
    * Validates that inputs match ``dao_type`` before repository calls.
    * Normalizes conflict policy to ``OnUpsertConflictDo`` and enforces a configurable
      lower bound on successful upsert row counts.
    * Parses dict, ``pandas.Series``, or ``pandas.DataFrame`` inputs into the
      service's ``dao_type`` via ``parse_dto``.

Major objects:
    * ``BaseService``: Default CRUD and upsert orchestration for a single DAO type.
"""

import inspect
import logging
import uuid
from typing import Annotated, Any, Dict, Literal, Type

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from papita_txnsmodel.access.base import BaseRepository
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.model.base import BaseSQLModel

logger = logging.getLogger(__name__)


class BaseService(BaseModel):
    """Coordinate repository access and validation for one SQLModel table type.

    Subclasses set ``dao_type`` and ``repository_type`` to bind a concrete model and
    repository. Operations use ``self.db_session`` when calling repository methods;
    ensure the session is set for the current unit of work before mutating calls.

    Attributes:
        dao_type: SQLModel class (``table=True``) this service reads and writes.
        repository_type: Repository class used for database operations.
        missing_upsertions_tol: Minimum acceptable fraction of rows successfully
            upserted (0–0.5). If the repository reports fewer successes, ``upsert_records``
            raises ``RuntimeError``.
        on_conflict_do: Default ``OnUpsertConflictDo`` strategy for upserts (also
            overridable per call via ``kwargs``).
        db_session: Active SQLAlchemy/SQLModel session for repository calls, or
            ``None`` if the caller supplies session context elsewhere.
        repository: Lazily constructed instance of ``repository_type``; set during
            model validation.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    dao_type: Type[BaseSQLModel] = BaseSQLModel
    repository_type: Type[BaseRepository] = BaseRepository
    missing_upsertions_tol: Annotated[float, Field(ge=0, le=0.5)] = 0.01
    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.NOTHING
    db_session: Session | None = None

    repository: BaseRepository | None = None

    @model_validator(mode="after")
    def _normalize_model(self) -> "BaseService":
        """Normalize the model after initialization."""
        self.repository = self.repository_type()
        self.on_conflict_do = OnUpsertConflictDo(getattr(self.on_conflict_do, "value", self.on_conflict_do).upper())
        return self

    def check_expected_dao_type(self, dao: Type[BaseSQLModel] | BaseSQLModel | None) -> Type[BaseSQLModel]:
        """Ensure the given DAO class or instance is compatible with ``dao_type``.

        Args:
            dao: DAO class or instance to validate, or ``None``.

        Returns:
            The concrete DAO type (class) that was validated.

        Raises:
            TypeError: If ``dao_type`` is not a class, if ``dao`` is missing, or if
                the resolved type is not a subclass of ``self.dao_type``.
        """
        if not inspect.isclass(self.dao_type):
            raise TypeError("Expected type not properly configured.")

        if not dao:
            raise TypeError("Provided DAO is not a class or instance.")

        dao_type = dao if inspect.isclass(dao) else dao.__class__
        if not issubclass(dao_type, self.dao_type):  # type: ignore[arg-type]
            raise TypeError(
                f"The type {dao_type.__name__} of the DTO differ from the expected " + self.dao_type.__name__
            )

        return dao_type  # type: ignore[return-value]

    def create(self, *, obj: BaseSQLModel | dict[str, Any], **kwargs) -> BaseSQLModel:
        """Insert or merge a single record via the repository upsert path.

        Args:
            obj: New row as a DAO instance or attribute dictionary.
            **kwargs: Forwarded to ``repository.upsert_record`` (e.g. dialect-specific
                options). ``_db_session``, if present, is removed before the call.

        Returns:
            The parsed DAO that was passed to the repository (same logical row as
            ``obj`` after validation).

        Raises:
            TypeError: If the parsed object does not match ``dao_type``.
        """
        parsed_obj = self.parse_dto(obj)
        self.check_expected_dao_type(parsed_obj)
        kwargs.pop("_db_session", None)
        self.repository.upsert_record(dao=parsed_obj, db_session=self.db_session, **kwargs)
        return parsed_obj

    def delete(self, *, obj: BaseSQLModel | dict[str, Any], hard: bool = False, **kwargs) -> pd.DataFrame:
        """Delete rows matching non-null attributes on the parsed object.

        Builds equality filters from ``parsed_obj.model_fields_set`` against
        ``self.dao_type.__dao_type__`` (the mapped SQL table model).

        Args:
            obj: Row identifier payload as DAO or dict.
            hard: If ``True``, permanently remove rows; otherwise soft-delete (active
                flag and timestamps per repository defaults).
            **kwargs: Forwarded to ``hard_delete_records`` or ``soft_delete_records``.
                ``_db_session`` is stripped before the call.

        Returns:
            DataFrame of rows that were deleted (shape and columns per repository).

        Raises:
            TypeError: If the parsed object does not match ``dao_type``.
        """
        parsed_obj = self.parse_dto(obj)
        self.check_expected_dao_type(parsed_obj)
        dao = self.dao_type.__dao_type__
        query_filters = [
            getattr(dao, key) == getattr(parsed_obj, key)
            for key in parsed_obj.model_fields_set
            if getattr(parsed_obj, key, None) is not None and hasattr(dao, key)
        ]
        kwargs.pop("_db_session", None)
        if hard:
            return self.repository.hard_delete_records(
                *query_filters, dao_type=self.dao_type, db_session=self.db_session, **kwargs
            )

        return self.repository.soft_delete_records(
            *query_filters, dao_type=self.dao_type, db_session=self.db_session, **kwargs
        )

    def get(self, *, obj: BaseSQLModel | str | Dict[str, Any] | uuid.UUID, **kwargs) -> BaseSQLModel | None:
        """Load one row by primary key, falling back to attribute match when needed.

        Attempts ``get_record_by_id`` first. If that returns empty and ``obj`` is a
        dict or DAO instance, parses it and tries ``get_record_from_attributes``.

        Args:
            obj: Lookup key (e.g. UUID), or a dict/DAO with fields to match.
            **kwargs: Forwarded to repository getters.

        Returns:
            The loaded DAO, or ``None`` if no row matches.

        Raises:
            TypeError: If a dict/DAO path is used and the type does not match
                ``dao_type``.
        """
        dto = self.repository.get_record_by_id(obj, dao_type=self.dao_type, db_session=self.db_session, **kwargs)
        if not dto and isinstance(obj, (dict, self.dao_type)):
            obj = self.parse_dto(obj, strict=True, by_alias=True)
            self.check_expected_dao_type(obj)
            dto = self.repository.get_record_from_attributes(dto=obj, db_session=self.db_session, **kwargs)

        return dto

    def get_or_create(self, *, obj: BaseSQLModel | Dict[str, Any] | str | uuid.UUID, **kwargs) -> BaseSQLModel:
        """Return an existing row or create it when the input is not a bare UUID miss.

        Args:
            obj: DAO, dict of attributes, or UUID of an existing row.
            **kwargs: Forwarded to ``get`` and, when creating, to ``create``.

        Returns:
            Existing or newly created DAO instance.

        Raises:
            ValueError: If ``obj`` is not a DAO, dict, or UUID; or if ``obj`` is a
                UUID that does not exist (no attributes available to create).
        """
        if not isinstance(obj, (BaseSQLModel, dict, str, uuid.UUID)):
            raise ValueError("Input object not supported. Supported: BaseSQLModel | dict | uuid.UUID")

        dto = self.get(obj=obj, **kwargs)
        if isinstance(dto, self.dao_type):
            return dto

        if isinstance(obj, (str, uuid.UUID)):
            raise ValueError("The id does not exist.")

        return self.create(obj=obj, **kwargs)

    def get_records(self, *, obj: BaseSQLModel | Dict[str, Any] | None, **kwargs) -> pd.DataFrame:
        """Query zero or more rows and return a standardized DataFrame.

        Args:
            dto: When ``None``, selects all rows for ``dao_type`` (subject to
                repository behavior). Otherwise filters by non-null attributes on the
                parsed/validated DAO.
            **kwargs: Forwarded to ``get_records`` / ``get_records_from_attributes`` and
                to ``standardized_dataframe``.

        Returns:
            DataFrame in the shape produced by ``dao_type.standardized_dataframe``.

        Raises:
            TypeError: When ``dto`` is provided and does not match ``dao_type``.
        """
        dto = self.parse_dto(obj, strict=True, by_alias=True) if obj else None
        if not dto:
            records_df = self.repository.get_records(dao_type=self.dao_type, db_session=self.db_session)
        else:
            parsed_dto = self.dao_type.model_validate(dto, strict=True) if isinstance(dto, dict) else dto
            self.check_expected_dao_type(parsed_dto)
            records_df = self.repository.get_records_from_attributes(
                dao=parsed_dto, db_session=self.db_session, **kwargs
            )

        return self.dao_type.standardized_dataframe(records_df, **kwargs)

    def parse_dto(
        self,
        obj: BaseSQLModel | str | Dict[str, Any] | uuid.UUID | pd.Series | pd.DataFrame,
        strict: bool = False,
        by_alias: bool = False,
        position: int | Literal["first", "last"] | None = None,
    ) -> BaseSQLModel:
        """Coerce supported container types into an instance of ``dao_type``.

        Args:
            obj: Dict, ``pandas.Series``, ``pandas.DataFrame``, or existing DAO
                instance.
            strict: Passed to Pydantic ``model_validate`` when constructing the DAO.
            by_alias: When ``True``, validation prefers field aliases in the input
                mapping context.
            position: Row index for DataFrame inputs: ``0``/``"first"`` (default) or
                ``-1``/``"last"``. Ignored for non-DataFrame ``obj``.

        Returns:
            Validated instance of ``self.dao_type``.

        Raises:
            TypeError: If ``obj`` is not one of the supported types.
        """
        if isinstance(obj, (str, uuid.UUID)):
            return self.dao_type.model_construct(id=obj)

        if isinstance(obj, dict):
            return self.dao_type.model_validate(
                obj, strict=strict, context={"by_alias": by_alias, "by_name": not by_alias}
            )

        if isinstance(obj, pd.Series):
            return self.dao_type.model_validate(
                obj.to_dict(), strict=strict, context={"by_alias": by_alias, "by_name": not by_alias}
            )

        if isinstance(obj, pd.DataFrame):
            if position == "first":
                position = 0
            elif position == "last":
                position = -1
            else:
                position = 0

            return self.dao_type.model_validate(
                obj.iloc[position].to_dict(), strict=strict, context={"by_alias": by_alias, "by_name": not by_alias}
            )

        if isinstance(obj, self.dao_type):
            return obj

        raise TypeError(f"Expected BaseSQLModel | dict, got {type(obj)}")

    def upsert_records(self, *, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Bulk upsert rows from a DataFrame with tolerance checking.

        Args:
            df: Tabular batch aligned with ``dao_type`` columns (after
                ``standardized_dataframe``).
            **kwargs: Forwarded to ``standardized_dataframe`` and
                ``repository.upsert_records``. May include ``on_conflict_do`` to
                override ``self.on_conflict_do``. ``_db_session`` is removed before the
                repository call.

        Returns:
            The standardized mappings DataFrame that was written.

        Raises:
            RuntimeError: If the repository-reported upsert count falls below
                ``(1 - missing_upsertions_tol) * len(mappings)``.
        """
        mappings = self.dao_type.standardized_dataframe(df, **kwargs)
        kwargs.pop("_db_session", None)
        on_conflict_do = kwargs.pop("on_conflict_do", self.on_conflict_do)
        on_conflict_do = OnUpsertConflictDo(getattr(on_conflict_do, "value", on_conflict_do).upper())
        logger.info("Upserting %s records", len(mappings.index))
        upsertions = self.repository.upsert_records(
            dao_type=self.dao_type,
            mappings=mappings,
            db_session=self.db_session,
            on_conflict_do=on_conflict_do,
            **kwargs,
        )
        if upsertions < (len(mappings.index) * (1 - self.missing_upsertions_tol)):
            raise RuntimeError(
                "Not all records were correctly upserted and the mismatch has overpass the tolerance threshold of"
                f"{(self.missing_upsertions_tol * 100):2f}%"
            )

        return mappings

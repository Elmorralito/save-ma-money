"""Extended services for user-owned tables and declarative foreign-key relations.

Builds on ``BaseService`` with ownership-aware CRUD, safe batch upserts against
existing primary keys, and optional validation that dependent rows reference
real parent records via configured repositories.

Key components:
    ``_coerce_pk_value``: Normalizes primary-key-like values (e.g. string to UUID)
        for consistent ORM comparisons.
    ``OwnedTableService``: Scopes operations to a user owner and blocks upserts that
        would touch another user's rows.
    ``Relation``: Describes one FK edge (dependent column, parent DAO, repository,
        and parent column used in lookups).
    ``RelationLinkedService``: Enforces all configured ``Relation`` instances on
        create and optionally filters invalid rows before upsert.

Note:
    ``Relation.check_relation`` logs configuration or type mismatches and returns
    ``False`` rather than raising; callers that need strict errors should inspect
    the boolean result or use ``RelationLinkedService.check_relations``.
"""

import logging
import re
import uuid
from typing import Any, Dict, Literal, Self, Type

import pandas as pd
from pydantic import BaseModel, ValidationError, field_validator, model_validator
from sqlalchemy import and_, or_
from sqlalchemy.inspection import inspect as sqlalchemy_inspect
from sqlmodel import Session

from papita_txnsmodel.access.base import BaseRepository, OwnedTableRepository
from papita_txnsmodel.access.users import UsersRepository
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.model.base import BaseSQLModel
from papita_txnsmodel.model.users import Users
from papita_txnsmodel.services.base import BaseService

logger = logging.getLogger(__name__)


def _coerce_pk_value(value: object) -> object:
    """Return ``uuid.UUID(value)`` when parsable, otherwise the original ``value``.

    Used when building ``IN``/equality filters so string IDs match UUID columns.

    Args:
        value: Arbitrary object, often a string or UUID from a DataFrame cell.

    Returns:
        A ``uuid.UUID`` instance if ``str(value)`` is a valid UUID string, else
        ``value`` unchanged.
    """
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return value


class OwnedTableService(BaseService):
    """Service layer for DAOs scoped by ``owner_id`` (user-owned rows).

    Overrides CRUD and batch upsert so reads/writes respect the current owner,
    and so bulk upserts cannot update existing PKs that belong to another user.

    Attributes:
        repository_type: Repository class; defaults to ``OwnedTableRepository``.
        owner_repository_type: Repository used to resolve ``Users`` by id.
        owner: Current owner as ``Users``, UUID, or ``None`` until resolved.
        owner_id: Resolved owner UUID used for filters and upsert checks.
        owner_id_key: Model attribute name for the owner FK (default ``owner_id``).
        requires_mandatory_ownership: If True, operations that need an owner fail
            when none is set.
        owner_repository: Instance of ``owner_repository_type``; set by validation.
    """

    repository_type: Type[BaseRepository] = OwnedTableRepository
    owner_repository_type: Type[UsersRepository] = UsersRepository
    owner: Users | uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    owner_id_key: str = "owner_id"
    requires_mandatory_ownership: bool = True

    owner_repository: UsersRepository | None = None

    @model_validator(mode="after")
    def _normalize_model(self) -> Self:
        """Normalize the model after initialization."""
        super()._normalize_model()
        self.owner_repository = self.owner_repository_type()

        return self

    def check_owner(self, **kwargs) -> None:
        """Resolve and validate ``owner`` / ``owner_id`` against the users table.

        When ``owner`` is a ``Users`` instance, replaces it with that user's id,
        loads the row if needed, and sets ``owner_id``. No-op when neither owner
        field is set and mandatory ownership is disabled.

        Args:
            **kwargs: Reserved for compatibility with callers; unused here.

        Raises:
            ValueError: If mandatory ownership is required but no owner is set, or
                if the owner id does not exist in the database.
        """
        if not self.owner and self.requires_mandatory_ownership:
            raise ValueError("An owner or owner_id is required for this operation.")

        if not self.owner and not self.owner_id:
            return

        if self.owner:
            if isinstance(self.owner, Users):
                self.owner = self.owner.id

            owner = self.owner_repository.get_record_by_id(self.owner, dao_type=Users, db_session=self.db_session)
            self.owner_id = owner.id if isinstance(owner, Users) else None

        if isinstance(self.owner_id, uuid.UUID):
            return

        raise ValueError("The owner does not exist.")

    def set_owner(self, owner: Users | uuid.UUID) -> Self:
        """Assign owner and refresh ``owner_id``; returns ``self`` for chaining.

        Args:
            owner: User row or user primary key.

        Returns:
            This service instance.

        Raises:
            ValueError: Propagated from ``check_owner`` when the owner is invalid.
        """
        self.owner = owner
        self.check_owner()
        return self

    def manage_ownership(
        self,
        *,
        obj: BaseSQLModel | str | Dict[str, Any] | uuid.UUID,
        action: Literal["read", "update", "create", "delete"],
        **kwargs,
    ) -> BaseSQLModel:
        """Enforce owner consistency on a DAO instance for the given lifecycle action.

        Parses ``obj`` to the service DAO type, then applies rules so create/read/
        update/delete only proceed when ``owner_id`` matches the service owner
        (or is filled on create when appropriate).

        Args:
            obj: Incoming DAO instance or mapping.
            action: Which operation is about to run on ``obj``.
            **kwargs: Forwarded unused; kept for a uniform service signature.

        Returns:
            The parsed DAO, possibly with ``owner_id`` set on create.

        Raises:
            ValueError: If the record's owner does not match, or the action is not
                allowed for the current owner state.
        """
        self.check_owner()
        parsed_obj = self.parse_dto(obj)
        self.check_expected_dao_type(parsed_obj)
        match (
            action,
            parsed_obj.owner_id == self.owner_id,
            self.owner_id is not None,
            self.requires_mandatory_ownership,
        ):
            case (
                ("read", True, True, _)
                | ("read", True, False, False)
                | ("update", True, True, _)
                | ("update", True, False, False)
                | ("create", True, True, _)
                | ("create", True, False, False)
                | ("delete", True, True, _)
                | ("delete", True, False, False)
            ):
                output_obj = parsed_obj
            case ("create", False, True, _):
                parsed_obj.owner_id = self.owner_id
                output_obj = parsed_obj
            case (
                ("read", False, _, _) | ("update", False, _, _) | ("create", False, False, _) | ("delete", False, _, _)
            ):
                raise ValueError("The provided owner does not match the expected owner.")
            case _:
                raise ValueError("Invalid action.")

        return output_obj

    def create(self, *, obj: BaseSQLModel | Dict[str, Any], **kwargs) -> BaseSQLModel:
        """Create a row after applying ownership rules for the create action."""
        input_obj = self.manage_ownership(obj=obj, action="create", **kwargs)
        return super().create(obj=input_obj, **kwargs)

    def delete(self, *, obj: BaseSQLModel | Dict[str, Any], **kwargs) -> pd.DataFrame:
        """Soft-delete (or delegate) after ownership checks for delete."""
        input_obj = self.manage_ownership(obj=obj, action="delete", **kwargs)
        return super().delete(obj=input_obj, **kwargs)

    def get(self, *, obj: BaseSQLModel | str | Dict[str, Any] | uuid.UUID, **kwargs) -> BaseSQLModel | None:
        """Load one row after ownership checks for read."""
        input_obj = self.manage_ownership(obj=obj, action="read", **kwargs)
        return super().get(obj=input_obj, **kwargs)

    def get_or_create(self, *, obj: BaseSQLModel | str | Dict[str, Any] | uuid.UUID, **kwargs) -> BaseSQLModel:
        """Get or insert using ownership rules appropriate for create."""
        input_obj = self.manage_ownership(obj=obj, action="create", **kwargs)
        return super().get_or_create(obj=input_obj, **kwargs)

    def get_records(self, *, obj: BaseSQLModel | Dict[str, Any] | None, **kwargs) -> pd.DataFrame:
        """Query rows with ownership-scoped filters."""
        if obj is None:
            return super().get_records(obj=None, **kwargs)

        input_dto = self.manage_ownership(obj=obj, action="read", **kwargs)
        return super().get_records(obj=input_dto, **kwargs)

    def _assert_upsert_updates_owned(self, mappings: pd.DataFrame) -> None:
        """Ensure rows that target existing PKs are owned by the current owner.

        Uses ``BaseRepository.get_records`` so existing rows are visible regardless of
        owner filter on ``OwnedTableRepository``.
        """
        if getattr(mappings, "empty", True) or not hasattr(self.dao_type, self.owner_id_key):
            return
        if self.owner_id is None:
            return

        pk_names = [c.key for c in sqlalchemy_inspect(self.dao_type).primary_key]
        if not pk_names or not set(pk_names).issubset(mappings.columns):
            return

        if len(pk_names) == 1:
            n0 = pk_names[0]
            pk_present = mappings[n0].notna() & mappings[n0].astype(str).str.strip().ne("")
        else:
            pk_present = pd.concat(
                [mappings[n].notna() & mappings[n].astype(str).str.strip().ne("") for n in pk_names],
                axis=1,
            ).all(axis=1)
        subset = mappings.loc[pk_present, pk_names].drop_duplicates()
        if subset.empty:
            return

        dao = self.dao_type
        if len(pk_names) == 1:
            col = pk_names[0]
            query_filter = getattr(dao, col).in_(subset[col].map(_coerce_pk_value).tolist())
        else:
            clauses = [
                and_(*[getattr(dao, n) == _coerce_pk_value(v) for n, v in zip(pk_names, tup)])
                for tup in subset.itertuples(index=False, name=None)
            ]
            query_filter = or_(*clauses) if len(clauses) > 1 else clauses[0]

        existing = self.repository.get_records(
            self.repository,
            query_filter,
            dao_type=self.dao_type,
            db_session=self.db_session,
        )
        if getattr(existing, "empty", True):
            return

        owner_key = self.owner_id_key
        logger.debug(
            "Upsert batch includes %s existing row(s); verifying %s.",
            len(existing.index),
            owner_key,
        )
        if owner_key not in existing.columns:
            raise RuntimeError(f"Cannot verify ownership: existing rows have no {owner_key!r} column.")

        expected = uuid.UUID(str(self.owner_id))
        if not existing[owner_key].map(lambda r: uuid.UUID(str(r))).eq(expected).all():
            raise ValueError("Cannot upsert: the batch targets existing record(s) not owned by the current owner.")

    def upsert_records(self, *, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Standardize ``df``, verify ownership on PK collisions, then upsert.

        Commits via the repository; raises if the number of affected rows falls
        below ``missing_upsertions_tol`` relative to the batch size.

        Args:
            df: Raw rows to upsert.
            **kwargs: Passed to ``standardized_dataframe``, the repository upsert,
                and conflict handling (e.g. ``on_conflict_do``, ``owner``). Internal
                ``_db_session`` is stripped before the repository call.

        Returns:
            The standardized ``DataFrame`` that was sent to the repository.

        Raises:
            ValueError: From ``check_owner`` or ownership verification on existing
                PKs targeted by the batch.
            RuntimeError: If upsert count is below the configured tolerance.
        """
        self.check_owner()
        mappings = self.dao_type.standardized_dataframe(df, **kwargs)
        kwargs.pop("_db_session", None)
        self._assert_upsert_updates_owned(mappings)
        on_conflict_do = kwargs.pop("on_conflict_do", self.on_conflict_do)
        on_conflict_do = OnUpsertConflictDo(getattr(on_conflict_do, "value", on_conflict_do).upper())
        logger.info("Upserting %s records", len(mappings.index))
        if kwargs.get("owner") is None:
            owner_ref = self.owner_id if self.owner_id is not None else self.owner
            kwargs["owner"] = owner_ref
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


class Relation(BaseModel):
    """Declarative FK check: dependent column must reference an existing parent row.

    Maps a column on ``dependent_dao_type`` to a column on ``dependency_dao_type``
    and uses ``dependency_repository`` to confirm the parent exists. Column names
    are sanitized to alphanumeric plus underscore.

    Attributes:
        dependency_relation_column: Parent column used in the lookup (often ``id``).
        dependent_column: Dependent-side column holding the FK value.
        dependency_repository_type: Class used to instantiate ``dependency_repository``.
        dependency_repository: Live repository; created during model validation.
        dependency_dao_type: SQLModel class for the parent table.
        dependent_dao_type: SQLModel class for the dependent row being validated.
    """

    dependency_relation_column: str
    dependent_column: str
    dependency_repository_type: Type[BaseRepository] = BaseRepository
    dependency_repository: BaseRepository | None = None
    dependency_dao_type: Type[BaseSQLModel] = BaseSQLModel
    dependent_dao_type: Type[BaseSQLModel] = BaseSQLModel

    @field_validator("dependency_relation_column", "dependent_column", mode="before")
    @classmethod
    def _validate_string_fields(cls, value: str) -> str:
        """Validate and sanitize string fields."""
        value = re.sub(r"[^A-Za-z0-9_]*", "", value)
        if not value:
            raise ValueError("The string field must not be empty")

        return value

    @model_validator(mode="after")
    def _normalize_model(self) -> Self:
        """Normalize the model after initialization."""
        self.dependency_repository = self.dependency_repository_type()
        return self

    def check_relation(self, *, db_session: Session, dependent_obj: BaseSQLModel, **kwargs) -> bool:
        """Return whether the dependent's FK points at an existing parent row.

        Inspects ORM nullability on ``dependent_column``; requires a non-empty FK
        value, then queries ``dependency_repository`` for a row where
        ``dependency_relation_column`` equals the coerced FK.

        Args:
            db_session: Active SQLModel session for reads.
            dependent_obj: Instance of ``dependent_dao_type`` (or subclass) to inspect.
            **kwargs: Forwarded to ``dependency_repository.get_records`` (e.g. owner
                filters for ``OwnedTableRepository``).

        Returns:
            ``True`` if the FK is set and a matching parent row exists; ``False``
            if the type is wrong, configuration is invalid, FK is missing, or no
            parent row was found.

        Note:
            Warnings are logged for type mismatches, missing columns, or an
            uninitialized repository instead of raising.
        """
        if not isinstance(dependent_obj, self.dependent_dao_type):
            logger.warning("The dependent object is not of the expected type")
            return False

        dependent_mapper = sqlalchemy_inspect(self.dependent_dao_type)
        if self.dependent_column not in dependent_mapper.columns:
            logger.warning(
                "The dependent DAO type %s has no column %s", self.dependent_dao_type.__name__, self.dependent_column
            )
            return False

        dependent_col = dependent_mapper.columns[self.dependent_column]
        fk_value = getattr(dependent_obj, self.dependent_column, None)

        if not dependent_col.nullable and fk_value is None:
            return False

        if fk_value and isinstance(fk_value, str) and not fk_value.strip():
            return False

        dependency_mapper = sqlalchemy_inspect(self.dependency_dao_type)
        if self.dependency_relation_column not in dependency_mapper.columns:
            logger.warning(
                "The dependency DAO type %s has no column %s",
                self.dependency_dao_type.__name__,
                self.dependency_relation_column,
            )
            return False

        fk_lookup = _coerce_pk_value(fk_value)
        dep_col_attr = getattr(self.dependency_dao_type, self.dependency_relation_column)
        records = self.dependency_repository.get_records(
            dep_col_attr == fk_lookup,
            dao_type=self.dependency_dao_type,
            db_session=db_session,
            **kwargs,
        )

        return not getattr(records, "empty", True)


class RelationLinkedService(OwnedTableService):
    """Owned-table service that validates named ``Relation`` graphs before writes.

    Ensures every configured relation passes ``Relation.check_relation`` for a
    single DAO instance, and can filter bulk upserts row-wise when relations or
    row validation fail.

    Attributes:
        relations: Map of relation label to ``Relation`` definition; each entry is
            enforced by ``check_relations``.
    """

    relations: Dict[str, Relation]

    def check_relations(self, *, obj: BaseSQLModel | str | Dict[str, Any] | uuid.UUID, **kwargs) -> Self:
        """Run all ``relations`` checks against ``obj`` using ``self.db_session``.

        Args:
            obj: Dependent DAO instance passed to each ``Relation.check_relation``.
                Should match ``dao_type`` expectations; dict inputs are not
                coerced here.
            **kwargs: Forwarded to each ``check_relation`` (e.g. repository owner).

        Returns:
            ``self`` when every relation resolves.

        Raises:
            ValueError: If any relation returns ``False`` (invalid or missing FK
                target).
        """
        parsed_obj = self.parse_dto(obj)
        self.check_expected_dao_type(parsed_obj)
        valid_relations = {
            relation_name: relation.check_relation(db_session=self.db_session, dependent_obj=parsed_obj, **kwargs)
            for relation_name, relation in self.relations.items()
        }
        invalid_relations = {relation_name for relation_name, relation in valid_relations.items() if not relation}
        if invalid_relations:
            raise ValueError(f"The relations {invalid_relations} are not valid.")

        return self

    def create(self, *, obj: BaseSQLModel | Dict[str, Any], **kwargs) -> BaseSQLModel:
        """Create after ``check_relations`` succeeds for ``obj``."""
        self.check_relations(obj=obj, **kwargs)
        return super().create(obj=obj, **kwargs)

    def _row_relations_ok(
        self, row: pd.Series, *, on_invalid_relation: Literal["raise", "skip"], **kwargs: Any
    ) -> bool:
        """Validate one standardized row and run ``check_relations``; return success flag.

        Used by ``upsert_records`` with ``DataFrame.apply``; respects
        ``on_invalid_relation`` for ``ValidationError`` and relation errors.

        Args:
            row: Single row of the standardized upsert frame (index is the row
                label used in warning messages).
            on_invalid_relation: ``raise`` to propagate errors; ``skip`` to log and
                return ``False``.
            **kwargs: Forwarded to ``check_relations``.

        Returns:
            ``True`` if the row model validates and all relations pass.

        Raises:
            ValidationError: When ``on_invalid_relation`` is ``raise`` and the row
                does not match ``dao_type``.
            ValueError: When ``on_invalid_relation`` is ``raise`` and
                ``check_relations`` fails.
        """
        try:
            obj = self.dao_type.model_validate(row.to_dict())
        except ValidationError as exc:
            if on_invalid_relation == "raise":
                raise
            logger.warning("Skipping row %s due to invalid model data: %s", row.name, exc)
            return False
        try:
            self.check_relations(obj=obj, **kwargs)
        except ValueError as exc:
            if on_invalid_relation == "raise":
                raise
            logger.warning("Skipping row %s due to invalid relations: %s", row.name, exc)
            return False
        return True

    def upsert_records(
        self,
        *,
        df: pd.DataFrame,
        on_invalid_relation: Literal["raise", "skip"] = "raise",
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Standardize ``df``, validate relations per row, then delegate to the base upsert.

        Row validation uses ``dao_type.model_validate`` and ``check_relations``.
        With ``on_invalid_relation="skip"``, failing rows are removed and warnings
        are logged; with ``"raise"``, the first invalid row stops the call.

        Args:
            df: Incoming batch before DAO-specific standardization.
            on_invalid_relation: ``raise`` aborts on first bad row; ``skip`` drops
                bad rows and upserts the remainder.
            **kwargs: Passed to ``standardized_dataframe``, row validation, relation
                checks, and ``OwnedTableService.upsert_records``.

        Returns:
            The standardized ``DataFrame`` actually upserted (possibly a subset when
            skipping).

        Raises:
            ValidationError: When ``on_invalid_relation`` is ``raise`` and a row
                fails Pydantic validation.
            ValueError: When ``on_invalid_relation`` is ``raise`` and relations
                fail for a row.
            ValueError, RuntimeError: From the parent ``upsert_records`` (owner,
                ownership collision, upsert tolerance).
        """
        standardized_df = self.dao_type.standardized_dataframe(df, **kwargs)
        mask = standardized_df.apply(
            lambda r: self._row_relations_ok(r, on_invalid_relation=on_invalid_relation, **kwargs),
            axis=1,
        )
        if on_invalid_relation == "skip":
            standardized_df = standardized_df.loc[mask].copy()

        return super().upsert_records(df=standardized_df, **kwargs)

"""Transactions service module for the Papita Transactions system.

This module provides services for managing transaction entities in the system, including
transaction templates (recurring/planned) and posted transactions. It implements the
necessary functionality to handle relationships between transactions, accounts, and categories.

Classes:
    TransactionTemplatesService: Service for managing transaction template entities.
    TransactionsService: Service for managing posted transaction entities.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from datetime import date, datetime, time, timezone
from typing import Annotated, Any, Dict, Literal, Self

import pandas as pd
from pydantic import Field, model_validator

from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.access.categories.dto import CategoriesDTO
from papita_txnsmodel.access.transactions.dto import TransactionsDTO, TransactionTemplatesDTO
from papita_txnsmodel.access.transactions.query_filters import TransactionListFilterSpec, build_transaction_list_filters
from papita_txnsmodel.access.transactions.repository import TransactionsRepository, TransactionTemplatesRepository
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.model.enums import CategoryKind, TransactionKind, TransactionStatus
from papita_txnsmodel.model.transactions import Transactions
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.balance_views import refresh_balance_materialized_views
from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.services.categories import CategoriesService
from papita_txnsmodel.services.dues import (
    UpcomingDueDTO,
    period_bounds,
    period_key,
    remind_start_for,
    resolve_due_date,
    select_upcoming_due,
)
from papita_txnsmodel.utils.datautils import mapping_without_missing

logger = logging.getLogger(__name__)


def _as_uuid(value: uuid.UUID | TableDTO | None) -> uuid.UUID | None:
    """Return a relation field as UUID when present."""
    if value is None:
        return None
    if isinstance(value, TableDTO):
        if value.id is None:
            raise ValueError("Related DTO must include an id.")
        return value.id
    return value


class TransactionTemplatesService(BaseService):
    """Service for managing transaction template entities in the Papita Transactions system.

    Attributes:
        category_id_column_name (str): Name of the column storing the category ID.
        category_id_field_name (str): Name of the field storing the category.
        dto_type (type[TransactionTemplatesDTO]): DTO type for transaction templates.
        repository_type (type[TransactionTemplatesRepository]): Repository for templates.
        categories_dto_type (type[CategoriesDTO]): DTO type for categories.
        transactions_service (TransactionsService): Posted-ledger writes for mark-paid.
        accounts_service (AccountsService): Owner-scoped account validation.
    """

    categories_service: CategoriesService | None = None
    category_id_column_name: str = "category_id"
    category_id_field_name: str = "category_id"
    dto_type: type[TransactionTemplatesDTO] = TransactionTemplatesDTO
    repository_type: type[TransactionTemplatesRepository] = TransactionTemplatesRepository
    categories_dto_type: type[CategoriesDTO] = CategoriesDTO
    transactions_service: Any | None = None
    accounts_service: AccountsService | None = None
    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.UPDATE

    @model_validator(mode="after")
    def _wire_dues_dependencies(self) -> Self:
        """Instantiate ledger/account/category services from the shared connector when omitted."""
        if not isinstance(self.categories_service, CategoriesService):
            self.categories_service = CategoriesService.model_validate({"connector": self.connector})
        if self.accounts_service is None:
            self.accounts_service = AccountsService.model_validate({"connector": self.connector})
        if self.transactions_service is None:
            txn_service = TransactionsService.model_validate({"connector": self.connector})
            txn_service.load_link_services(
                {
                    "template_id": self,
                    "from_account_id": self.accounts_service,
                    "to_account_id": self.accounts_service,
                    "category_id": self.categories_service,
                }
            )
            self.transactions_service = txn_service
        return self

    def create(self, *, obj: TableDTO | dict[str, Any], owner: UsersDTO | None = None, **kwargs) -> TableDTO:
        """Create a transaction template after validating its category reference."""
        raw_cat = obj.get(self.category_id_field_name) if isinstance(obj, dict) else getattr(obj, self.category_id_field_name, None)
        category_dto = self.categories_service.get_or_create(obj=raw_cat, owner=owner, **kwargs)
        dto = super().create(obj=obj, owner=owner, **kwargs)
        setattr(dto, self.category_id_field_name, category_dto)
        return dto

    def get(
        self, *, obj: TableDTO | str | dict | uuid.UUID, owner: UsersDTO | None = None, **kwargs
    ) -> TableDTO | None:
        """Retrieve a transaction template and optionally hydrate its category."""
        categorized_dto = super().get(obj=obj, owner=owner, **kwargs)
        if kwargs.get("include_category", True) and isinstance(categorized_dto, self.dto_type):
            category_kwargs = {key: value for key, value in kwargs.items() if key != "dto_type"}
            categorized_dto = self.dto_type.model_validate(
                categorized_dto.model_dump(mode="python")
                | {
                    self.category_id_field_name: self.categories_service.get(
                        obj=getattr(categorized_dto, self.category_id_field_name),
                        owner=owner,
                        dto_type=self.categories_dto_type,
                        **category_kwargs,
                    )
                }
            )
        return categorized_dto

    def _templates_from_frame(self, frame: pd.DataFrame) -> list[TransactionTemplatesDTO]:
        """Parse an owner-scoped templates DataFrame into DTOs."""
        if getattr(frame, "empty", True):
            return []
        return [self.dto_type.model_validate(mapping_without_missing(row)) for row in frame.to_dict(orient="records")]

    @staticmethod
    def _txn_sort_key(item: TransactionsDTO) -> tuple[datetime, str]:
        """Sort key for latest-posting selection (timestamp, then id)."""
        ts = item.transaction_ts or datetime.min.replace(tzinfo=timezone.utc)
        return (ts, str(item.id))

    def _require_owner(self, owner: UsersDTO | None) -> UsersDTO:
        """Require a tenant owner and narrow the type for mypy."""
        ensured = self._ensure_owner(owner)
        if ensured is None:
            raise ValueError("UsersDTO owner is required for tenant-scoped dues operations.")
        return ensured

    def _latest_paid_in_frame(
        self,
        frame: pd.DataFrame,
        wanted: set[uuid.UUID],
    ) -> dict[uuid.UUID, TransactionsDTO]:
        """Pick the latest active posting per template id from a period frame."""
        latest_for_template: dict[uuid.UUID, TransactionsDTO] = {}
        for row in frame.to_dict(orient="records"):
            txn = TransactionsDTO.model_validate(row)
            linked_template_id = _as_uuid(txn.template_id)
            if linked_template_id is None or linked_template_id not in wanted:
                continue
            if not getattr(txn, "active", True):
                continue
            current = latest_for_template.get(linked_template_id)
            if current is None or self._txn_sort_key(txn) > self._txn_sort_key(current):
                latest_for_template[linked_template_id] = txn
        return latest_for_template

    def _paid_postings_by_template(
        self,
        *,
        owner: UsersDTO,
        dues_by_template: dict[uuid.UUID, date],
        **kwargs: Any,
    ) -> dict[uuid.UUID, TransactionsDTO]:
        """Return latest active linked posting per template for each due's month.

        Batches by calendar month so ``list_upcoming_dues`` issues one frame read
        per distinct period instead of one read per template.

        Args:
            owner: Tenant owner.
            dues_by_template: Map of template id → resolved due date.
            **kwargs: Passed to ``get_transactions_frame``.

        Returns:
            Map of template id → latest matching ``TransactionsDTO`` when paid.
        """
        if not dues_by_template:
            return {}

        by_period: dict[tuple[int, int], list[tuple[uuid.UUID, date]]] = {}
        for template_id, due in dues_by_template.items():
            by_period.setdefault(period_key(due), []).append((template_id, due))

        paid_by_template: dict[uuid.UUID, TransactionsDTO] = {}
        for items in by_period.values():
            period_start, period_end = period_bounds(items[0][1])
            frame = self.transactions_service.get_transactions_frame(
                owner=owner,
                start_date=period_start,
                end_date=period_end,
                exclude_transfer=False,
                **kwargs,
            )
            if getattr(frame, "empty", True):
                continue
            wanted = {template_id for template_id, _due in items}
            paid_by_template.update(self._latest_paid_in_frame(frame, wanted))

        return paid_by_template

    def _paid_posting_for_period(
        self,
        *,
        template_id: uuid.UUID,
        owner: UsersDTO,
        due: date,
        **kwargs: Any,
    ) -> TransactionsDTO | None:
        """Return the latest active linked posting for ``template_id`` in ``due``'s month."""
        paid = self._paid_postings_by_template(
            owner=owner,
            dues_by_template={template_id: due},
            **kwargs,
        )
        return paid.get(template_id)

    def list_upcoming_dues(
        self,
        *,
        owner: UsersDTO,
        as_of: date,
        window_days: int = 14,
        include_paid: bool = True,
        **kwargs: Any,
    ) -> list[UpcomingDueDTO]:
        """List owner-scoped templates with a due in the upcoming reminder window.

        Paid state is derived from active posted transactions linked via
        ``template_id`` within the resolved due's calendar month. Paid lookups are
        batched by calendar month.

        Args:
            owner: Tenant owner (required).
            as_of: Window anchor date.
            window_days: Inclusive days after ``as_of`` to consider.
            include_paid: When False, omit dues that already have a linked posting.
            **kwargs: Passed through to repository/service reads.

        Returns:
            Upcoming dues sorted by resolved due date, then template name/id.
        """
        owner = self._require_owner(owner)
        if window_days < 0:
            raise ValueError("window_days must be >= 0")

        templates = self._templates_from_frame(
            self.get_records(dto=None, owner=owner, include_category=False, **kwargs)
        )
        dues_by_template: dict[uuid.UUID, date] = {}
        selected: list[tuple[TransactionTemplatesDTO, date]] = []
        for template in templates:
            if template.id is None:
                continue
            due = select_upcoming_due(template, as_of=as_of, window_days=window_days)
            if due is None:
                continue
            selected.append((template, due))
            dues_by_template[template.id] = due

        paid_by_template = self._paid_postings_by_template(
            owner=owner,
            dues_by_template=dues_by_template,
            **kwargs,
        )

        results: list[UpcomingDueDTO] = []
        for template, due in selected:
            assert template.id is not None
            paid = paid_by_template.get(template.id)
            is_paid = paid is not None
            if is_paid and not include_paid:
                continue
            results.append(
                UpcomingDueDTO(
                    template=template,
                    due_date=due,
                    remind_start=remind_start_for(due, template.remind_days_before),
                    is_paid=is_paid,
                    paid_transaction_id=paid.id if paid is not None else None,
                )
            )

        results.sort(key=lambda item: (item.due_date, item.template.name or "", str(item.template.id)))
        return results

    def mark_paid(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        *,
        template_id: uuid.UUID,
        owner: UsersDTO,
        as_of: date | None = None,
        transaction_ts: datetime | None = None,
        amount: float | None = None,
        **kwargs: Any,
    ) -> TransactionsDTO:
        """Post a linked EXPENSE/INCOME for a template due (mark paid).

        Kind follows the template category. The optional template ``from_account_id``
        is the pay-from account for EXPENSE and the deposit account (``to_account_id``)
        for INCOME. Currency defaults to USD.

        Args:
            template_id: Template to mark paid.
            owner: Tenant owner (required).
            as_of: Anchor for resolving the recurring occurrence (default: UTC today).
            transaction_ts: Posted timestamp (default: noon UTC on the resolved due).
            amount: Posted amount (default: ``planned_amount``).
            **kwargs: Passed to create/get paths (e.g. ``refresh_balances``).

        Returns:
            Created ``TransactionsDTO`` with ``template_id`` set.

        Raises:
            ValueError: Missing template, already paid, missing account, or bad category.
        """
        owner = self._require_owner(owner)

        template = self.get(obj=template_id, owner=owner, include_category=False, **kwargs)
        if not isinstance(template, TransactionTemplatesDTO) or template.id is None:
            raise ValueError("Transaction template not found.")

        # Period is the occurrence in ``as_of``'s month (or the one-off due_date).
        anchor = as_of or datetime.now(timezone.utc).date()
        due = resolve_due_date(template, ref=anchor)

        existing = self._paid_posting_for_period(template_id=template.id, owner=owner, due=due, **kwargs)
        if existing is not None:
            raise ValueError("Template due is already marked paid for this period.")

        category_id = _as_uuid(template.category_id)
        if category_id is None:
            raise ValueError("Template category_id is required for mark_paid.")
        category = self.categories_service.get(obj=category_id, owner=owner, **kwargs)
        if not isinstance(category, CategoriesDTO):
            raise ValueError("Template category not found.")

        account_id = _as_uuid(template.from_account_id)
        if account_id is None:
            raise ValueError("Template from_account_id is required for mark_paid.")
        account = self.accounts_service.get(obj=account_id, owner=owner, **kwargs)
        if account is None:
            raise ValueError("Pay account not found for owner.")

        if category.category_kind == CategoryKind.EXPENSE:
            kind = TransactionKind.EXPENSE
            from_account_id: uuid.UUID | None = account_id
            to_account_id: uuid.UUID | None = None
        elif category.category_kind == CategoryKind.INCOME:
            kind = TransactionKind.INCOME
            from_account_id = None
            to_account_id = account_id
        else:  # pragma: no cover - CategoryKind is currently INCOME|EXPENSE only
            raise ValueError(f"Unsupported category kind for mark_paid: {category.category_kind!r}")

        posted_amount = float(template.planned_amount if amount is None else amount)
        if posted_amount <= 0:
            raise ValueError("mark_paid amount must be positive.")

        posted_ts = transaction_ts or datetime.combine(due, time(hour=12), tzinfo=timezone.utc)
        payload = TransactionsDTO(
            owner_id=owner.id,
            transaction_kind=kind,
            amount=posted_amount,
            currency="USD",
            transaction_ts=posted_ts,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            category_id=category_id,
            template_id=template.id,
            status=TransactionStatus.COMPLETED,
            description=template.description or template.name or "",
            tags=list(template.tags or []),
        )
        # Avoid CategorizedEntitiesService category hydration on the template link
        # (passes dto_type= into CategoriesService.get and can collide with kwargs).
        created = self.transactions_service.create(
            obj=payload,
            owner=owner,
            include_category=False,
            **kwargs,
        )
        if not isinstance(created, TransactionsDTO):
            raise RuntimeError("mark_paid failed to create a transaction.")
        return created

    def clear_paid(
        self,
        *,
        template_id: uuid.UUID,
        owner: UsersDTO,
        as_of: date | None = None,
        **kwargs: Any,
    ) -> TransactionsDTO:
        """Soft-delete the latest active linked posting for the due period.

        Args:
            template_id: Template whose paid posting should be cleared.
            owner: Tenant owner (required).
            as_of: Anchor for resolving the recurring occurrence (default: UTC today).
            **kwargs: Passed to get/delete paths.

        Returns:
            The posting DTO that was soft-deleted.

        Raises:
            ValueError: Missing template or no paid posting for the period.
        """
        owner = self._require_owner(owner)

        template = self.get(obj=template_id, owner=owner, include_category=False, **kwargs)
        if not isinstance(template, TransactionTemplatesDTO) or template.id is None:
            raise ValueError("Transaction template not found.")

        anchor = as_of or datetime.now(timezone.utc).date()
        due = resolve_due_date(template, ref=anchor)

        paid = self._paid_posting_for_period(template_id=template.id, owner=owner, due=due, **kwargs)
        if paid is None or paid.id is None:
            raise ValueError("Template due is not marked paid for this period.")

        self.transactions_service.delete(obj=paid, owner=owner, hard=False, **kwargs)
        return paid


# Backward-compatible alias for legacy callers.
IdentifiedTransactionsService = TransactionTemplatesService


class TransactionsService(BaseService):
    """Service for managing posted transaction entities in the Papita Transactions system."""

    dto_type: type[TransactionsDTO] = TransactionsDTO
    repository_type: type[TransactionsRepository] = TransactionsRepository
    accounts_service: AccountsService | None = None
    categories_service: CategoriesService | None = None
    templates_service: TransactionTemplatesService | None = None

    missing_upsertions_tol: Annotated[float, Field(ge=0, le=0.5)] = 0.0
    on_conflict_do: OnUpsertConflictDo | str = OnUpsertConflictDo.UPDATE

    def load_link_services(
        self, links: Dict[str, BaseService], reload: bool = True, **kwargs
    ) -> "TransactionsService":
        """Bind collaborator services used to validate/resolve FK references."""
        del kwargs
        if "from_account_id" in links and (self.accounts_service is None or reload):
            self.accounts_service = links["from_account_id"]  # type: ignore[assignment]
        elif "to_account_id" in links and (self.accounts_service is None or reload):
            self.accounts_service = links["to_account_id"]  # type: ignore[assignment]
        if "category_id" in links and (self.categories_service is None or reload):
            self.categories_service = links["category_id"]  # type: ignore[assignment]
        if "template_id" in links and (self.templates_service is None or reload):
            self.templates_service = links["template_id"]  # type: ignore[assignment]
        return self

    def _link_service_for_field(self, field_name: str) -> BaseService | None:
        if field_name in ("from_account_id", "to_account_id"):
            return self.accounts_service
        if field_name == "category_id":
            return self.categories_service
        if field_name == "template_id":
            return self.templates_service
        return None

    def _maybe_refresh_balances(self, **kwargs) -> None:
        """Refresh balance materialized views when ``refresh_balances=True``."""
        if not kwargs.get("refresh_balances", False):
            return
        try:
            refresh_balance_materialized_views(
                self.connector,
                concurrently=kwargs.get("refresh_balances_concurrently", False),
            )
        except Exception:
            logger.exception("Failed to refresh balance materialized views after transaction write.")

    def refresh_balance_views(self, *, concurrently: bool = False) -> None:
        """Explicitly refresh account/owner balance materialized views."""
        self._maybe_refresh_balances(refresh_balances=True, refresh_balances_concurrently=concurrently)

    def create(
        self, *, obj: TransactionsDTO | dict[str, Any], owner: UsersDTO | None = None, **kwargs
    ) -> TransactionsDTO:
        """Create a transaction after validating any non-null FK references."""
        linked_dto_cache = kwargs.pop("linked_dto_cache", None)
        linked_dtos: dict[str, Any] = {}
        for field_name in ("template_id", "from_account_id", "to_account_id", "category_id"):
            field_value = obj.get(field_name) if isinstance(obj, dict) else getattr(obj, field_name, None)
            if field_value is None:
                continue

            linked_service = self._link_service_for_field(field_name)
            if not isinstance(linked_service, BaseService):
                raise TypeError(f"Service of the linked entity in field {field_name} has not been loaded.")

            cache_key = None
            if isinstance(linked_dto_cache, dict):
                key_id = field_value if isinstance(field_value, uuid.UUID) else getattr(field_value, "id", None)
                if isinstance(key_id, uuid.UUID):
                    cache_key = (field_name, key_id)
                    cached = linked_dto_cache.get(cache_key)
                    if cached is not None:
                        linked_dtos[field_name] = cached
                        continue

            linked_dto = linked_service.get_or_create(obj=field_value, owner=owner, **kwargs)
            linked_dtos[field_name] = linked_dto
            if cache_key is not None:
                linked_dto_cache[cache_key] = linked_dto

        result = super().create(obj=obj, owner=owner, **kwargs)
        for field_name, linked_dto in linked_dtos.items():
            setattr(result, field_name, linked_dto)
        self._maybe_refresh_balances(**kwargs)
        return result

    def get(
        self, *, obj: TableDTO | str | dict | uuid.UUID, owner: UsersDTO | None = None, **kwargs
    ) -> TransactionsDTO | None:
        """Retrieve a transaction and optionally hydrate linked FK DTOs."""
        dto = super().get(obj=obj, owner=owner, **kwargs)
        if kwargs.get("include_linked_dtos", True) and isinstance(dto, self.dto_type):
            linked_dtos: dict[str, Any] = {}
            for field_name in ("template_id", "from_account_id", "to_account_id", "category_id"):
                linked_service = self._link_service_for_field(field_name)
                if not isinstance(linked_service, BaseService):
                    continue
                field_value = getattr(dto, field_name, None)
                if field_value is None:
                    continue
                resolved = linked_service.get(obj=field_value, owner=owner, **kwargs)
                linked_dtos[field_name] = field_value if resolved is None else resolved
            if linked_dtos:
                dto = self.dto_type.model_validate(dto.model_dump(mode="python") | linked_dtos)
        return dto  # type: ignore[return-value]

    def delete(
        self, *, obj: TransactionsDTO | dict[str, Any], owner: UsersDTO | None = None, hard: bool = False, **kwargs
    ) -> pd.DataFrame:
        """Delete a transaction; MV refresh is opt-in via ``refresh_balances=True``."""
        result = super().delete(obj=obj, owner=owner, hard=hard, **kwargs)
        self._maybe_refresh_balances(**kwargs)
        return result

    def upsert_records(self, *, df: pd.DataFrame, owner: UsersDTO | None = None, **kwargs) -> pd.DataFrame:
        """Upsert transactions; MV refresh is opt-in via ``refresh_balances=True``."""
        mappings = super().upsert_records(df=df, owner=owner, **kwargs)
        self._maybe_refresh_balances(**kwargs)
        return mappings

    def list_transactions(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        *,
        owner: UsersDTO,
        account_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        transaction_kind: TransactionKind | None = None,
        exclude_transfer: bool = True,
        status: TransactionStatus | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
        **kwargs,
    ) -> tuple[pd.DataFrame, int]:
        """List posted transactions for a tenant using SQLModel WHERE filters."""
        query_filters = build_transaction_list_filters(
            TransactionListFilterSpec(
                transaction_kind=transaction_kind,
                exclude_transfer=exclude_transfer,
                status=status,
                account_id=account_id,
                category_id=category_id,
                start_date=start_date,
                end_date=end_date,
                min_amount=min_amount,
                max_amount=max_amount,
                search=search,
            )
        )
        order_by = (Transactions.transaction_ts.desc(), Transactions.id.desc())
        return self._repository.get_page_with_total(
            *query_filters,
            dto_type=self.dto_type,
            owner=owner,
            skip=skip,
            limit=limit,
            order_by=order_by,
            **kwargs,
        )

    def get_transactions_frame(  # pylint: disable=too-many-arguments
        self,
        *,
        owner: UsersDTO,
        account_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        transaction_kind: TransactionKind | None = None,
        exclude_transfer: bool = False,
        status: TransactionStatus | None = None,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Load matching tenant transactions without list pagination (report paths).

        Unlike ``list_transactions``, this applies SQL filters only and returns the
        full matching frame so analytics can aggregate without N+1 page loops.
        """
        query_filters = build_transaction_list_filters(
            TransactionListFilterSpec(
                transaction_kind=transaction_kind,
                exclude_transfer=exclude_transfer,
                status=status,
                account_id=account_id,
                category_id=category_id,
                start_date=start_date,
                end_date=end_date,
            )
        )
        return self._repository.get_records(
            *query_filters,
            dto_type=self.dto_type,
            owner=owner,
            **kwargs,
        )

    def list_transfers(  # pylint: disable=too-many-arguments
        self,
        *,
        owner: UsersDTO,
        source_account_id: uuid.UUID | None = None,
        destination_account_id: uuid.UUID | None = None,
        status: TransactionStatus | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        skip: int = 0,
        limit: int = 100,
        **kwargs,
    ) -> tuple[pd.DataFrame, int]:
        """List transfer transactions for a tenant owner."""
        query_filters = build_transaction_list_filters(
            TransactionListFilterSpec(
                transaction_kind=TransactionKind.TRANSFER,
                exclude_transfer=False,
                status=status,
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                start_date=start_date,
                end_date=end_date,
            )
        )
        order_by = (Transactions.transaction_ts.desc(), Transactions.id.desc())
        return self._repository.get_page_with_total(
            *query_filters,
            dto_type=self.dto_type,
            owner=owner,
            skip=skip,
            limit=limit,
            order_by=order_by,
            **kwargs,
        )

    def create_transfer(
        self,
        *,
        obj: TransactionsDTO | dict[str, Any],
        owner: UsersDTO | None = None,
        **kwargs,
    ) -> TransactionsDTO:
        """Create a transfer transaction with both account legs enforced."""
        transfer = self.parse_dto(obj)
        transfer.transaction_kind = TransactionKind.TRANSFER
        if transfer.from_account_id is None or transfer.to_account_id is None:
            raise ValueError("Transfers require from_account_id and to_account_id.")
        transfer.status = TransactionStatus.PENDING
        return self.create(obj=transfer, owner=owner, **kwargs)

    def complete_transfer(
        self,
        *,
        transaction_id: uuid.UUID | TransactionsDTO | dict[str, Any],
        owner: UsersDTO | None = None,
        **kwargs,
    ) -> TransactionsDTO:
        """Mark a transfer as completed (``POST /movements/{id}/execute``)."""
        transfer = self._get_transfer(transaction_id=transaction_id, owner=owner, **kwargs)
        transfer.status = TransactionStatus.COMPLETED
        return self.create(obj=transfer, owner=owner, **kwargs)

    def cancel(
        self,
        *,
        transaction_id: uuid.UUID | TransactionsDTO | dict[str, Any],
        owner: UsersDTO | None = None,
        **kwargs,
    ) -> TransactionsDTO:
        """Cancel a transfer by setting ``status=CANCELLED`` (not soft delete)."""
        transfer = self._get_transfer(transaction_id=transaction_id, owner=owner, **kwargs)
        if transfer.status == TransactionStatus.CANCELLED:
            return transfer
        transfer.status = TransactionStatus.CANCELLED
        return self.create(obj=transfer, owner=owner, **kwargs)

    def _get_transfer(
        self,
        *,
        transaction_id: uuid.UUID | TransactionsDTO | dict[str, Any],
        owner: UsersDTO | None,
        **kwargs,
    ) -> TransactionsDTO:
        """Load and validate a transfer row for status transitions."""
        transfer = self.get(obj=transaction_id, owner=owner, include_linked_dtos=False, **kwargs)
        if transfer is None:
            raise ValueError("Transfer transaction not found.")
        if transfer.transaction_kind != TransactionKind.TRANSFER:
            raise ValueError("Transaction is not a transfer.")
        return transfer

    def aggregate_spending(
        self,
        *,
        owner: UsersDTO,
        start_date: date | datetime | None = None,
        end_date: date | datetime | None = None,
        account_id: uuid.UUID | None = None,
        group_by: Literal["category", "account"] = "category",
        **kwargs,
    ) -> dict[str, Any]:
        """SQL spending breakdown for completed expenses plus income/expense totals."""
        return self._repository.aggregate_spending(
            owner=owner,
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
            group_by=group_by,
            **kwargs,
        )

    def prefetch_link_dtos(
        self,
        *,
        owner: UsersDTO,
        account_ids: Sequence[uuid.UUID] | None = None,
        category_ids: Sequence[uuid.UUID] | None = None,
        **kwargs,
    ) -> dict[tuple[str, uuid.UUID], TableDTO]:
        """Prefetch account/category link DTOs for bulk create FK reuse.

        Missing IDs are omitted from the cache so per-item ``create`` still raises
        via ``get_or_create`` and bulk can count them as ``failed``.

        Args:
            owner: Tenant used for owned-table lookups.
            account_ids: Distinct account UUIDs referenced by the batch.
            category_ids: Distinct category UUIDs referenced by the batch.
            **kwargs: Forwarded to linked ``get`` calls.

        Returns:
            Cache mapping ``(field_name, id)`` to loaded DTOs for
            ``from_account_id``, ``to_account_id``, and ``category_id``.

        Raises:
            TypeError: When linked account/category services are not loaded.
        """
        accounts_service = self.accounts_service
        categories_service = self.categories_service
        if not isinstance(accounts_service, BaseService):
            raise TypeError("Accounts link service has not been loaded.")
        if not isinstance(categories_service, BaseService):
            raise TypeError("Categories link service has not been loaded.")

        cache: dict[tuple[str, uuid.UUID], TableDTO] = {}
        for account_id in {item for item in (account_ids or []) if item is not None}:
            account = accounts_service.get(obj=account_id, owner=owner, **kwargs)
            if account is None:
                continue
            cache[("from_account_id", account_id)] = account
            cache[("to_account_id", account_id)] = account

        for category_id in {item for item in (category_ids or []) if item is not None}:
            category = categories_service.get(obj=category_id, owner=owner, **kwargs)
            if category is None:
                continue
            cache[("category_id", category_id)] = category

        return cache

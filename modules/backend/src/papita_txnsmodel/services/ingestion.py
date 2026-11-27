"""Ingestion upsert bridge for trusted owner-scoped ledger writes (PPT-078 / #172).

Keeps idempotency on the non-partitioned provenance sidecar. Re-ingest with the same
``(owner, ingestion_source, source_ref)`` reuses the transaction id / ``transaction_ts``
and reactivates soft-deleted rows in place.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from papita_txnsmodel.access.ingestion.dto import IngestionDeadLetterDTO, TransactionIngestionProvenanceDTO
from papita_txnsmodel.access.ingestion.repository import (
    IngestionDeadLetterRepository,
    TransactionIngestionProvenanceRepository,
)
from papita_txnsmodel.access.transactions.dto import TransactionsDTO
from papita_txnsmodel.access.transactions.repository import TransactionsRepository
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import IngestionSource, SettlementStatus, TransactionKind, TransactionStatus
from papita_txnsmodel.services.accounts import AccountsService
from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.services.categories import CategoriesService
from papita_txnsmodel.services.transactions import TransactionsService, TransactionTemplatesService

logger = logging.getLogger(__name__)

IngestOutcome = Literal["created", "updated", "reactivated"]

_GENERIC_PARSER_TAGS = frozenset({"imported", "bancolombia", "nu", "global66", "nequi", "auto", "pse"})


def match_template_for_payload(
    *,
    templates: list[Any],
    description: str,
    tags: list[str],
    transaction_kind: TransactionKind,
    amount: float,
) -> Any | None:
    """Match an ingested transaction to a payment-due template via parser markers.

    Matches only outflows (EXPENSE) using:
    1. Specific shared parser tags (e.g. ``rent``, ``aluna-hoa``, ``card_last4:3250``).
    2. Template name contained in the transaction description.
    Breaks ties by proximity to ``planned_amount``.
    """
    if transaction_kind != TransactionKind.EXPENSE or not templates:
        return None

    txn_markers = {str(t).strip().lower() for t in tags if str(t).strip().lower() not in _GENERIC_PARSER_TAGS}
    desc_lower = (description or "").strip().lower()

    best_template = None
    best_score = 0
    for tmpl in templates:
        if not getattr(tmpl, "active", True):
            continue
        score = 0
        tmpl_tags = {
            str(t).strip().lower()
            for t in (getattr(tmpl, "tags", None) or [])
            if str(t).strip().lower() not in _GENERIC_PARSER_TAGS
        }
        shared_markers = txn_markers.intersection(tmpl_tags)
        if shared_markers:
            score += 4 * len(shared_markers)

        tmpl_name = str(getattr(tmpl, "name", "") or "").strip().lower()
        if tmpl_name and len(tmpl_name) >= 4 and tmpl_name in desc_lower:
            score += 3

        planned = float(getattr(tmpl, "planned_amount", 0) or 0)
        if score > 0 and planned > 0 and abs(amount - planned) / planned <= 0.2:
            score += 1

        if score > best_score:
            best_score = score
            best_template = tmpl

    return best_template if best_score >= 3 else None


class IngestTransactionRequest(BaseModel):
    """Model-local ingest payload (not an API schema). Trusted caller supplies ``owner``."""

    model_config = ConfigDict(extra="forbid")

    ingestion_source: IngestionSource
    source_ref: str | None = Field(default=None, max_length=255)
    transaction_kind: TransactionKind
    amount: float = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    transaction_ts: datetime | None = None
    from_account_id: uuid.UUID | None = None
    to_account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    template_id: uuid.UUID | None = None
    status: TransactionStatus = TransactionStatus.COMPLETED
    settlement_status: SettlementStatus = SettlementStatus.SETTLED
    description: str = ""
    reference_number: str | None = Field(default=None, max_length=64)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_kind_accounts(self) -> Self:
        """Enforce LK-style account/category shape before touching the ledger."""
        kind = self.transaction_kind
        if kind == TransactionKind.INCOME:
            if self.from_account_id is not None or self.to_account_id is None or self.category_id is None:
                raise ValueError("INCOME requires to_account_id and category_id; from_account_id must be null.")
        elif kind == TransactionKind.EXPENSE:
            if self.to_account_id is not None or self.from_account_id is None or self.category_id is None:
                raise ValueError("EXPENSE requires from_account_id and category_id; to_account_id must be null.")
        elif kind == TransactionKind.TRANSFER:
            if self.from_account_id is None or self.to_account_id is None or self.category_id is not None:
                raise ValueError("TRANSFER requires from_account_id and to_account_id; category_id must be null.")
        return self


class IngestTransactionResult(BaseModel):
    """Result of a single bridge ingest."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    outcome: IngestOutcome
    transaction: TransactionsDTO
    provenance: TransactionIngestionProvenanceDTO | None = None


class IngestionBridgeService(BaseService):
    """Trusted-owner bridge: validate → sidecar lookup → create/update/reactivate."""

    dto_type: type[TransactionIngestionProvenanceDTO] = TransactionIngestionProvenanceDTO
    repository_type: type[TransactionIngestionProvenanceRepository] = TransactionIngestionProvenanceRepository
    # Any allows test doubles; production wires TransactionsService in ``_init_deps``.
    transactions_service: Any | None = None
    dead_letter_repository_type: type[IngestionDeadLetterRepository] = IngestionDeadLetterRepository

    _dead_letter_repository: IngestionDeadLetterRepository | None = None

    @model_validator(mode="after")
    def _init_deps(self) -> Self:
        """Wire nested services/repositories after BaseService validation."""
        if self.transactions_service is None:
            # Mirror TransactionTemplatesService: LinkedEntitiesService.create requires
            # loaded account/category/template collaborators for non-null FKs.
            txn_service = TransactionsService.model_validate({"connector": self.connector})
            accounts = AccountsService.model_validate({"connector": self.connector})
            categories = CategoriesService.model_validate({"connector": self.connector})
            templates = TransactionTemplatesService.model_validate(
                {
                    "connector": self.connector,
                    "accounts_service": accounts,
                    # Reuse this txn service so templates wiring does not build a second one.
                    "transactions_service": txn_service,
                }
            )
            txn_service.load_link_services(
                {
                    "template_id": templates,
                    "from_account_id": accounts,
                    "to_account_id": accounts,
                    "category_id": categories,
                }
            )
            self.transactions_service = txn_service
        self._dead_letter_repository = self.dead_letter_repository_type()
        return self

    def ingest_transaction(
        self,
        *,
        owner: UsersDTO,
        request: IngestTransactionRequest | dict[str, Any],
        **kwargs,
    ) -> IngestTransactionResult:
        """Upsert a posted transaction with provenance idempotency when ``source_ref`` is set.

        Args:
            owner: Authenticated tenant (trusted; never taken from the payload).
            request: Ingest fields (kind, amount, accounts, source identity).
            **kwargs: Forwarded to transaction create/upsert (e.g. ``refresh_balances``).

        Returns:
            IngestTransactionResult with outcome and the ledger + provenance rows.

        Raises:
            ValueError: Invalid kind/account shape or missing owner.
        """
        if owner is None or owner.id is None:
            raise ValueError("ingest_transaction requires a trusted owner with an id.")

        payload = (
            request
            if isinstance(request, IngestTransactionRequest)
            else IngestTransactionRequest.model_validate(request)
        )
        if payload.template_id is None and payload.transaction_kind == TransactionKind.EXPENSE:
            matched_tmpl = self._find_matching_template(owner=owner, payload=payload)
            if matched_tmpl is not None and getattr(matched_tmpl, "id", None) is not None:
                payload = payload.model_copy(update={"template_id": matched_tmpl.id})
        source_ref = (payload.source_ref or "").strip() or None
        existing_prov = None
        if source_ref is not None:
            existing_prov = self._repository.get_by_source_ref(
                owner=owner,
                ingestion_source=payload.ingestion_source,
                source_ref=source_ref,
                include_deleted=True,
            )

        if existing_prov is not None:
            # Sidecar lookup only runs when source_ref is set; narrow for type checkers.
            if source_ref is None:
                raise RuntimeError("Provenance hit requires a non-null source_ref.")
            return self._reingest(
                owner=owner,
                payload=payload,
                provenance=existing_prov,
                source_ref=source_ref,
                **kwargs,
            )

        return self._create_new(
            owner=owner,
            payload=payload,
            source_ref=source_ref,
            **kwargs,
        )

    def record_dead_letter(
        self,
        *,
        owner: UsersDTO,
        ingestion_source: IngestionSource,
        raw_payload: str,
        error_message: str,
        source_ref: str | None = None,
        **kwargs,
    ) -> IngestionDeadLetterDTO:
        """Persist a thin DLQ row for a failed ingest attempt."""
        if owner is None or owner.id is None:
            raise ValueError("record_dead_letter requires a trusted owner with an id.")
        dto = IngestionDeadLetterDTO(
            owner_id=owner.id,
            ingestion_source=ingestion_source,
            raw_payload=raw_payload,
            error_message=error_message,
            source_ref=(source_ref or "").strip() or None,
        )
        return self._dead_letter_repository.upsert_record(dto, owner=owner, **kwargs) or dto

    def _find_matching_template(self, *, owner: UsersDTO, payload: IngestTransactionRequest) -> Any | None:
        """Best-effort auto-wire of an ingested expense to a payment-due template via parser markers."""
        try:
            tmpl_svc = TransactionTemplatesService.model_validate({"connector": self.connector})
            df = tmpl_svc.get_records(owner=owner, skip=0, limit=100, include_category=False)
            if df is None or df.empty:
                return None
            templates = [
                type(
                    "_Tmpl",
                    (),
                    {
                        "id": row.get("id"),
                        "name": row.get("name"),
                        "tags": row.get("tags") or [],
                        "planned_amount": row.get("planned_amount"),
                        "active": bool(row.get("active", True)),
                    },
                )()
                for _, row in df.iterrows()
            ]
            return match_template_for_payload(
                templates=templates,
                description=payload.description,
                tags=payload.tags,
                transaction_kind=payload.transaction_kind,
                amount=payload.amount,
            )
        except Exception:  # pylint: disable=broad-except
            logger.debug("Template auto-match skipped for owner_id=%s", owner.id, exc_info=True)
            return None

    def _create_new(
        self,
        *,
        owner: UsersDTO,
        payload: IngestTransactionRequest,
        source_ref: str | None,
        **kwargs,
    ) -> IngestTransactionResult:
        txn = self._build_transaction_dto(owner=owner, payload=payload, txn_id=None, transaction_ts=None)
        created = self._normalize_transaction(
            self.transactions_service.create(obj=txn, owner=owner, include_category=False, **kwargs)
        )
        provenance = None
        if source_ref is not None:
            provenance = self._upsert_provenance(
                owner=owner,
                transaction=created,
                ingestion_source=payload.ingestion_source,
                source_ref=source_ref,
                provenance_id=None,
                reactivate=False,
            )
        return IngestTransactionResult(outcome="created", transaction=created, provenance=provenance)

    def _reingest(
        self,
        *,
        owner: UsersDTO,
        payload: IngestTransactionRequest,
        provenance: TransactionIngestionProvenanceDTO,
        source_ref: str,
        **kwargs,
    ) -> IngestTransactionResult:
        was_inactive = not bool(getattr(provenance, "active", True))
        existing_txn = TransactionsRepository().get_record_by_id(
            provenance.transaction_id,
            owner=owner,
            dto_type=TransactionsDTO,
            include_deleted=True,
        )
        if existing_txn is None:
            raise RuntimeError(f"Provenance {provenance.id} points at missing transaction {provenance.transaction_id}.")
        if not bool(getattr(existing_txn, "active", True)):
            was_inactive = True

        # Keep partition key + id stable; refresh mutable ledger fields from payload.
        txn = self._build_transaction_dto(
            owner=owner,
            payload=payload,
            txn_id=provenance.transaction_id,
            transaction_ts=provenance.transaction_ts,
        )
        updated = self._normalize_transaction(
            self.transactions_service.create(obj=txn, owner=owner, reactivate=True, include_category=False, **kwargs)
        )
        updated_prov = self._upsert_provenance(
            owner=owner,
            transaction=updated,
            ingestion_source=payload.ingestion_source,
            source_ref=source_ref,
            provenance_id=provenance.id,
            reactivate=True,
        )
        outcome: IngestOutcome = "reactivated" if was_inactive else "updated"
        return IngestTransactionResult(outcome=outcome, transaction=updated, provenance=updated_prov)

    def _upsert_provenance(
        self,
        *,
        owner: UsersDTO,
        transaction: TransactionsDTO,
        ingestion_source: IngestionSource,
        source_ref: str,
        provenance_id: uuid.UUID | None,
        reactivate: bool,
    ) -> TransactionIngestionProvenanceDTO:
        if transaction.id is None:
            raise ValueError("Transaction must have an id before provenance upsert.")
        dto = TransactionIngestionProvenanceDTO(
            id=provenance_id or uuid.uuid4(),
            owner_id=owner.id,
            transaction_id=transaction.id,
            transaction_ts=transaction.transaction_ts,
            ingestion_source=ingestion_source,
            source_ref=source_ref,
            active=True,
            deleted_at=None,
        )
        return self._repository.upsert_record(dto, owner=owner, reactivate=reactivate) or dto

    @staticmethod
    def _normalize_transaction(txn: TransactionsDTO | Any) -> TransactionsDTO:
        """Collapse LinkedEntitiesService-hydrated relation DTOs back to UUIDs."""
        if not isinstance(txn, TransactionsDTO):
            txn = TransactionsDTO.model_validate(txn)
        data = txn.model_dump(mode="python")
        for key in ("from_account_id", "to_account_id", "category_id", "template_id", "owner_id"):
            value = data.get(key)
            if value is None or isinstance(value, uuid.UUID):
                continue
            if isinstance(value, dict) and value.get("id") is not None:
                data[key] = value["id"]
            elif hasattr(value, "id"):
                data[key] = getattr(value, "id")
        return TransactionsDTO.model_validate(data)

    @staticmethod
    def _build_transaction_dto(
        *,
        owner: UsersDTO,
        payload: IngestTransactionRequest,
        txn_id: uuid.UUID | None,
        transaction_ts: datetime | None,
    ) -> TransactionsDTO:
        ts = transaction_ts if transaction_ts is not None else payload.transaction_ts
        return TransactionsDTO(
            id=txn_id or uuid.uuid4(),
            owner_id=owner.id,
            transaction_kind=payload.transaction_kind,
            amount=payload.amount,
            currency=payload.currency,
            transaction_ts=ts if ts is not None else datetime.now(),
            from_account_id=payload.from_account_id,
            to_account_id=payload.to_account_id,
            category_id=payload.category_id,
            template_id=payload.template_id,
            status=payload.status,
            settlement_status=payload.settlement_status,
            description=payload.description,
            reference_number=payload.reference_number,
            tags=list(payload.tags),
            active=True,
            deleted_at=None,
        )

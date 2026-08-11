"""Map ParsedRecord → IngestTransactionRequest (PPT-079 / #173)."""

from __future__ import annotations

from papita_ingestor_core.errors.taxonomy import IngestorValidationError
from papita_ingestor_core.types.records import ParsedRecord
from papita_txnsmodel.model.enums import TransactionKind
from papita_txnsmodel.services.ingestion import IngestTransactionRequest


def _assert_complete_fks(parsed: ParsedRecord) -> None:
    """Require kind-shaped account/category FKs before calling the bridge."""
    kind = parsed.transaction_kind
    if kind == TransactionKind.INCOME:
        if parsed.from_account_id is not None or parsed.to_account_id is None or parsed.category_id is None:
            raise IngestorValidationError(
                "INCOME ParsedRecord requires to_account_id and category_id; from_account_id must be null."
            )
    elif kind == TransactionKind.EXPENSE:
        if parsed.to_account_id is not None or parsed.from_account_id is None or parsed.category_id is None:
            raise IngestorValidationError(
                "EXPENSE ParsedRecord requires from_account_id and category_id; to_account_id must be null."
            )
    elif kind == TransactionKind.TRANSFER:
        if parsed.from_account_id is None or parsed.to_account_id is None or parsed.category_id is not None:
            raise IngestorValidationError(
                "TRANSFER ParsedRecord requires from_account_id and to_account_id; category_id must be null."
            )
    else:
        raise IngestorValidationError(f"Unsupported transaction_kind: {kind!r}")


def to_ingest_transaction_request(parsed: ParsedRecord) -> IngestTransactionRequest:
    """Convert a complete ``ParsedRecord`` into a bridge request.

    Raises:
        IngestorValidationError: Incomplete FKs for the transaction kind.
    """
    _assert_complete_fks(parsed)
    return IngestTransactionRequest(
        ingestion_source=parsed.ingestion_source,
        source_ref=parsed.source_ref,
        transaction_kind=parsed.transaction_kind,
        amount=parsed.amount,
        currency=parsed.currency,
        transaction_ts=parsed.transaction_ts,
        from_account_id=parsed.from_account_id,
        to_account_id=parsed.to_account_id,
        category_id=parsed.category_id,
        template_id=parsed.template_id,
        status=parsed.status,
        description=parsed.description,
        reference_number=parsed.reference_number,
        tags=list(parsed.tags),
    )


__all__ = ["to_ingest_transaction_request"]

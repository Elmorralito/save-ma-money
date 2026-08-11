"""IngestionRunner: fetch → parse → validate → bridge persist → ack (PPT-079 / #173)."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Iterator
from typing import Any, TypeAlias

from papita_ingestor_core.errors.taxonomy import (
    IngestorConnectionError,
    IngestorError,
    IngestorFetchError,
    IngestorParseError,
    IngestorPersistError,
    IngestorValidationError,
)
from papita_ingestor_core.mapping.raw_payload import encode_raw_payload
from papita_ingestor_core.mapping.to_bridge import to_ingest_transaction_request
from papita_ingestor_core.parsers.base import BaseRecordParser
from papita_ingestor_core.registry.parsers import ParserRegistry
from papita_ingestor_core.settings.base import BaseIngestorSettings
from papita_ingestor_core.sources.base import BaseIngestorSource
from papita_ingestor_core.types.records import FetchFilter, RawRecord, RecordFailure, RunResult
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.ingestion import IngestionBridgeService

logger = logging.getLogger(__name__)

OwnerProvider: TypeAlias = UsersDTO | Callable[[], UsersDTO]
_KNOWN_OUTCOMES = frozenset({"created", "updated", "reactivated"})


class IngestionRunner:
    """Orchestrate one ingestion run against a source and registered parsers."""

    _source: BaseIngestorSource
    _owner: OwnerProvider
    _bridge: IngestionBridgeService | Any
    _parsers: list[BaseRecordParser] | None
    _settings: BaseIngestorSettings

    def __init__(
        self,
        *,
        source: BaseIngestorSource,
        owner: OwnerProvider,
        bridge: IngestionBridgeService | Any,
        parsers: Iterable[BaseRecordParser] | None = None,
        settings: BaseIngestorSettings | None = None,
    ) -> None:
        if owner is None:
            raise ValueError("IngestionRunner requires an owner UsersDTO or zero-arg callable")
        self._source = source
        self._owner = owner
        self._bridge = bridge
        self._parsers = list(parsers) if parsers is not None else None
        self._settings = settings or BaseIngestorSettings()

    def _resolve_owner(self) -> UsersDTO:
        owner = self._owner() if callable(self._owner) else self._owner
        if owner is None or getattr(owner, "id", None) is None:
            raise ValueError("IngestionRunner owner must be a UsersDTO with an id")
        return owner

    def _resolve_parsers(self) -> list[BaseRecordParser]:
        """Cache parser instances once per run (avoid per-record construction)."""
        if self._parsers is not None:
            parsers = list(self._parsers)
        else:
            parsers = ParserRegistry.create_instances()
        if not parsers:
            raise ValueError(
                "IngestionRunner requires at least one parser "
                + "(pass parsers=… or register parsers on ParserRegistry)"
            )
        return parsers

    def _effective_fetch_filter(self, fetch_filter: FetchFilter | None) -> FetchFilter | None:
        """Merge settings.fetch_limit when the caller did not set FetchFilter.limit."""
        limit = self._settings.fetch_limit
        if fetch_filter is None:
            if limit is None:
                return None
            return FetchFilter(limit=limit)
        if fetch_filter.limit is None and limit is not None:
            return fetch_filter.model_copy(update={"limit": limit})
        return fetch_filter

    def _iter_records(self, fetch_filter: FetchFilter | None) -> Iterator[RawRecord]:
        """Stream source records; enforce limit even if the source ignores FetchFilter."""
        effective = self._effective_fetch_filter(fetch_filter)
        limit = effective.limit if effective is not None else None
        yielded = 0
        for record in self._source.fetch(effective):
            yield record
            yielded += 1
            if limit is not None and yielded >= limit:
                break

    def run(self, fetch_filter: FetchFilter | None = None) -> RunResult:
        """Execute fetch → parse → persist → ack. Connect/fetch failures abort the run.

        Per-record ack failures are recorded and the batch continues. Parse/validation
        failures dead-letter then ack (poison-message semantics) when DLQ write succeeds.
        """
        result = RunResult()
        owner = self._resolve_owner()
        parsers = self._resolve_parsers()
        try:
            self._source.connect()
        except IngestorError:
            raise
        except Exception as exc:
            raise IngestorConnectionError(str(exc)) from exc

        try:
            try:
                for record in self._iter_records(fetch_filter):
                    result.fetched += 1
                    self._process_record(owner=owner, record=record, result=result, parsers=parsers)
            except IngestorError:
                raise
            except Exception as exc:
                raise IngestorFetchError(str(exc)) from exc
        finally:
            try:
                self._source.disconnect()
            except Exception:  # pylint: disable=broad-except
                logger.exception("Source disconnect failed for %s", self._source.source_id)

        return result

    def _parse_and_map(self, *, record: RawRecord, parsers: list[BaseRecordParser]):
        """Select parser, parse/validate, and map to a bridge request."""
        if not (record.source_ref or "").strip():
            raise IngestorValidationError("RawRecord.source_ref is required for idempotent ingest")

        parser = ParserRegistry.select_for(record, instances=parsers)
        try:
            parsed = parser.parse(record)
            parsed = parser.validate(parsed)
        except IngestorValidationError:
            raise
        except IngestorParseError:
            raise
        except Exception as exc:
            raise IngestorParseError(str(exc)) from exc

        if not (parsed.source_ref or "").strip():
            raise IngestorValidationError("ParsedRecord.source_ref is required for idempotent ingest")
        return to_ingest_transaction_request(parsed)

    def _persist(self, *, owner: UsersDTO, request: Any) -> str:
        """Call the bridge and return a known outcome string."""
        try:
            ingest_result = self._bridge.ingest_transaction(owner=owner, request=request)
        except ValueError as exc:
            raise IngestorValidationError(str(exc)) from exc
        except IngestorError:
            raise
        except Exception as exc:
            raise IngestorPersistError(str(exc)) from exc

        outcome = getattr(ingest_result, "outcome", None)
        if outcome not in _KNOWN_OUTCOMES:
            raise IngestorPersistError(f"Unexpected ingest outcome: {outcome!r}")
        return outcome

    @staticmethod
    def _count_outcome(result: RunResult, outcome: str) -> None:
        if outcome == "created":
            result.created += 1
        elif outcome == "updated":
            result.updated += 1
        else:
            result.reactivated += 1

    def _record_persist_failure(self, *, record: RawRecord, result: RunResult, exc: IngestorPersistError) -> None:
        result.failed += 1
        result.failures.append(
            RecordFailure(
                source_ref=record.source_ref,
                error_type=type(exc).__name__,
                message=str(exc),
                dead_lettered=False,
            )
        )
        logger.warning("Persist failed source_ref=%s: %s", record.source_ref, exc)

    def _process_record(
        self,
        *,
        owner: UsersDTO,
        record: RawRecord,
        result: RunResult,
        parsers: list[BaseRecordParser],
    ) -> None:
        try:
            request = self._parse_and_map(record=record, parsers=parsers)
            if self._settings.dry_run:
                result.dry_run_skipped += 1
                return
            outcome = self._persist(owner=owner, request=request)
            self._count_outcome(result, outcome)
            self._acknowledge(record=record, result=result, count_as_failure=True)
        except (IngestorParseError, IngestorValidationError) as exc:
            self._dead_letter(owner=owner, record=record, result=result, exc=exc)
        except IngestorPersistError as exc:
            self._record_persist_failure(record=record, result=result, exc=exc)
        except LookupError as exc:
            self._dead_letter(
                owner=owner,
                record=record,
                result=result,
                exc=IngestorParseError(str(exc)),
            )

    def _acknowledge(self, *, record: RawRecord, result: RunResult, count_as_failure: bool) -> bool:
        """Ack at the source; never raise — batch processing must continue."""
        try:
            self._source.acknowledge(record)
            result.acknowledged += 1
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Acknowledge failed source_ref=%s", record.source_ref)
            if count_as_failure:
                result.failed += 1
            result.failures.append(
                RecordFailure(
                    source_ref=record.source_ref,
                    error_type="IngestorAckError",
                    message=str(exc),
                    dead_lettered=False,
                )
            )
            return False

    def _dead_letter(
        self,
        *,
        owner: UsersDTO,
        record: RawRecord,
        result: RunResult,
        exc: Exception,
    ) -> None:
        """Record a DLQ row; on success ack the poison message to stop redelivery."""
        if self._settings.dry_run:
            result.failed += 1
            result.dry_run_skipped += 1
            result.failures.append(
                RecordFailure(
                    source_ref=record.source_ref,
                    error_type=type(exc).__name__,
                    message=str(exc),
                    dead_lettered=False,
                )
            )
            return

        result.failed += 1
        dead_lettered = False
        try:
            self._bridge.record_dead_letter(
                owner=owner,
                ingestion_source=record.ingestion_source,
                raw_payload=encode_raw_payload(record),
                error_message=str(exc),
                source_ref=record.source_ref,
            )
            dead_lettered = True
            result.dead_lettered += 1
        except Exception:  # pylint: disable=broad-except
            logger.exception("Dead-letter write failed source_ref=%s", record.source_ref)
        result.failures.append(
            RecordFailure(
                source_ref=record.source_ref,
                error_type=type(exc).__name__,
                message=str(exc),
                dead_lettered=dead_lettered,
            )
        )
        if dead_lettered:
            # Poison-message: ack after successful DLQ so the source does not redeliver forever.
            self._acknowledge(record=record, result=result, count_as_failure=False)


__all__ = ["IngestionRunner", "OwnerProvider"]

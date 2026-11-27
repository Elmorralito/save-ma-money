"""Unit tests for the holistic search query parser and interleaving engine."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from papita_txnsmodel.services.global_search import (
    KIND_ACCOUNT,
    KIND_CATEGORY,
    KIND_PAYMENT_DUE,
    KIND_PROJECTION,
    KIND_TRANSACTION,
    GlobalSearchHit,
    _interleave,
    _resolve_kinds,
    parse_global_search_query,
)


def test_parse_kind_aliases_and_structured_filters() -> None:
    parts = parse_global_search_query("txn nu >500000 currency:COP date:>=2026-01-01")
    assert parts.kinds == (KIND_TRANSACTION,)
    assert parts.residual_q == "nu"
    assert parts.text_tokens == ("nu",)
    assert parts.currency == "COP"
    assert len(parts.amount_bounds) == 1
    assert parts.amount_bounds[0].op == ">"
    assert parts.amount_bounds[0].value == pytest.approx(500000.0)
    assert len(parts.date_bounds) == 1
    assert parts.date_bounds[0].op == ">="


def test_parse_hint_words_keep_residual_and_uuid() -> None:
    sample_id = uuid.uuid4()
    parts = parse_global_search_query(f"loan {sample_id} deleted:true")
    assert KIND_ACCOUNT in parts.kinds
    assert KIND_PROJECTION in parts.kinds
    assert parts.exact_id == sample_id
    assert "loan" in parts.text_tokens
    assert parts.deleted_presence is True


def test_resolve_kinds_and_round_robin_interleave() -> None:
    assert _resolve_kinds(requested={KIND_TRANSACTION, KIND_ACCOUNT}, implied={KIND_TRANSACTION}) == (KIND_TRANSACTION,)
    assert _resolve_kinds(requested=set(), implied=set()) == (
        KIND_ACCOUNT,
        KIND_TRANSACTION,
        KIND_PAYMENT_DUE,
        KIND_CATEGORY,
        KIND_PROJECTION,
    )

    acc_hits = [GlobalSearchHit(kind=KIND_ACCOUNT, id=uuid.uuid4(), title=f"A{i}", subtitle="") for i in range(3)]
    txn_hits = [GlobalSearchHit(kind=KIND_TRANSACTION, id=uuid.uuid4(), title=f"T{i}", subtitle="") for i in range(5)]
    due_hits = [GlobalSearchHit(kind=KIND_PAYMENT_DUE, id=uuid.uuid4(), title=f"D{i}", subtitle="") for i in range(1)]

    merged = _interleave([acc_hits, txn_hits, due_hits], limit=6)
    assert [h.title for h in merged] == ["A0", "T0", "D0", "A1", "T1", "A2"]


def test_parse_edge_cases_dates_amounts_and_currencies() -> None:
    """Parser handles date operators, timestamps, bad inputs, currency aliases, and empty strings."""
    empty = parse_global_search_query("   ")
    assert empty.kinds == ()
    assert empty.residual_q == ""

    parts = parse_global_search_query(
        "amt:=1,250.50 cur:usd created:<2026-06-01 date:<=2026-05-01 date:>2026-01-01 "
        "date:=2026-02-02T10:30:00Z baddate:notadate amount:bad cur:12 deleted:false"
    )
    assert parts.currency == "USD"
    assert len(parts.amount_bounds) == 1
    assert parts.amount_bounds[0].op == "="
    assert parts.amount_bounds[0].value == pytest.approx(1250.50)
    assert len(parts.date_bounds) == 4
    assert parts.deleted_presence is False
    assert "baddate:notadate" in parts.text_tokens


def test_search_everything_covers_all_entity_kinds() -> None:
    """Exercise search_everything across accounts, transactions, dues, categories, and projections."""
    from datetime import datetime, timezone
    from types import SimpleNamespace

    from papita_txnsmodel.services import global_search

    owner_id = uuid.uuid4()
    acc_id = uuid.uuid4()
    txn_id = uuid.uuid4()
    due_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    now = datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc)

    fake_acc = SimpleNamespace(
        id=acc_id,
        name="Bancolombia Savings",
        account_kind=SimpleNamespace(value="savings"),
        ledger_side=SimpleNamespace(value="asset"),
        currency="COP",
        current_value=2_000_000.0,
        initial_value=1_000_000.0,
        opened_at=now,
        active=True,
    )
    fake_txn = SimpleNamespace(
        id=txn_id,
        description="Nu Card Payment",
        reference_number="REF-1",
        transaction_kind=SimpleNamespace(value="transfer"),
        amount=500_000.0,
        currency="COP",
        transaction_ts=now,
        from_account_id=acc_id,
        to_account_id=None,
        template_id=due_id,
        tags=["card", "monthly"],
    )
    fake_due = SimpleNamespace(
        id=due_id,
        name="Rent",
        description="Monthly apartment rent",
        due_date=now.date(),
        planned_day=15,
        planned_amount=1_500_000.0,
        from_account_id=acc_id,
        tags=["housing"],
    )
    fake_cat = SimpleNamespace(
        id=cat_id,
        name="Housing",
        category_kind=SimpleNamespace(value="expense"),
        owner_id=None,
    )

    class _FakeScalarResult:
        def __init__(self, rows: list[Any]) -> None:
            self._rows = rows

        def all(self) -> list[Any]:
            return self._rows

    class _FakeSession:
        def __init__(self) -> None:
            self._call = 0

        def scalars(self, stmt: Any) -> _FakeScalarResult:
            sql_text = str(stmt)
            if "FROM papita_transactions.accounts" in sql_text:
                return _FakeScalarResult([fake_acc])
            if "FROM papita_transactions.transactions" in sql_text:
                return _FakeScalarResult([fake_txn])
            if "FROM papita_transactions.transaction_templates" in sql_text:
                return _FakeScalarResult([fake_due])
            if "FROM papita_transactions.categories" in sql_text:
                return _FakeScalarResult([fake_cat])
            return _FakeScalarResult([])

        def exec(self, stmt: Any) -> _FakeScalarResult:
            del stmt
            return _FakeScalarResult([(acc_id, "COP")])

    owner = SimpleNamespace(
        id=owner_id,
        preferences={
            "projection_configs": {
                str(acc_id): {"annual_rate_pct": 11.5, "rate_convention": "CO_EA"},
                "not-a-uuid": {},
            }
        },
    )
    session = _FakeSession()

    result = global_search.search_everything(
        session,  # type: ignore[arg-type]
        owner=owner,  # type: ignore[arg-type]
        q=f"{acc_id} >=100 <=5000000 date:>=2026-01-01 date:=2026-03-15 currency:COP",
        limit=20,
    )
    kinds_found = {hit.kind for hit in result.items}
    assert global_search.KIND_ACCOUNT in kinds_found
    assert global_search.KIND_TRANSACTION in kinds_found
    assert global_search.KIND_PAYMENT_DUE in kinds_found
    assert global_search.KIND_PROJECTION in kinds_found

    text_res = global_search.search_everything(
        session,  # type: ignore[arg-type]
        owner=owner,  # type: ignore[arg-type]
        q="bancolombia >100 <9000000 =2000000 date:<2026-12-31 date:>2025-01-01",
        kinds=(global_search.KIND_ACCOUNT, global_search.KIND_CATEGORY),
        limit=10,
    )
    assert any(h.kind == global_search.KIND_CATEGORY and h.flags == ("global",) for h in text_res.items)

    # Empty query or missing owner returns empty result cleanly
    assert global_search.search_everything(session, owner=owner, q="   ").items == ()  # type: ignore[arg-type]
    assert (
        global_search.search_everything(session, owner=SimpleNamespace(id=None), q="test").items == ()  # type: ignore[arg-type]
    )

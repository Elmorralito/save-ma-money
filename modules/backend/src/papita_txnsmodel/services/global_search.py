"""Unified holistic search engine across accounts, transactions, payment dues, categories, and projections.

Patterned after Piggies-VetPharma-Track's unified search architecture:
- Structured query parser supporting pure kind selectors, hint words, exact UUIDs,
  date bounds (``date:>=2026-01-01``, ``created:<2026-06-01``, ``deleted:true``),
  numeric amount bounds (``amount:>=500000``, ``>100000``), and currency filters
  (``currency:USD``, ``cur:COP``).
- Strict owner-scoped SQLAlchemy queries across the full database (never truncated
  to a client-side page).
- Round-robin interleaving across entity kinds so noisy tables cannot crowd out
  accounts, dues, categories, or projections.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Literal

from sqlalchemy import String, and_, cast, func, or_, select
from sqlmodel import Session

from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.accounts import Accounts
from papita_txnsmodel.model.categories import Categories
from papita_txnsmodel.model.transactions import Transactions, TransactionTemplates

KIND_ACCOUNT = "account"
KIND_TRANSACTION = "transaction"
KIND_PAYMENT_DUE = "payment_due"
KIND_CATEGORY = "category"
KIND_PROJECTION = "projection"

SEARCH_KINDS: tuple[str, ...] = (
    KIND_ACCOUNT,
    KIND_TRANSACTION,
    KIND_PAYMENT_DUE,
    KIND_CATEGORY,
    KIND_PROJECTION,
)
SEARCH_KIND_SET: frozenset[str] = frozenset(SEARCH_KINDS)

DateField = Literal["occurred_at", "created_at", "deleted_at"]
CompareOp = Literal[">=", "<=", ">", "<", "="]

_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_BARE_AMOUNT_RE = re.compile(r"^(>=|<=|>|<)(\d+(?:[.,]\d+)?)$")
_OPS: tuple[str, ...] = (">=", "<=", "==", ">", "<", "=")

# Pure kind selectors: narrow kinds and are removed from residual text.
_PURE_KIND_ALIASES: dict[str, frozenset[str]] = {
    "acc": frozenset({KIND_ACCOUNT}),
    "account": frozenset({KIND_ACCOUNT}),
    "accounts": frozenset({KIND_ACCOUNT}),
    "bank": frozenset({KIND_ACCOUNT}),
    "banks": frozenset({KIND_ACCOUNT}),
    "txn": frozenset({KIND_TRANSACTION}),
    "txns": frozenset({KIND_TRANSACTION}),
    "transaction": frozenset({KIND_TRANSACTION}),
    "transactions": frozenset({KIND_TRANSACTION}),
    "ledger": frozenset({KIND_TRANSACTION}),
    "movement": frozenset({KIND_TRANSACTION}),
    "movements": frozenset({KIND_TRANSACTION}),
    "due": frozenset({KIND_PAYMENT_DUE}),
    "dues": frozenset({KIND_PAYMENT_DUE}),
    "bill": frozenset({KIND_PAYMENT_DUE}),
    "bills": frozenset({KIND_PAYMENT_DUE}),
    "template": frozenset({KIND_PAYMENT_DUE}),
    "templates": frozenset({KIND_PAYMENT_DUE}),
    "recurring": frozenset({KIND_PAYMENT_DUE}),
    "cat": frozenset({KIND_CATEGORY}),
    "category": frozenset({KIND_CATEGORY}),
    "categories": frozenset({KIND_CATEGORY}),
    "proj": frozenset({KIND_PROJECTION}),
    "projection": frozenset({KIND_PROJECTION}),
    "projections": frozenset({KIND_PROJECTION}),
    "amortization": frozenset({KIND_PROJECTION}),
}

# Hint words: narrow kinds AND remain in residual text for per-kind filtering.
_HINT_KIND_ALIASES: dict[str, frozenset[str]] = {
    "income": frozenset({KIND_TRANSACTION, KIND_CATEGORY}),
    "expense": frozenset({KIND_TRANSACTION, KIND_CATEGORY}),
    "transfer": frozenset({KIND_TRANSACTION}),
    "loan": frozenset({KIND_ACCOUNT, KIND_PROJECTION}),
    "mortgage": frozenset({KIND_ACCOUNT, KIND_PROJECTION}),
    "debt": frozenset({KIND_ACCOUNT, KIND_PROJECTION}),
    "credit_card": frozenset({KIND_ACCOUNT, KIND_PROJECTION}),
    "real_estate": frozenset({KIND_ACCOUNT, KIND_PROJECTION}),
    "investment": frozenset({KIND_ACCOUNT, KIND_PROJECTION}),
    "checking": frozenset({KIND_ACCOUNT}),
    "savings": frozenset({KIND_ACCOUNT}),
}

_DATE_FIELD_ALIASES: dict[str, DateField] = {
    "date": "occurred_at",
    "on": "occurred_at",
    "created": "created_at",
    "created_at": "created_at",
    "deleted": "deleted_at",
    "deleted_at": "deleted_at",
}


@dataclass(frozen=True, slots=True)
class DateBound:
    field: DateField
    op: CompareOp
    instant: datetime


@dataclass(frozen=True, slots=True)
class AmountBound:
    op: CompareOp
    value: float


@dataclass(frozen=True, slots=True)
class GlobalSearchParts:
    kinds: tuple[str, ...]
    residual_q: str
    text_tokens: tuple[str, ...]
    exact_id: uuid.UUID | None
    currency: str | None = None
    amount_bounds: tuple[AmountBound, ...] = field(default_factory=tuple)
    date_bounds: tuple[DateBound, ...] = field(default_factory=tuple)
    deleted_presence: bool | None = None


@dataclass(frozen=True, slots=True)
class GlobalSearchHit:
    kind: str
    id: uuid.UUID
    title: str
    subtitle: str
    occurred_at: datetime | None = None
    status: str | None = None
    amount: float | None = None
    currency: str | None = None
    account_id: uuid.UUID | None = None
    flags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GlobalSearchResult:
    q: str
    kinds: tuple[str, ...]
    account_id: uuid.UUID | None
    limit: int
    items: tuple[GlobalSearchHit, ...]


def split_search_tokens(raw: str) -> tuple[str, ...]:
    """Split ``raw`` on whitespace into non-empty tokens."""
    return tuple(part for part in re.split(r"\s+", raw.strip()) if part)


def parse_uuid_token(token: str) -> uuid.UUID | None:
    """Return a UUID when ``token`` is an exact UUID string; otherwise ``None``."""
    if not _UUID_RE.match(token):
        return None
    try:
        return uuid.UUID(token)
    except ValueError:
        return None


def _split_op(rest: str) -> tuple[CompareOp, str]:
    for candidate in _OPS:
        if rest.startswith(candidate):
            op: CompareOp = "=" if candidate == "==" else candidate  # type: ignore[assignment]
            return op, rest[len(candidate) :]
    return "=", rest


def _parse_instant(raw: str, *, op: CompareOp) -> datetime | None:
    text = raw.strip()
    if not text:
        return None
    if _DATE_ONLY_RE.match(text):
        try:
            day = date.fromisoformat(text)
        except ValueError:
            return None
        start = datetime.combine(day, time.min, tzinfo=UTC)
        if op == "<=":
            return datetime.combine(day, time(23, 59, 59, 999999), tzinfo=UTC)
        if op == ">":
            return start + timedelta(days=1)
        return start
    normalized = text.replace("Z", "+00:00").replace("z", "+00:00").replace(" ", "T", 1)
    try:
        instant = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    return instant.astimezone(UTC)


def _parse_date_or_deleted(token: str) -> DateBound | bool | None:
    """Parse ``date:>=2026-01-01``, ``created:<2026-06-01``, or ``deleted:true``."""
    lower = token.lower()
    for alias, field_name in sorted(_DATE_FIELD_ALIASES.items(), key=lambda item: -len(item[0])):
        rest: str | None = None
        if lower.startswith(f"{alias}:"):
            rest = token[len(alias) + 1 :]
        elif lower.startswith(alias) and len(token) > len(alias) and token[len(alias)] in "><=":
            rest = token[len(alias) :]
        if rest is None:
            continue
        trimmed = rest.strip()
        if not trimmed:
            return None
        if field_name == "deleted_at" and trimmed.lower() in {"true", "yes", "1"}:
            return True
        if field_name == "deleted_at" and trimmed.lower() in {"false", "no", "0", "null", "none"}:
            return False
        op, value = _split_op(trimmed)
        instant = _parse_instant(value, op=op)
        if instant is None:
            return None
        return DateBound(field=field_name, op=op, instant=instant)
    return None


def _parse_amount_bound(token: str) -> AmountBound | None:
    lower = token.lower()
    rest: str | None = None
    for prefix in ("amount:", "amt:"):
        if lower.startswith(prefix):
            rest = token[len(prefix) :].strip()
            break
    if rest is not None:
        op, raw_num = _split_op(rest)
        cleaned = raw_num.replace(",", "").replace("$", "").strip()
        try:
            return AmountBound(op=op, value=float(cleaned))
        except ValueError:
            return None
    m = _BARE_AMOUNT_RE.match(token)
    if m:
        op_raw, num_raw = m.group(1), m.group(2).replace(",", "")
        try:
            return AmountBound(op=op_raw, value=float(num_raw))  # type: ignore[arg-type]
        except ValueError:
            return None
    return None


def _parse_currency_token(token: str) -> str | None:
    lower = token.lower()
    for prefix in ("currency:", "cur:"):
        if lower.startswith(prefix):
            val = token[len(prefix) :].strip().upper()
            if len(val) == 3 and val.isalpha():
                return val
    return None


def parse_global_search_query(raw: str) -> GlobalSearchParts:
    """Parse free-text query into kind selectors, structured filters, and residual tokens."""
    tokens = split_search_tokens(raw)
    if not tokens:
        return GlobalSearchParts(kinds=(), residual_q="", text_tokens=(), exact_id=None)

    kinds: set[str] = set()
    residual: list[str] = []
    text_tokens: list[str] = []
    exact_id: uuid.UUID | None = None
    currency: str | None = None
    amount_bounds: list[AmountBound] = []
    date_bounds: list[DateBound] = []
    deleted_presence: bool | None = None

    for token in tokens:
        lower = token.lower()
        cur = _parse_currency_token(token)
        if cur is not None:
            currency = cur
            continue
        amt = _parse_amount_bound(token)
        if amt is not None:
            amount_bounds.append(amt)
            continue
        dt = _parse_date_or_deleted(token)
        if isinstance(dt, bool):
            deleted_presence = dt
            continue
        if isinstance(dt, DateBound):
            date_bounds.append(dt)
            continue
        parsed_id = parse_uuid_token(token)
        if parsed_id is not None:
            exact_id = parsed_id
            residual.append(token)
            continue
        pure = _PURE_KIND_ALIASES.get(lower)
        if pure is not None:
            kinds.update(pure)
            continue
        hint = _HINT_KIND_ALIASES.get(lower)
        if hint is not None:
            kinds.update(hint)
            residual.append(token)
            text_tokens.append(token)
            continue
        residual.append(token)
        text_tokens.append(token)

    return GlobalSearchParts(
        kinds=tuple(sorted(kinds)),
        residual_q=" ".join(residual),
        text_tokens=tuple(text_tokens),
        exact_id=exact_id,
        currency=currency,
        amount_bounds=tuple(amount_bounds),
        date_bounds=tuple(date_bounds),
        deleted_presence=deleted_presence,
    )


def _resolve_kinds(*, requested: set[str], implied: set[str]) -> tuple[str, ...]:
    if requested and implied:
        resolved = (requested & implied) or requested
    elif requested:
        resolved = set(requested)
    elif implied:
        resolved = set(implied)
    else:
        resolved = set(SEARCH_KINDS)
    return tuple(k for k in SEARCH_KINDS if k in resolved)


def _interleave(buckets: Sequence[Sequence[GlobalSearchHit]], limit: int) -> tuple[GlobalSearchHit, ...]:
    """Round-robin across kinds so one noisy kind cannot crowd out the rest."""
    merged: list[GlobalSearchHit] = []
    cursors = [0] * len(buckets)
    while len(merged) < limit:
        progressed = False
        for index, bucket in enumerate(buckets):
            if cursors[index] >= len(bucket):
                continue
            merged.append(bucket[cursors[index]])
            cursors[index] += 1
            progressed = True
            if len(merged) >= limit:
                break
        if not progressed:
            break
    return tuple(merged)


def _apply_numeric_bounds(col: Any, bounds: tuple[AmountBound, ...]) -> list[Any]:
    clauses: list[Any] = []
    for b in bounds:
        if b.op == ">=":
            clauses.append(col >= b.value)
        elif b.op == "<=":
            clauses.append(col <= b.value)
        elif b.op == ">":
            clauses.append(col > b.value)
        elif b.op == "<":
            clauses.append(col < b.value)
        else:
            clauses.append(col == b.value)
    return clauses


def _apply_date_bounds(col: Any, bounds: tuple[DateBound, ...]) -> list[Any]:
    clauses: list[Any] = []
    for b in bounds:
        naive = b.instant.replace(tzinfo=None)
        if b.op == ">=":
            clauses.append(col >= naive)
        elif b.op == "<=":
            clauses.append(col <= naive)
        elif b.op == ">":
            clauses.append(col > naive)
        elif b.op == "<":
            clauses.append(col < naive)
        else:
            day_start = naive.replace(hour=0, minute=0, second=0, microsecond=0)
            clauses.append(and_(col >= day_start, col < day_start + timedelta(days=1)))
    return clauses


def _search_accounts(
    session: Session,
    *,
    owner_id: uuid.UUID,
    parts: GlobalSearchParts,
    account_id: uuid.UUID | None,
    limit: int,
) -> list[GlobalSearchHit]:
    want_active = False if parts.deleted_presence is True else True
    stmt = select(Accounts).where(Accounts.owner_id == owner_id, Accounts.active == want_active)
    if account_id is not None:
        stmt = stmt.where(Accounts.id == account_id)
    if parts.exact_id is not None:
        stmt = stmt.where(Accounts.id == parts.exact_id)
    if parts.currency:
        stmt = stmt.where(func.upper(Accounts.currency) == parts.currency)
    if parts.amount_bounds:
        val_col = func.coalesce(Accounts.current_value, Accounts.initial_value, 0)
        for clause in _apply_numeric_bounds(val_col, parts.amount_bounds):
            stmt = stmt.where(clause)
    if parts.date_bounds:
        for clause in _apply_date_bounds(Accounts.opened_at, parts.date_bounds):
            stmt = stmt.where(clause)
    for tok in parts.text_tokens:
        pat = f"%{tok}%"
        stmt = stmt.where(
            or_(
                Accounts.name.ilike(pat),
                Accounts.description.ilike(pat),
                cast(Accounts.account_kind, String).ilike(pat),
                cast(Accounts.ledger_side, String).ilike(pat),
                func.array_to_string(Accounts.tags, " ").ilike(pat),
            )
        )
    rows = session.scalars(stmt.order_by(Accounts.name.asc()).limit(limit)).all()
    hits: list[GlobalSearchHit] = []
    for acc in rows:
        kind_val = acc.account_kind.value if hasattr(acc.account_kind, "value") else str(acc.account_kind)
        side_val = acc.ledger_side.value if hasattr(acc.ledger_side, "value") else str(acc.ledger_side)
        bal = float(acc.current_value if acc.current_value is not None else (acc.initial_value or 0.0))
        hits.append(
            GlobalSearchHit(
                kind=KIND_ACCOUNT,
                id=acc.id,
                title=acc.name,
                subtitle=f"{kind_val} · {side_val} · {acc.currency}",
                occurred_at=acc.opened_at,
                status=kind_val,
                amount=round(bal, 2),
                currency=acc.currency,
                account_id=acc.id,
                flags=("inactive",) if not acc.active else (),
            )
        )
    return hits


def _search_transactions(
    session: Session,
    *,
    owner_id: uuid.UUID,
    parts: GlobalSearchParts,
    account_id: uuid.UUID | None,
    limit: int,
) -> list[GlobalSearchHit]:
    want_active = False if parts.deleted_presence is True else True
    stmt = select(Transactions).where(Transactions.owner_id == owner_id, Transactions.active == want_active)
    if account_id is not None:
        stmt = stmt.where(or_(Transactions.from_account_id == account_id, Transactions.to_account_id == account_id))
    if parts.exact_id is not None:
        stmt = stmt.where(Transactions.id == parts.exact_id)
    if parts.currency:
        stmt = stmt.where(func.upper(Transactions.currency) == parts.currency)
    if parts.amount_bounds:
        for clause in _apply_numeric_bounds(Transactions.amount, parts.amount_bounds):
            stmt = stmt.where(clause)
    if parts.date_bounds:
        for clause in _apply_date_bounds(Transactions.transaction_ts, parts.date_bounds):
            stmt = stmt.where(clause)
    for tok in parts.text_tokens:
        pat = f"%{tok}%"
        stmt = stmt.where(
            or_(
                Transactions.description.ilike(pat),
                Transactions.reference_number.ilike(pat),
                cast(Transactions.transaction_kind, String).ilike(pat),
                cast(Transactions.amount, String).ilike(pat),
                func.array_to_string(Transactions.tags, " ").ilike(pat),
            )
        )
    rows = session.scalars(stmt.order_by(Transactions.transaction_ts.desc()).limit(limit)).all()
    hits: list[GlobalSearchHit] = []
    for txn in rows:
        kind_val = txn.transaction_kind.value if hasattr(txn.transaction_kind, "value") else str(txn.transaction_kind)
        ref_part = f" · ref {txn.reference_number}" if txn.reference_number else ""
        tags_part = f" · {', '.join(txn.tags[:2])}" if txn.tags else ""
        hits.append(
            GlobalSearchHit(
                kind=KIND_TRANSACTION,
                id=txn.id,
                title=txn.description or f"{kind_val} transaction",
                subtitle=f"{kind_val}{ref_part}{tags_part}",
                occurred_at=txn.transaction_ts,
                status=kind_val,
                amount=round(float(txn.amount), 2),
                currency=txn.currency,
                account_id=txn.from_account_id or txn.to_account_id,
                flags=("wired_due",) if txn.template_id is not None else (),
            )
        )
    return hits


def _search_payment_dues(
    session: Session,
    *,
    owner_id: uuid.UUID,
    parts: GlobalSearchParts,
    account_id: uuid.UUID | None,
    limit: int,
) -> list[GlobalSearchHit]:
    want_active = False if parts.deleted_presence is True else True
    stmt = select(TransactionTemplates).where(
        TransactionTemplates.owner_id == owner_id, TransactionTemplates.active == want_active
    )
    if account_id is not None:
        stmt = stmt.where(TransactionTemplates.from_account_id == account_id)
    if parts.exact_id is not None:
        stmt = stmt.where(TransactionTemplates.id == parts.exact_id)
    if parts.amount_bounds:
        for clause in _apply_numeric_bounds(TransactionTemplates.planned_amount, parts.amount_bounds):
            stmt = stmt.where(clause)
    for tok in parts.text_tokens:
        pat = f"%{tok}%"
        stmt = stmt.where(
            or_(
                TransactionTemplates.name.ilike(pat),
                TransactionTemplates.description.ilike(pat),
                func.array_to_string(TransactionTemplates.tags, " ").ilike(pat),
            )
        )
    rows = session.scalars(
        stmt.order_by(TransactionTemplates.planned_day.asc(), TransactionTemplates.name.asc()).limit(limit)
    ).all()
    acct_ids = [r.from_account_id for r in rows if r.from_account_id is not None]
    currency_by_acc: dict[uuid.UUID, str] = {}
    if acct_ids:
        acc_rows = session.exec(
            select(Accounts.id, Accounts.currency).where(Accounts.id.in_(acct_ids), Accounts.owner_id == owner_id)
        ).all()
        currency_by_acc = {row[0]: row[1] for row in acc_rows}

    hits: list[GlobalSearchHit] = []
    for due in rows:
        cur = currency_by_acc.get(due.from_account_id, "COP") if due.from_account_id else "COP"
        if parts.currency and cur.upper() != parts.currency:
            continue
        sched = f"Due {due.due_date.isoformat()}" if due.due_date else f"Monthly · day {due.planned_day}"
        hits.append(
            GlobalSearchHit(
                kind=KIND_PAYMENT_DUE,
                id=due.id,
                title=due.name,
                subtitle=f"{sched}" + (f" · {due.description[:60]}" if due.description else ""),
                occurred_at=datetime.combine(due.due_date, time.min) if due.due_date else None,
                status="recurring" if due.due_date is None else "scheduled",
                amount=round(float(due.planned_amount), 2),
                currency=cur,
                account_id=due.from_account_id,
                flags=("auto_wired",) if due.tags else (),
            )
        )
    return hits


def _search_categories(
    session: Session,
    *,
    owner_id: uuid.UUID,
    parts: GlobalSearchParts,
    limit: int,
) -> list[GlobalSearchHit]:
    want_active = False if parts.deleted_presence is True else True
    stmt = select(Categories).where(
        or_(Categories.owner_id == owner_id, Categories.owner_id.is_(None)),
        Categories.active == want_active,
    )
    if parts.exact_id is not None:
        stmt = stmt.where(Categories.id == parts.exact_id)
    for tok in parts.text_tokens:
        pat = f"%{tok}%"
        stmt = stmt.where(
            or_(
                Categories.name.ilike(pat),
                Categories.description.ilike(pat),
                cast(Categories.category_kind, String).ilike(pat),
                func.array_to_string(Categories.tags, " ").ilike(pat),
            )
        )
    rows = session.scalars(stmt.order_by(Categories.name.asc()).limit(limit)).all()
    hits: list[GlobalSearchHit] = []
    for cat in rows:
        kind_val = cat.category_kind.value if hasattr(cat.category_kind, "value") else str(cat.category_kind)
        hits.append(
            GlobalSearchHit(
                kind=KIND_CATEGORY,
                id=cat.id,
                title=cat.name,
                subtitle=f"{kind_val}" + (" · global" if cat.owner_id is None else ""),
                status=kind_val,
                flags=("global",) if cat.owner_id is None else (),
            )
        )
    return hits


def _search_projections(
    session: Session,
    *,
    owner: UsersDTO,
    parts: GlobalSearchParts,
    account_id: uuid.UUID | None,
    limit: int,
) -> list[GlobalSearchHit]:
    configs: dict[str, dict[str, Any]] = dict((owner.preferences or {}).get("projection_configs") or {})
    if not configs:
        return []
    acc_uuids: list[uuid.UUID] = []
    for raw_id in configs:
        try:
            parsed = uuid.UUID(raw_id)
            if account_id is None or parsed == account_id:
                acc_uuids.append(parsed)
        except ValueError:
            continue
    if not acc_uuids:
        return []
    rows = session.scalars(
        select(Accounts).where(
            Accounts.owner_id == owner.id,
            Accounts.active == True,  # noqa: E712
            Accounts.id.in_(acc_uuids),
        )
    ).all()
    hits: list[GlobalSearchHit] = []
    for acc in rows:
        cfg = configs.get(str(acc.id), {})
        rate = cfg.get("annual_rate_pct") or cfg.get("annual_appreciation_pct")
        conv = cfg.get("rate_convention") or ("REAL_ESTATE" if "annual_appreciation_pct" in cfg else "CO_EA")
        hay = f"{acc.name} {conv} {cfg.get('investment_type', '')} {rate or ''}".lower()
        if parts.exact_id is not None and acc.id != parts.exact_id:
            continue
        if parts.currency and acc.currency.upper() != parts.currency:
            continue
        if any(tok.lower() not in hay for tok in parts.text_tokens):
            continue
        bal = float(acc.current_value if acc.current_value is not None else (acc.initial_value or 0.0))
        rate_str = f"{rate}% {conv}" if rate is not None else str(conv)
        hits.append(
            GlobalSearchHit(
                kind=KIND_PROJECTION,
                id=acc.id,
                title=f"{acc.name} — Projection",
                subtitle=f"{rate_str} · {acc.currency}",
                status=str(conv),
                amount=round(bal, 2),
                currency=acc.currency,
                account_id=acc.id,
            )
        )
        if len(hits) >= limit:
            break
    return hits


def search_everything(
    session: Session,
    *,
    owner: UsersDTO,
    q: str,
    kinds: Sequence[str] = (),
    account_id: uuid.UUID | None = None,
    limit: int = 20,
) -> GlobalSearchResult:
    """Execute owner-scoped holistic search across all requested/implied entity kinds."""
    if owner.id is None:
        return GlobalSearchResult(q=q.strip(), kinds=(), account_id=account_id, limit=limit, items=())

    parts = parse_global_search_query(q)
    has_filters = bool(parts.currency or parts.amount_bounds or parts.date_bounds or parts.deleted_presence is not None)
    if not parts.residual_q and parts.exact_id is None and not parts.kinds and not has_filters:
        return GlobalSearchResult(q=q.strip(), kinds=(), account_id=account_id, limit=limit, items=())

    requested = {k for k in kinds if k in SEARCH_KIND_SET}
    implied = set(parts.kinds)
    active_kinds = _resolve_kinds(requested=requested, implied=implied)
    capped_limit = max(1, min(limit, 50))
    per_kind_limit = max(6, capped_limit)

    buckets: list[Sequence[GlobalSearchHit]] = []
    for kind in active_kinds:
        if kind == KIND_ACCOUNT:
            buckets.append(
                _search_accounts(session, owner_id=owner.id, parts=parts, account_id=account_id, limit=per_kind_limit)
            )
        elif kind == KIND_TRANSACTION:
            buckets.append(
                _search_transactions(
                    session, owner_id=owner.id, parts=parts, account_id=account_id, limit=per_kind_limit
                )
            )
        elif kind == KIND_PAYMENT_DUE:
            buckets.append(
                _search_payment_dues(
                    session, owner_id=owner.id, parts=parts, account_id=account_id, limit=per_kind_limit
                )
            )
        elif kind == KIND_CATEGORY and account_id is None:
            buckets.append(_search_categories(session, owner_id=owner.id, parts=parts, limit=per_kind_limit))
        elif kind == KIND_PROJECTION:
            buckets.append(
                _search_projections(session, owner=owner, parts=parts, account_id=account_id, limit=per_kind_limit)
            )

    merged = _interleave(buckets, capped_limit)
    return GlobalSearchResult(
        q=q.strip(),
        kinds=active_kinds,
        account_id=account_id,
        limit=capped_limit,
        items=merged,
    )

"""Owner-scoped account & category FK enrichment for parsed email records.

Resolves ``from_account_id``, ``to_account_id``, and ``category_id`` from the
owner's persisted ``parsing_rules`` plus live account/category lookups so
``IngestionBridgeService`` can upsert real ledger rows without ``IngestorValidationError``.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from papita_ingestor_core.types.records import ParsedRecord
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import TransactionKind

_FIXED_BILL_TAGS = frozenset({"rent", "aluna-hoa", "health", "ica", "visa-payment"})
_INTERNAL_NU_DEST_MARKERS = ("1017230391", "3016663962", "drh391", "cuenta nu")


def _parse_uuid(raw: Any) -> uuid.UUID | None:
    if isinstance(raw, uuid.UUID):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return uuid.UUID(raw.strip())
        except ValueError:
            return None
    return None


class EmailFKEnricher:
    """Resolve account and category foreign keys for email-ingested ``ParsedRecord`` items."""

    def __init__(
        self,
        *,
        parsing_rules: Sequence[dict[str, Any]] = (),
        accounts: Sequence[dict[str, Any]] = (),
        categories: Sequence[dict[str, Any]] = (),
    ) -> None:
        self._rules = [r for r in parsing_rules if r.get("enabled", True)]
        self._accounts = list(accounts)
        self._categories = list(categories)

    def _find_account_id(self, *needles: str) -> uuid.UUID | None:
        for needle in needles:
            low = needle.lower()
            for acc in self._accounts:
                name = str(acc.get("name") or "").lower()
                if low in name:
                    uid = _parse_uuid(acc.get("id"))
                    if uid is not None:
                        return uid
        return None

    def _find_category_id(self, kind: str, *needles: str) -> uuid.UUID | None:
        kind_u = kind.upper()
        for needle in needles:
            low = needle.lower()
            for cat in self._categories:
                if str(cat.get("category_kind") or "").upper() != kind_u:
                    continue
                name = str(cat.get("name") or "").lower()
                if low in name:
                    uid = _parse_uuid(cat.get("id"))
                    if uid is not None:
                        return uid
        # Fallback to first active category of matching kind
        for cat in self._categories:
            if str(cat.get("category_kind") or "").upper() == kind_u:
                uid = _parse_uuid(cat.get("id"))
                if uid is not None:
                    return uid
        return None

    def _rule_defaults(
        self, parser_mode: str, *, prefer_id_sub: str | None = None
    ) -> tuple[uuid.UUID | None, uuid.UUID | None]:
        matched = [r for r in self._rules if str(r.get("parser_mode") or "").lower() == parser_mode.lower()]
        if prefer_id_sub:
            for r in matched:
                if (
                    prefer_id_sub.lower() in str(r.get("id") or "").lower()
                    or prefer_id_sub.lower() in str(r.get("name") or "").lower()
                ):
                    return _parse_uuid(r.get("default_account_id")), _parse_uuid(r.get("default_category_id"))
        if matched:
            return _parse_uuid(matched[0].get("default_account_id")), _parse_uuid(matched[0].get("default_category_id"))
        return None, None

    def __call__(self, _owner: UsersDTO, parsed: ParsedRecord) -> ParsedRecord:
        tags = {str(t).lower() for t in (parsed.tags or ())}
        desc_low = (parsed.description or "").lower()
        kind = parsed.transaction_kind

        bc_acc = self._find_account_id("savings account bancolombia", "bancolombia")
        fidu_acc = self._find_account_id("fiduciary bancolombia", "fiducuenta")
        nu_acc = self._find_account_id("cuenta nu (drh391)", "cuenta nu")
        nu_emerg = self._find_account_id("emergency fund nu")
        nu_travel = self._find_account_id("travel fund nu")
        g66_acc = self._find_account_id("global66")
        ibkr_acc = self._find_account_id("ibkr cash")

        # Determine primary parser mode & default rule account/category
        if "nu" in tags:
            rule_acc, rule_cat = self._rule_defaults("nu-email")
            primary_acc = nu_acc or rule_acc
        elif "global66" in tags:
            rule_acc, rule_cat = self._rule_defaults("global66-email")
            primary_acc = g66_acc or rule_acc
        elif "nequi" in tags:
            rule_acc, rule_cat = self._rule_defaults("nequi-email")
            primary_acc = rule_acc or bc_acc
        else:
            prefer = "payroll" if "payroll" in tags else ("rent" if tags & _FIXED_BILL_TAGS else None)
            rule_acc, rule_cat = self._rule_defaults("bancolombia-email", prefer_id_sub=prefer)
            primary_acc = bc_acc or rule_acc

        from_id = parsed.from_account_id
        to_id = parsed.to_account_id
        cat_id = parsed.category_id

        if kind == TransactionKind.INCOME:
            if "cdt-yield" in tags:
                if "cajita:emergency" in tags and nu_emerg:
                    to_id = to_id or nu_emerg
                elif "cajita:travel" in tags and nu_travel:
                    to_id = to_id or nu_travel
                else:
                    to_id = to_id or nu_acc or primary_acc
                cat_id = cat_id or self._find_category_id("INCOME", "variable income", "non-operating")
            elif "payroll" in tags:
                to_id = to_id or bc_acc or primary_acc
                cat_id = cat_id or self._find_category_id("INCOME", "salary", "fixed income")
            else:
                to_id = to_id or primary_acc
                cat_id = cat_id or self._find_category_id("INCOME", "variable income", "non-operating")
            from_id = None

        elif kind == TransactionKind.TRANSFER:
            cat_id = None
            if "fiducuenta" in tags and fidu_acc and bc_acc:
                from_id = from_id or fidu_acc
                to_id = to_id or bc_acc
            elif "global66" in tags and "international_wire" in tags and g66_acc and ibkr_acc:
                from_id = from_id or g66_acc
                to_id = to_id or ibkr_acc
            elif "global66-funding" in tags and nu_acc and g66_acc:
                from_id = from_id or nu_acc
                to_id = to_id or g66_acc
            elif any(m in desc_low for m in _INTERNAL_NU_DEST_MARKERS) and bc_acc and nu_acc:
                from_id = from_id or bc_acc
                to_id = to_id or nu_acc
            else:
                # External transfer without a second internal account -> book as EXPENSE
                kind = TransactionKind.EXPENSE
                from_id = from_id or primary_acc
                to_id = None
                cat_id = self._find_category_id("EXPENSE", "variable spending", "unexpected")

        if kind == TransactionKind.EXPENSE:
            from_id = from_id or primary_acc
            to_id = None
            if tags & _FIXED_BILL_TAGS:
                cat_id = cat_id or self._find_category_id("EXPENSE", "fixed bills", "subscriptions")
            elif "loan-repayment" in tags:
                cat_id = cat_id or self._find_category_id("EXPENSE", "loan payments")
            else:
                # Ensure chosen category is actually an EXPENSE category
                exp_cat_ids = {
                    _parse_uuid(c.get("id"))
                    for c in self._categories
                    if str(c.get("category_kind") or "").upper() == "EXPENSE"
                }
                if cat_id not in exp_cat_ids:
                    cat_id = (
                        rule_cat if rule_cat in exp_cat_ids else self._find_category_id("EXPENSE", "variable spending")
                    )

        return parsed.model_copy(
            update={
                "transaction_kind": kind,
                "from_account_id": from_id,
                "to_account_id": to_id,
                "category_id": cat_id,
            }
        )


__all__ = ["EmailFKEnricher"]

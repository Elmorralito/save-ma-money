"""PPT-044 client-contract discovery and migration helpers.

Hardens wire-breaking security defaults by making them **discoverable**,
**machine-addressable**, and **temporarily reversible** via explicit settings
(never by silently weakening production CORS/docs).

Key exports:
    HEADER_*: Response header names for contract discovery and error codes.
    ERROR_*: Stable error codes for PPT-044 validation / tenancy changes.
    contract_discovery_headers: Headers attached to ``/api/v1`` responses.
    build_client_contract: Snapshot used by ``GET /meta/client-contract``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from papita_txnsapi.config.settings import Settings

# Discovery / migration headers (safe for browsers and SDKs to cache briefly).
HEADER_BREAKING_CHANGES = "X-Papita-Breaking-Changes"
HEADER_BULK_MAX = "X-Papita-Bulk-Max"
HEADER_REPORT_WINDOW_MAX_DAYS = "X-Papita-Report-Window-Max-Days"
HEADER_REFRESH_BALANCES_DEFAULT = "X-Papita-Cash-Flow-Refresh-Default"
HEADER_REPORTS_FOREIGN_ACCOUNT_STATUS = "X-Papita-Reports-Foreign-Account-Status"
HEADER_ERROR_CODE = "X-Papita-Error-Code"
HEADER_COMPAT_ACTIVE = "X-Papita-Compat-Active"
HEADER_DEPRECATION = "Deprecation"
HEADER_SUNSET = "Sunset"

BREAKING_CHANGES_ID = "ppt-044"

# Stable machine codes (also documented on GET /meta/client-contract).
ERROR_REPORT_ACCOUNT_NOT_FOUND = "report_account_not_found"
ERROR_REPORT_WINDOW_TOO_LARGE = "report_window_too_large"
ERROR_BULK_TOO_LARGE = "bulk_too_large"
ERROR_EXTRA_FIELDS_FORBIDDEN = "extra_fields_forbidden"
ERROR_INVALID_REQUEST = "invalid_request"
ERROR_IDEMPOTENCY_BODY_MISMATCH = "idempotency_body_mismatch"
ERROR_EMAIL_NOT_CONFIRMED = "email_not_confirmed"

# Optional temporary legacy behaviors (settings-gated; emit Deprecation when used).
COMPAT_LEGACY_REPORT_ACCOUNT_400 = "legacy_report_account_400"
COMPAT_LEGACY_REFRESH_BALANCES_DEFAULT_TRUE = "legacy_refresh_balances_default_true"

# RFC 8594-style sunset hint for temporary compat flags (operators should remove before).
COMPAT_SUNSET_DATE = "2026-10-01"


def reports_foreign_account_status(settings: Settings) -> int:
    """HTTP status for foreign ``account_id`` on report routes.

    Args:
        settings: Application settings with optional PPT-044 compat flags.

    Returns:
        ``400`` when legacy compat is enabled; otherwise ``404`` (CRUD parity).
    """
    if settings.API_COMPAT_LEGACY_REPORT_ACCOUNT_400:
        return 400
    return 404


def cash_flow_refresh_balances_default(settings: Settings) -> bool:
    """Default for omitted ``refresh_balances`` on cash-flow reports.

    Args:
        settings: Application settings with optional PPT-044 compat flags.

    Returns:
        ``True`` only when the temporary legacy-default compat flag is enabled.
    """
    return bool(settings.API_COMPAT_LEGACY_REFRESH_BALANCES_DEFAULT_TRUE)


def active_compat_flags(settings: Settings) -> list[str]:
    """Return enabled temporary compat flag names for headers and discovery.

    Args:
        settings: Application settings.

    Returns:
        Sorted list of active compat identifiers (empty when on secure defaults).
    """
    flags: list[str] = []
    if settings.API_COMPAT_LEGACY_REPORT_ACCOUNT_400:
        flags.append(COMPAT_LEGACY_REPORT_ACCOUNT_400)
    if settings.API_COMPAT_LEGACY_REFRESH_BALANCES_DEFAULT_TRUE:
        flags.append(COMPAT_LEGACY_REFRESH_BALANCES_DEFAULT_TRUE)
    return flags


def contract_discovery_headers(settings: Settings) -> dict[str, str]:
    """Build response headers advertising PPT-044 client contract limits.

    Args:
        settings: Application settings.

    Returns:
        Header map safe to attach to ``/api/v1`` responses.
    """
    headers = {
        HEADER_BREAKING_CHANGES: BREAKING_CHANGES_ID,
        HEADER_BULK_MAX: str(settings.API_BULK_MAX_TRANSACTIONS),
        HEADER_REPORT_WINDOW_MAX_DAYS: str(settings.API_REPORT_WINDOW_MAX_DAYS),
        HEADER_REFRESH_BALANCES_DEFAULT: "true" if cash_flow_refresh_balances_default(settings) else "false",
        HEADER_REPORTS_FOREIGN_ACCOUNT_STATUS: str(reports_foreign_account_status(settings)),
    }
    flags = active_compat_flags(settings)
    if flags:
        headers[HEADER_COMPAT_ACTIVE] = ",".join(flags)
        headers[HEADER_DEPRECATION] = "true"
        headers[HEADER_SUNSET] = COMPAT_SUNSET_DATE
    return headers


def build_client_contract(settings: Settings) -> dict[str, Any]:
    """Build the JSON body for ``GET /api/v1/meta/client-contract``.

    Args:
        settings: Application settings.

    Returns:
        Discoverable contract snapshot for SDKs and migration checklists.
    """
    compat = active_compat_flags(settings)
    return {
        "breaking_changes": BREAKING_CHANGES_ID,
        "api_version": settings.APP_VERSION,
        "secure_defaults": {
            "reports_foreign_account_status": 404,
            "cash_flow_refresh_balances_default": False,
            "bulk_max_transactions": settings.API_BULK_MAX_TRANSACTIONS,
            "report_window_max_days": settings.API_REPORT_WINDOW_MAX_DAYS,
            "docs_require_debug_or_docs_enabled": True,
            "cors_wildcard_forbidden_when_not_debug": True,
        },
        "effective": {
            "reports_foreign_account_status": reports_foreign_account_status(settings),
            "cash_flow_refresh_balances_default": cash_flow_refresh_balances_default(settings),
            "bulk_max_transactions": settings.API_BULK_MAX_TRANSACTIONS,
            "report_window_max_days": settings.API_REPORT_WINDOW_MAX_DAYS,
            "docs_enabled": bool(settings.DEBUG or settings.DOCS_ENABLED),
        },
        "compat": {
            "active": compat,
            "sunset": COMPAT_SUNSET_DATE if compat else None,
            "flags": {
                "API_COMPAT_LEGACY_REPORT_ACCOUNT_400": {
                    "enabled": settings.API_COMPAT_LEGACY_REPORT_ACCOUNT_400,
                    "effect": "Foreign report account_id returns HTTP 400 instead of 404",
                },
                "API_COMPAT_LEGACY_REFRESH_BALANCES_DEFAULT_TRUE": {
                    "enabled": settings.API_COMPAT_LEGACY_REFRESH_BALANCES_DEFAULT_TRUE,
                    "effect": "Omitted refresh_balances on cash-flow defaults to true",
                },
            },
        },
        "error_codes": {
            ERROR_REPORT_ACCOUNT_NOT_FOUND: "Foreign or unknown account_id on report routes",
            ERROR_REPORT_WINDOW_TOO_LARGE: "Report start/end span exceeds max days",
            ERROR_BULK_TOO_LARGE: "Bulk create exceeds max item count",
            ERROR_EXTRA_FIELDS_FORBIDDEN: "Write/auth body included unknown fields",
            ERROR_INVALID_REQUEST: "Masked/unsafe ValueError detail",
            ERROR_IDEMPOTENCY_BODY_MISMATCH: "Idempotency-Key reused with a different request body",
        },
        "migration": {
            "probe": "GET /api/v1/meta/client-contract",
            "prefer_headers": [
                HEADER_BULK_MAX,
                HEADER_REPORT_WINDOW_MAX_DAYS,
                HEADER_REFRESH_BALANCES_DEFAULT,
                HEADER_REPORTS_FOREIGN_ACCOUNT_STATUS,
                HEADER_ERROR_CODE,
            ],
            "client_checklist": [
                "Treat report foreign account_id as 404 (unless compat 400 enabled)",
                "Pass refresh_balances=true explicitly when MV refresh is required",
                f"Chunk bulk creates to <= {settings.API_BULK_MAX_TRANSACTIONS} items",
                f"Keep report windows <= {settings.API_REPORT_WINDOW_MAX_DAYS} days",
                "Fetch OpenAPI offline or enable DOCS_ENABLED in non-prod only",
                "Configure explicit ALLOWED_ORIGINS (never * in production)",
            ],
        },
    }


def error_code_for_value_error(message: str) -> str | None:
    """Map known domain ValueError messages to stable PPT-044 error codes.

    Args:
        message: ``str(exc)`` from a domain ``ValueError``.

    Returns:
        Error code string, or ``None`` when no stable code applies.
    """
    if message == "Account not found for tenant.":
        return ERROR_REPORT_ACCOUNT_NOT_FOUND
    if message.startswith("report window must be at most"):
        return ERROR_REPORT_WINDOW_TOO_LARGE
    return None


def error_code_for_validation_errors(errors: list[Any]) -> str | None:
    """Derive a PPT-044 error code from a Pydantic/FastAPI validation error list.

    Args:
        errors: ``RequestValidationError.errors()`` payload.

    Returns:
        Matching error code, or ``None``.
    """
    for item in errors:
        if not isinstance(item, dict):
            continue
        loc = item.get("loc") or ()
        msg = str(item.get("msg") or "").lower()
        typ = str(item.get("type") or "").lower()
        if "transactions" in loc and ("max_length" in typ or "at most" in msg):
            return ERROR_BULK_TOO_LARGE
        if typ == "extra_forbidden" or "extra" in typ:
            return ERROR_EXTRA_FIELDS_FORBIDDEN
    return None

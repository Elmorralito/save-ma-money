"""Ingestion connection and run-status routes — PPT-083 / #177.

Read-only status APIs under ``/ingestion``. Handlers require JWT auth via
``get_current_owner`` and delegate to model services. Workers (Prefect email
flow) own writes; this router never triggers runs or exposes OAuth/DLQ secrets.

Routes:
    ``GET /ingestion/connections`` — paginated non-secret connection metadata.
    ``GET /ingestion/connections/{connection_id}`` — single connection.
    ``GET /ingestion/runs/latest`` — most recently started run.
    ``GET /ingestion/runs`` — paginated recent runs (optional ``connection_id``).

Tenant scoping:
    Cross-tenant ids resolve as 404 (not 403). Unauthenticated requests → 401.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Annotated

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from redis import Redis

from papita_ingestor_core.errors import IngestorParseError, IngestorPluginError
from papita_ingestor_core.plugins import PluginKind
from papita_ingestor_core.registry import get_default_registry
from papita_ingestor_core.types.records import RawRecord
from papita_ingestor_email.parsers.bancolombia import BancolombiaParser
from papita_ingestor_email.parsers.global66 import Global66Parser
from papita_ingestor_email.parsers.nequi import NequiParser
from papita_ingestor_email.parsers.nu import NuParser
from papita_ingestor_email.parsers.security import redact_sensitive_text
from papita_txnsapi.config.settings import Settings, get_settings
from papita_txnsapi.core.cache import CacheNamespace, bump_cache_versions
from papita_txnsapi.core.oauth_txns import consume_oauth_txn, store_oauth_txn
from papita_txnsapi.dependencies.auth import get_current_owner
from papita_txnsapi.dependencies.pagination import PaginationParams, get_pagination
from papita_txnsapi.dependencies.rate_limit import enforce_tenant_api_rate_limit
from papita_txnsapi.dependencies.redis import get_optional_redis
from papita_txnsapi.dependencies.services import (
    get_ibkr_import_service,
    get_ingestion_connection_service,
    get_ingestion_run_service,
    get_portfolio_import_service,
    get_users_service,
)
from papita_txnsapi.schemas.common import PaginatedResponse
from papita_txnsapi.schemas.converters import enum_to_api_slug
from papita_txnsapi.schemas.ingestion import (
    ConnectorManifestResponse,
    EmailParseTestRequest,
    EmailParseTestResponse,
    EmailParsingRuleSchema,
    IBKRImportRequest,
    IBKRImportResponse,
    IngestionConnectionResponse,
    IngestionConnectionUpdateRequest,
    IngestionConnectionUpsertRequest,
    IngestionRunResponse,
)
from papita_txnsmodel.access.ingestion.dto import IngestionRunDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.model.enums import IngestionSource
from papita_txnsmodel.services.ibkr_import import IBKRImportService
from papita_txnsmodel.services.ingestion_status import (
    IngestionConnectionService,
    IngestionRunService,
    UpdateIngestionConnectionRequest,
    UpsertIngestionConnectionRequest,
)
from papita_txnsmodel.services.portfolio_import import PortfolioImportService
from papita_txnsmodel.services.users import UsersService

logger = logging.getLogger(__name__)

_GMAIL_OAUTH_COOKIE_PATH = "/api/v1/ingestion/gmail"
_GMAIL_OAUTH_CV_COOKIE = "papita_gmail_cv"
_GMAIL_OAUTH_STATE_COOKIE = "papita_gmail_state"
_GMAIL_OAUTH_OWNER_COOKIE = "papita_gmail_owner"
_GMAIL_OAUTH_REDIRECT_COOKIE = "papita_gmail_rt"
_GMAIL_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GMAIL_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
_GMAIL_SCOPES = "openid email https://www.googleapis.com/auth/gmail.modify"
_GENERIC_AMOUNT_RE = re.compile(r"(?:US\$|COP\$|\$)\s*([\d.,]+)")

router = APIRouter(
    prefix="/ingestion",
    tags=["Ingestion"],
    dependencies=[Depends(enforce_tenant_api_rate_limit)],
)


def _connection_not_found() -> HTTPException:
    """Build a 404 that avoids leaking cross-tenant connection existence."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion connection not found")


def _run_not_found() -> HTTPException:
    """Build a 404 that avoids leaking cross-tenant run existence."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion run not found")


def _run_filter_dto(connection_id: uuid.UUID | None) -> IngestionRunDTO | None:
    """Build a partial filter DTO for run list/count when ``connection_id`` is set."""
    if connection_id is None:
        return None
    return IngestionRunDTO.model_construct(connection_id=connection_id)


@router.get("/connections", response_model=PaginatedResponse[IngestionConnectionResponse])
def list_ingestion_connections(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    connection_service: Annotated[IngestionConnectionService, Depends(get_ingestion_connection_service)],
) -> PaginatedResponse[IngestionConnectionResponse]:
    """List non-secret ingestion connections for the authenticated owner.

    Args:
        owner: Authenticated tenant from JWT.
        pagination: Skip/limit window for the response page.
        connection_service: Injected connection status service.

    Returns:
        Paginated allowlisted connection resources.
    """
    total = connection_service.count_records(dto=None, owner=owner)
    rows = connection_service.list_connections(
        owner=owner,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    return PaginatedResponse(
        items=[IngestionConnectionResponse.from_dto(row) for row in rows],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.put("/connections", response_model=IngestionConnectionResponse)
def upsert_ingestion_connection(
    payload: IngestionConnectionUpsertRequest,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    connection_service: Annotated[IngestionConnectionService, Depends(get_ingestion_connection_service)],
) -> IngestionConnectionResponse:
    """Create or update an owner-scoped ingestion connection and its channel filters.

    Args:
        payload: Non-secret connection and email channel filter configuration.
        owner: Authenticated tenant from JWT.
        connection_service: Injected connection service.

    Returns:
        Saved allowlisted connection resource.
    """
    saved = connection_service.upsert_connection(
        owner=owner,
        request=UpsertIngestionConnectionRequest(**payload.model_dump(mode="json")),
    )
    return IngestionConnectionResponse.from_dto(saved)


@router.get("/connections/{connection_id}", response_model=IngestionConnectionResponse)
def get_ingestion_connection(
    connection_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    connection_service: Annotated[IngestionConnectionService, Depends(get_ingestion_connection_service)],
) -> IngestionConnectionResponse:
    """Return one connection when owned by the caller; else 404.

    Args:
        connection_id: Connection primary key.
        owner: Authenticated tenant from JWT.
        connection_service: Injected connection status service.

    Returns:
        Allowlisted connection resource.
    """
    connection = connection_service.get_connection(owner=owner, connection_id=connection_id)
    if connection is None:
        raise _connection_not_found()
    return IngestionConnectionResponse.from_dto(connection)


@router.patch("/connections/{connection_id}", response_model=IngestionConnectionResponse)
def update_ingestion_connection(
    connection_id: uuid.UUID,
    payload: IngestionConnectionUpdateRequest,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    connection_service: Annotated[IngestionConnectionService, Depends(get_ingestion_connection_service)],
) -> IngestionConnectionResponse:
    """Partially update channel filters or schedule settings on an owned connection.

    Args:
        connection_id: Connection primary key.
        payload: Partial fields to update (unset fields are left unchanged).
        owner: Authenticated tenant from JWT.
        connection_service: Injected connection service.

    Returns:
        Updated allowlisted connection resource.
    """
    service_request = UpdateIngestionConnectionRequest(**payload.model_dump(exclude_unset=True, mode="json"))
    updated = connection_service.update_connection(
        owner=owner,
        connection_id=connection_id,
        request=service_request,
    )
    if updated is None:
        raise _connection_not_found()
    return IngestionConnectionResponse.from_dto(updated)


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingestion_connection(
    connection_id: uuid.UUID,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    connection_service: Annotated[IngestionConnectionService, Depends(get_ingestion_connection_service)],
) -> None:
    """Disable and soft-delete an owner-scoped connection; returns 404 if not owned."""
    deleted = connection_service.delete_connection(owner=owner, connection_id=connection_id)
    if not deleted:
        raise _connection_not_found()


@router.get("/runs/latest", response_model=IngestionRunResponse)
def get_latest_ingestion_run(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    run_service: Annotated[IngestionRunService, Depends(get_ingestion_run_service)],
    connection_id: Annotated[
        uuid.UUID | None,
        Query(description="Optional connection filter for the latest run"),
    ] = None,
) -> IngestionRunResponse:
    """Return the most recently started run for the owner.

    Args:
        owner: Authenticated tenant from JWT.
        run_service: Injected run status service.
        connection_id: Optional filter to a single connection.

    Returns:
        Allowlisted run resource.

    Raises:
        HTTPException: 404 when no runs exist for the scope.
    """
    run = run_service.get_latest_run(owner=owner, connection_id=connection_id)
    if run is None:
        raise _run_not_found()
    return IngestionRunResponse.from_dto(run)


@router.get("/runs", response_model=PaginatedResponse[IngestionRunResponse])
def list_ingestion_runs(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    run_service: Annotated[IngestionRunService, Depends(get_ingestion_run_service)],
    connection_id: Annotated[
        uuid.UUID | None,
        Query(description="Optional filter by connection id"),
    ] = None,
) -> PaginatedResponse[IngestionRunResponse]:
    """List recent ingestion runs for the authenticated owner.

    Args:
        owner: Authenticated tenant from JWT.
        pagination: Skip/limit window for the response page.
        run_service: Injected run status service.
        connection_id: Optional filter by connection id.

    Returns:
        Paginated allowlisted run resources, newest first.
    """
    filter_dto = _run_filter_dto(connection_id)
    total = run_service.count_records(dto=filter_dto, owner=owner)
    rows = run_service.list_runs(
        owner=owner,
        connection_id=connection_id,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    return PaginatedResponse(
        items=[IngestionRunResponse.from_dto(row) for row in rows],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.post("/ibkr/activity-statement", response_model=IBKRImportResponse)
def import_ibkr_activity_statement(
    payload: IBKRImportRequest,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    import_service: Annotated[IBKRImportService, Depends(get_ibkr_import_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
) -> IBKRImportResponse:
    """Import an Interactive Brokers Activity Statement CSV idempotently (PPT-101 / #262)."""
    try:
        result = import_service.import_activity_statement(
            owner=owner,
            csv_text=payload.csv_content,
            fx_rate=payload.fx_rate,
            base_currency=payload.base_currency,
            cash_account_id=payload.cash_account_id,
            margin_account_id=payload.margin_account_id,
            source_account_id=payload.source_account_id,
            create_missing_accounts=payload.create_missing_accounts,
        )
    except (IngestorParseError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    bump_cache_versions(
        redis,
        owner.id,
        CacheNamespace.TRANSACTIONS,
        CacheNamespace.REPORTS,
        CacheNamespace.ACCOUNTS,
    )
    return IBKRImportResponse.model_validate(result.model_dump(mode="python"))


@router.post("/statements/{importer_id}", response_model=IBKRImportResponse)
def import_statement_by_plugin(
    importer_id: str,
    payload: IBKRImportRequest,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    portfolio_service: Annotated[PortfolioImportService, Depends(get_portfolio_import_service)],
    redis: Annotated[Redis | None, Depends(get_optional_redis)],
) -> IBKRImportResponse:
    """Import a broker/statement payload via any registered ``BaseBatchImporter`` plugin."""
    try:
        importer = get_default_registry().get_importer(importer_id)
    except IngestorPluginError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown statement importer: {importer_id}",
        ) from exc

    try:
        batch = importer.parse_statement(payload.csv_content)
        result = portfolio_service.import_batch(
            owner=owner,
            batch=batch,
            fx_rate=payload.fx_rate,
            base_currency=payload.base_currency,
            cash_account_id=payload.cash_account_id,
            margin_account_id=payload.margin_account_id,
            source_account_id=payload.source_account_id,
            create_missing_accounts=payload.create_missing_accounts,
        )
    except (IngestorParseError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    bump_cache_versions(
        redis,
        owner.id,
        CacheNamespace.TRANSACTIONS,
        CacheNamespace.REPORTS,
        CacheNamespace.ACCOUNTS,
    )
    return IBKRImportResponse.model_validate(result.model_dump(mode="python"))


_GMAIL_REVOKE_URL = "https://oauth2.googleapis.com/revoke"


def _fernet_for_settings(settings: Settings) -> MultiFernet:
    """Build domain-separated Fernet encryption for per-user Gmail refresh tokens.

    Prefers dedicated ``GMAIL_TOKEN_ENCRYPTION_KEY`` when configured; otherwise
    derives a purpose-bound key via HKDF-SHA256 from ``JWT_SECRET_KEY``. Retains
    the legacy SHA-256 key as a decryption-only fallback for seamless rotation.
    """
    primary_ikm = (settings.GMAIL_TOKEN_ENCRYPTION_KEY or settings.JWT_SECRET_KEY).encode("utf-8")
    hkdf_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"papita-gmail-oauth-v1",
        info=b"papita:gmail-refresh-token:v1",
    ).derive(primary_ikm)
    primary = Fernet(base64.urlsafe_b64encode(hkdf_key))
    legacy_digest = hashlib.sha256(settings.JWT_SECRET_KEY.encode("utf-8")).digest()
    legacy = Fernet(base64.urlsafe_b64encode(legacy_digest))
    return MultiFernet([primary, legacy])


def _revoke_google_token_best_effort(refresh_token: str) -> None:
    """Best-effort revocation of a Gmail OAuth refresh token at Google's revoke endpoint."""
    try:
        body = urllib.parse.urlencode({"token": refresh_token}).encode("utf-8")
        req = urllib.request.Request(
            _GMAIL_REVOKE_URL,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10):  # nosec B310 - fixed Google revoke URL
            return
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("Best-effort Google token revocation failed: %s", redact_sensitive_text(str(exc)))


def _clear_gmail_oauth_cookies(response: RedirectResponse) -> None:
    for key in (
        _GMAIL_OAUTH_CV_COOKIE,
        _GMAIL_OAUTH_STATE_COOKIE,
        _GMAIL_OAUTH_OWNER_COOKIE,
        _GMAIL_OAUTH_REDIRECT_COOKIE,
    ):
        response.delete_cookie(key=key, path=_GMAIL_OAUTH_COOKIE_PATH)


def _seal_gmail_oauth_txn(
    settings: Settings,
    *,
    owner_id: str,
    state: str,
    code_verifier: str,
    callback_uri: str,
) -> str:
    """Cryptographically seal Gmail OAuth context to prevent owner_id cookie tampering (IDOR)."""
    payload = json.dumps(
        {
            "owner_id": owner_id,
            "state": state,
            "code_verifier": code_verifier,
            "callback_uri": callback_uri,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    return _fernet_for_settings(settings).encrypt(payload).decode("ascii")


def _unseal_gmail_oauth_txn(settings: Settings, token: str | None) -> dict[str, str] | None:
    """Verify and decrypt the sealed Gmail OAuth transaction cookie (10-minute TTL)."""
    if not token:
        return None
    try:
        raw = _fernet_for_settings(settings).decrypt(token.encode("ascii"), ttl=600)
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            return None
        return {k: str(v) for k, v in data.items() if isinstance(v, str)}
    except (InvalidToken, ValueError, json.JSONDecodeError):
        return None


def _parse_amount_number(raw: str) -> float | None:
    cleaned = raw.strip().replace(" ", "")
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts[-1]) == 2:
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
        else:
            cleaned = cleaned.replace(",", "")
    try:
        val = float(cleaned)
        return val if val > 0 else None
    except ValueError:
        return None


@router.get("/gmail/oauth/start", response_model=None)
def start_gmail_oauth(
    request: Request,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedirectResponse:
    """Start per-user incremental Gmail OAuth flow (``gmail.modify`` scope)."""
    client_id = (settings.GOOGLE_OAUTH_CLIENT_ID or "").strip()
    client_secret = (settings.GOOGLE_OAUTH_CLIENT_SECRET or "").strip()
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth client credentials are not configured on the API server.",
        )

    base = str(request.base_url).rstrip("/")
    callback_uri = f"{base}/api/v1/ingestion/gmail/oauth/callback"
    code_verifier = secrets.token_urlsafe(48)
    state = secrets.token_urlsafe(24)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    params = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": callback_uri,
            "response_type": "code",
            "scope": _GMAIL_SCOPES,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": "consent",
            "login_hint": owner.email,
        }
    )
    response = RedirectResponse(url=f"{_GMAIL_AUTH_URL}?{params}", status_code=status.HTTP_302_FOUND)
    cookie_kwargs = {
        "max_age": 600,
        "httponly": True,
        "samesite": "lax",
        "secure": settings.oauth_cookie_secure(),
        "path": _GMAIL_OAUTH_COOKIE_PATH,
    }
    flow_handle = str(uuid.uuid4())
    store_oauth_txn(
        flow_handle,
        {
            "owner_id": str(owner.id),
            "state": state,
            "code_verifier": code_verifier,
            "callback_uri": callback_uri,
        },
        ttl_seconds=600,
    )
    response.set_cookie(key=_GMAIL_OAUTH_STATE_COOKIE, value=flow_handle, **cookie_kwargs)
    return response


@router.get("/gmail/oauth/callback", response_model=None)
def gmail_oauth_callback(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    connection_service: Annotated[IngestionConnectionService, Depends(get_ingestion_connection_service)],
    users_service: Annotated[UsersService, Depends(get_users_service)],
    *,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Complete per-user Gmail OAuth and store encrypted refresh token on ingestion_connections."""
    txn = consume_oauth_txn(request.cookies.get(_GMAIL_OAUTH_STATE_COOKIE))
    expected_state = txn.get("state") if txn else None
    code_verifier = txn.get("code_verifier") if txn else None
    owner_raw = txn.get("owner_id") if txn else None
    callback_uri = txn.get("callback_uri") if txn else None
    if (
        error
        or not code
        or not code_verifier
        or not expected_state
        or not state
        or not secrets.compare_digest(state, expected_state)
        or not owner_raw
    ):
        failed = RedirectResponse(url="/settings?tab=integrations&gmail=error", status_code=status.HTTP_302_FOUND)
        _clear_gmail_oauth_cookies(failed)
        return failed

    try:
        owner = users_service.get_owner(uuid.UUID(owner_raw))
        if owner is None:
            raise ValueError("Owner not found")
        token_body = urllib.parse.urlencode(
            {
                "client_id": (settings.GOOGLE_OAUTH_CLIENT_ID or "").strip(),
                "client_secret": (settings.GOOGLE_OAUTH_CLIENT_SECRET or "").strip(),
                "code": code,
                "code_verifier": code_verifier,
                "redirect_uri": callback_uri
                or f"{str(request.base_url).rstrip('/')}/api/v1/ingestion/gmail/oauth/callback",
                "grant_type": "authorization_code",
            }
        ).encode("utf-8")
        token_req = urllib.request.Request(
            _GMAIL_TOKEN_URL,
            data=token_body,
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(token_req, timeout=15) as resp:  # nosec B310 - fixed Google token URL
            token_payload = json.loads(resp.read().decode("utf-8"))

        access_token = str(token_payload.get("access_token") or "").strip()
        refresh_token = str(token_payload.get("refresh_token") or "").strip()
        if not refresh_token:
            raise ValueError("Google did not return a refresh_token")

        connected_email = owner.email
        if access_token:
            ui_req = urllib.request.Request(
                _GMAIL_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
                method="GET",
            )
            with urllib.request.urlopen(ui_req, timeout=15) as resp:  # nosec B310 - fixed Google userinfo URL
                ui = json.loads(resp.read().decode("utf-8"))
                if isinstance(ui, dict) and ui.get("email"):
                    connected_email = str(ui["email"]).strip().lower()

        encrypted = _fernet_for_settings(settings).encrypt(refresh_token.encode("utf-8")).decode("ascii")
        connection_service.set_gmail_credentials(
            owner=owner,
            connected_email=connected_email,
            encrypted_refresh_token=encrypted,
            access_enabled=True,
        )
        ok_resp = RedirectResponse(url="/settings?tab=integrations&gmail=connected", status_code=status.HTTP_302_FOUND)
        _clear_gmail_oauth_cookies(ok_resp)
        return ok_resp
    except (urllib.error.URLError, ValueError, KeyError, json.JSONDecodeError) as exc:
        logger.warning("Per-user Gmail OAuth callback failed: %s", redact_sensitive_text(str(exc)))
        failed = RedirectResponse(url="/settings?tab=integrations&gmail=error", status_code=status.HTTP_302_FOUND)
        _clear_gmail_oauth_cookies(failed)
        return failed


@router.post("/gmail/disconnect", response_model=IngestionConnectionResponse)
def disconnect_gmail(
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    settings: Annotated[Settings, Depends(get_settings)],
    connection_service: Annotated[IngestionConnectionService, Depends(get_ingestion_connection_service)],
) -> IngestionConnectionResponse:
    """Revoke Gmail OAuth refresh token at Google, wipe encrypted DB token, and disable access."""
    existing = connection_service.get_connection_by_natural_key(
        owner=owner,
        provider="email",
        flow_name="papita-email-ingestion",
    )
    if existing is not None and existing.gmail_refresh_token_enc:
        try:
            raw_token = (
                _fernet_for_settings(settings).decrypt(existing.gmail_refresh_token_enc.encode("ascii")).decode("utf-8")
            )
            if raw_token:
                _revoke_google_token_best_effort(raw_token)
        except InvalidToken:
            logger.warning("Could not decrypt stored Gmail token during disconnect for owner_id=%s", owner.id)

    updated = connection_service.set_gmail_credentials(
        owner=owner,
        connected_email=None,
        encrypted_refresh_token=None,
        access_enabled=False,
    )
    return IngestionConnectionResponse.from_dto(updated)


@router.post("/email/test-parse", response_model=EmailParseTestResponse)
def test_email_parse(
    payload: EmailParseTestRequest,
    owner: Annotated[UsersDTO, Depends(get_current_owner)],
    connection_service: Annotated[IngestionConnectionService, Depends(get_ingestion_connection_service)],
) -> EmailParseTestResponse:
    """Dry-run sample email against the user's configured parsing rules and built-in bank parsers."""
    rules: list[EmailParsingRuleSchema]
    if payload.rules is not None:
        rules = payload.rules
    else:
        existing = connection_service.list_connections(owner=owner, skip=0, limit=1)
        rules = [EmailParsingRuleSchema.model_validate(item) for item in existing[0].parsing_rules] if existing else []

    sender_l = payload.sender.strip().lower()
    subject_l = payload.subject.strip().lower()
    raw_record = RawRecord(
        source_id="gmail",
        ingestion_source=IngestionSource.EMAIL,
        source_ref="dry-run-test-parse",
        content=payload.body.encode("utf-8"),
        metadata={"sender": payload.sender.strip(), "subject": payload.subject.strip()},
    )
    builtin_parsers = {
        "bancolombia-email": BancolombiaParser(),
        "global66-email": Global66Parser(),
        "nequi-email": NequiParser(),
        "nu-email": NuParser(),
    }

    for rule in rules:
        if not rule.enabled:
            continue
        if rule.sender_match and rule.sender_match.lower() not in sender_l:
            continue
        if rule.subject_match and rule.subject_match.lower() not in subject_l:
            continue

        if rule.parser_mode in builtin_parsers:
            parser = builtin_parsers[rule.parser_mode]
            if parser.can_parse(raw_record):
                try:
                    parsed = parser.parse(raw_record)
                    return EmailParseTestResponse(
                        matched=True,
                        matched_rule_name=rule.name,
                        parser_used=rule.parser_mode,
                        transaction_type=(
                            rule.transaction_type
                            if rule.transaction_type != "auto"
                            else enum_to_api_slug(parsed.transaction_kind)
                        ),
                        amount=parsed.amount,
                        currency=parsed.currency or rule.currency,
                        description=rule.description_template or parsed.description,
                        default_account_id=rule.default_account_id,
                        default_category_id=rule.default_category_id,
                    )
                except IngestorParseError as exc:
                    return EmailParseTestResponse(
                        matched=False,
                        matched_rule_name=rule.name,
                        parser_used=rule.parser_mode,
                        error=str(exc),
                    )
            continue
        elif rule.parser_mode == "auto":
            for pid, parser in builtin_parsers.items():
                if parser.can_parse(raw_record):
                    try:
                        parsed = parser.parse(raw_record)
                        return EmailParseTestResponse(
                            matched=True,
                            matched_rule_name=rule.name,
                            parser_used=pid,
                            transaction_type=(
                                rule.transaction_type
                                if rule.transaction_type != "auto"
                                else enum_to_api_slug(parsed.transaction_kind)
                            ),
                            amount=parsed.amount,
                            currency=parsed.currency or rule.currency,
                            description=rule.description_template or parsed.description,
                            default_account_id=rule.default_account_id,
                            default_category_id=rule.default_category_id,
                        )
                    except IngestorParseError as exc:
                        return EmailParseTestResponse(
                            matched=False,
                            matched_rule_name=rule.name,
                            parser_used=pid,
                            error=str(exc),
                        )

        # Custom regex (or fallback for auto when sender/subject matched)
        regex_pattern = re.compile(rule.amount_regex) if rule.amount_regex else _GENERIC_AMOUNT_RE
        match = regex_pattern.search(f"{payload.subject}\n{payload.body}")
        if match:
            raw_amt = match.group(1) if match.lastindex else match.group(0)
            amount = _parse_amount_number(raw_amt)
            if amount is not None:
                return EmailParseTestResponse(
                    matched=True,
                    matched_rule_name=rule.name,
                    parser_used="custom_regex",
                    transaction_type="expense" if rule.transaction_type == "auto" else rule.transaction_type,
                    amount=amount,
                    currency=rule.currency,
                    description=rule.description_template or payload.subject.strip() or rule.name,
                    default_account_id=rule.default_account_id,
                    default_category_id=rule.default_category_id,
                )

    # Fallback: try built-in parsers even if no custom rule matched
    for pid, parser in builtin_parsers.items():
        if parser.can_parse(raw_record):
            try:
                parsed = parser.parse(raw_record)
                return EmailParseTestResponse(
                    matched=True,
                    matched_rule_name=None,
                    parser_used=pid,
                    transaction_type=enum_to_api_slug(parsed.transaction_kind),
                    amount=parsed.amount,
                    currency=parsed.currency,
                    description=parsed.description,
                )
            except IngestorParseError as exc:
                return EmailParseTestResponse(matched=False, parser_used=pid, error=str(exc))

    return EmailParseTestResponse(
        matched=False,
        error="No rule or built-in parser matched this email. Add a custom regex rule or check sender/subject.",
    )


@router.get("/connectors", response_model=list[ConnectorManifestResponse])
def list_registered_connectors(
    _owner: Annotated[UsersDTO, Depends(get_current_owner)],
    kind: Annotated[PluginKind | None, Query(description="Optional plugin kind filter")] = None,
) -> list[ConnectorManifestResponse]:
    """List non-secret manifests for all registered ingestion plugins."""
    manifests = get_default_registry().list_manifests(kind=kind)
    return [
        ConnectorManifestResponse(
            plugin_id=item.plugin_id,
            kind=item.kind,
            version=item.version,
            ingestion_source=enum_to_api_slug(item.ingestion_source),
            supported_media_types=list(item.supported_media_types),
            capabilities=sorted(item.capabilities),
            description=item.description,
        )
        for item in manifests
    ]

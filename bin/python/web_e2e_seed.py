#!/usr/bin/env python3
"""Seed deterministic E2E fixtures for Playwright (PPT-061 / #126).

Strategy A (locked): HTTP against a running Compose API using the Bearer token
path. Playwright (#121) still exercises BFF cookie login in the browser.

Requires ``make api-all`` (or equivalent). Default B0 path uses
``AUTH_PROVIDER=local``. For Supabase, set ``E2E_SKIP_REGISTER=1`` and provide
a pre-confirmed ``E2E_USER_EMAIL`` / ``E2E_USER_PASSWORD``.

Writes ``modules/web/e2e/.auth/seed.json`` (gitignored) for #121 consumers.

Reset semantics (``--reset`` / ``RESET=1``):
  soft-delete baseline E2E transactions and E2E-prefixed accounts, then recreate.
  Categories are **reused** (not soft-deleted) — recreating the same category name
  after soft-delete can yield a phantom 201 against the unique tombstone.
  Full tenant wipe: new ``E2E_USER_EMAIL`` or Compose volume reset.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


def resolve_repo_root() -> Path:
    """Walk upward from this file to the monorepo root."""
    here = Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "modules").is_dir():
            return candidate
    raise RuntimeError(f"Could not locate repo root from {Path(__file__).resolve()}")


REPO_ROOT = resolve_repo_root()
DEFAULT_OUT = REPO_ROOT / "modules" / "web" / "e2e" / ".auth" / "seed.json"
DEFAULT_API_BASE = "http://127.0.0.1:8000"

NAME_PREFIX = "E2E "
CHECKING_NAME = "E2E Checking"
SAVINGS_NAME = "E2E Savings"
# Short names avoid colliding with earlier soft-deleted "E2E Expense" tombstones.
EXPENSE_CATEGORY_NAME = "E2E Exp"
INCOME_CATEGORY_NAME = "E2E Inc"
BASELINE_DESCRIPTION = "E2E baseline expense"
BASELINE_DATE = "2026-03-01"


class SeedError(RuntimeError):
    """Raised when the seed cannot complete against the API."""


def _parse_retry_after(headers: Any, default: float = 1.0) -> float:
    """Parse ``Retry-After`` seconds from response headers."""
    if headers is None:
        return default
    raw = headers.get("Retry-After")
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _decode_body(raw: str) -> Any:
    """Decode response text as JSON when possible."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _build_request_payload(
    *,
    token: str | None,
    json_body: dict[str, Any] | None,
    form_body: dict[str, str] | None,
    headers: dict[str, str] | None,
) -> tuple[bytes | None, dict[str, str]]:
    """Build request body bytes and headers for ``_request``."""
    req_headers = dict(headers or {})
    data: bytes | None = None
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    elif form_body is not None:
        data = urllib.parse.urlencode(form_body).encode("utf-8")
        req_headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        req_headers["Authorization"] = f"Bearer {token}"
    return data, req_headers


def _exchange(
    method: str,
    url: str,
    *,
    data: bytes | None,
    headers: dict[str, str],
) -> tuple[int, Any, float]:
    """Execute one HTTP exchange; return status, body, and Retry-After seconds."""
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
            return response.getcode(), _decode_body(raw), _parse_retry_after(response.headers)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return exc.code, _decode_body(raw), _parse_retry_after(exc.headers)
    except urllib.error.URLError as exc:
        raise SeedError(f"Cannot reach API at {url}: {exc.reason}") from exc


def _request(
    method: str,
    url: str,
    *,
    token: str | None = None,
    json_body: dict[str, Any] | None = None,
    form_body: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    retries: int = 4,
) -> tuple[int, Any]:
    """Perform an HTTP request and return ``(status, parsed_json_or_text)``."""
    data, req_headers = _build_request_payload(token=token, json_body=json_body, form_body=form_body, headers=headers)
    last_status = 0
    last_body: Any = None
    for attempt in range(retries + 1):
        status, body, retry_after = _exchange(method, url, data=data, headers=req_headers)
        last_status, last_body = status, body
        if status != 429 or attempt >= retries:
            return status, body
        time.sleep(min(max(retry_after, 0.5), 30.0) * (attempt + 1))
    return last_status, last_body


def _api(base: str, path: str) -> str:
    return f"{base.rstrip('/')}{path}"


def _require_ok(status: int, body: Any, *, expected: set[int], action: str) -> Any:
    if status not in expected:
        raise SeedError(f"{action} failed HTTP {status}: {body}")
    return body


def _list_items(base: str, token: str, path: str, *, limit: int = 100) -> list[dict[str, Any]]:
    status, body = _request("GET", _api(base, f"{path}?limit={limit}"), token=token)
    payload = _require_ok(status, body, expected={200}, action=f"GET {path}")
    if not isinstance(payload, dict):
        raise SeedError(f"Unexpected list payload for {path}: {payload}")
    items = payload.get("items") or []
    if not isinstance(items, list):
        raise SeedError(f"Unexpected items for {path}: {items}")
    return [item for item in items if isinstance(item, dict)]


def _find_by_name(items: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for item in items:
        if item.get("name") != name:
            continue
        if item.get("active") is False or item.get("is_active") is False:
            continue
        if item.get("deleted_at") is not None:
            continue
        return item
    return None


def _entity_exists(base: str, token: str, path: str, entity_id: str) -> bool:
    """Return True when GET ``path/{id}`` is 200 (guards phantom create IDs)."""
    status, _body = _request("GET", _api(base, f"{path}/{entity_id}"), token=token)
    return status == 200


def _register_or_login(
    base: str,
    *,
    email: str,
    password: str,
    username: str,
    skip_register: bool,
) -> tuple[str, str]:
    """Return ``(access_token, owner_id)`` for the fixture user."""
    if not skip_register:
        status, body = _request(
            "POST",
            _api(base, "/api/v1/auth/register"),
            json_body={
                "email": email,
                "password": password,
                "username": username,
                "display_name": "E2E Owner",
            },
        )
        if status not in {201, 409, 422}:
            raise SeedError(f"Register failed HTTP {status}: {body}")

    status, body = _request(
        "POST",
        _api(base, "/api/v1/auth/login"),
        form_body={"username": email, "password": password},
    )
    login = _require_ok(status, body, expected={200}, action="Login")
    if not isinstance(login, dict) or "access_token" not in login:
        raise SeedError(f"Login response missing access_token: {login}")
    token = str(login["access_token"])

    status, me = _request("GET", _api(base, "/api/v1/auth/me"), token=token)
    me_body = _require_ok(status, me, expected={200}, action="GET /auth/me")
    if not isinstance(me_body, dict) or "id" not in me_body:
        raise SeedError(f"/auth/me missing id: {me_body}")
    return token, str(me_body["id"])


def _ensure_account(
    base: str,
    token: str,
    *,
    name: str,
    initial_value: float,
    force_create: bool = False,
) -> str:
    if not force_create:
        accounts = _list_items(base, token, "/api/v1/accounts")
        existing = _find_by_name(accounts, name)
        existing_id = str(existing["id"]) if existing and existing.get("id") else None
        if existing_id and _entity_exists(base, token, "/api/v1/accounts", existing_id):
            return existing_id

    status, body = _request(
        "POST",
        _api(base, "/api/v1/accounts"),
        token=token,
        json_body={
            "name": name,
            "account_kind": "other_asset",
            "ledger_side": "asset",
            "currency": "USD",
            "initial_value": initial_value,
        },
    )
    created = _require_ok(status, body, expected={201}, action=f"Create account {name}")
    if not isinstance(created, dict) or "id" not in created:
        raise SeedError(f"Create account missing id: {created}")
    account_id = str(created["id"])
    if not _entity_exists(base, token, "/api/v1/accounts", account_id):
        raise SeedError(
            f"Create account {name!r} returned id {account_id} but GET is 404 "
            "(soft-delete unique tombstone?). Use a fresh E2E_USER_EMAIL or wipe Compose volumes."
        )
    return account_id


def _ensure_category(
    base: str,
    token: str,
    *,
    name: str,
    category_type: str,
) -> str:
    """Reuse an active category by name, or create one and verify GET."""
    categories = _list_items(base, token, "/api/v1/categories")
    existing = _find_by_name(categories, name)
    existing_id = str(existing["id"]) if existing and existing.get("id") else None
    if existing_id and _entity_exists(base, token, "/api/v1/categories", existing_id):
        return existing_id

    status, body = _request(
        "POST",
        _api(base, "/api/v1/categories"),
        token=token,
        json_body={"name": name, "category_type": category_type},
    )
    created = _require_ok(status, body, expected={201}, action=f"Create category {name}")
    if not isinstance(created, dict) or "id" not in created:
        raise SeedError(f"Create category missing id: {created}")
    category_id = str(created["id"])
    if not _entity_exists(base, token, "/api/v1/categories", category_id):
        raise SeedError(
            f"Create category {name!r} returned id {category_id} but GET is 404 "
            "(likely unique constraint vs soft-deleted row). "
            "Do not soft-delete fixture categories; use a fresh E2E_USER_EMAIL or wipe volumes."
        )
    return category_id


def _ensure_baseline_expense(
    base: str,
    token: str,
    *,
    account_id: str,
    category_id: str,
    force_create: bool = False,
) -> str:
    if not force_create:
        txns = _list_items(base, token, "/api/v1/transactions")
        for item in txns:
            txn_id = item.get("id")
            if item.get("description") != BASELINE_DESCRIPTION or not txn_id:
                continue
            if _entity_exists(base, token, "/api/v1/transactions", str(txn_id)):
                return str(txn_id)

    idem_key = f"e2e-baseline-{account_id}-{uuid.uuid4().hex[:8]}"
    status, body = _request(
        "POST",
        _api(base, "/api/v1/transactions"),
        token=token,
        headers={"Idempotency-Key": idem_key},
        json_body={
            "account_id": account_id,
            "category_id": category_id,
            "transaction_type": "expense",
            "amount": 12.34,
            "currency": "USD",
            "description": BASELINE_DESCRIPTION,
            "transaction_date": BASELINE_DATE,
        },
    )
    created = _require_ok(status, body, expected={201}, action="Create baseline expense")
    if not isinstance(created, dict) or "id" not in created:
        raise SeedError(f"Baseline txn missing id: {created}")
    return str(created["id"])


def _soft_delete_prefixed_accounts(base: str, token: str) -> int:
    deleted = 0
    for item in _list_items(base, token, "/api/v1/accounts"):
        name = item.get("name")
        item_id = item.get("id")
        if not isinstance(name, str) or not name.startswith(NAME_PREFIX) or not item_id:
            continue
        status, body = _request("DELETE", _api(base, f"/api/v1/accounts/{item_id}"), token=token)
        if status not in {204, 404}:
            raise SeedError(f"DELETE account {item_id} failed HTTP {status}: {body}")
        deleted += 1
        time.sleep(0.15)
    return deleted


def _soft_delete_baseline_txns(base: str, token: str) -> int:
    deleted = 0
    for item in _list_items(base, token, "/api/v1/transactions"):
        if item.get("description") != BASELINE_DESCRIPTION or not item.get("id"):
            continue
        status, body = _request(
            "DELETE",
            _api(base, f"/api/v1/transactions/{item['id']}"),
            token=token,
        )
        if status not in {204, 404}:
            raise SeedError(f"DELETE transaction failed HTTP {status}: {body}")
        deleted += 1
        time.sleep(0.15)
    return deleted


def _probe_live(base: str) -> None:
    status, body = _request("GET", _api(base, "/api/v1/health/live"))
    if status != 200:
        raise SeedError(f"API not healthy at {base} (HTTP {status}: {body}). Run: make api-all")


def seed(*, api_base: str, out_path: Path, reset: bool) -> dict[str, Any]:
    """Create or refresh fixture data and return the seed artifact dict."""
    email = os.environ.get("E2E_USER_EMAIL", "e2e.owner@example.local")
    password = os.environ.get("E2E_USER_PASSWORD", "SecurePass1!")
    username = os.environ.get("E2E_USER_USERNAME", "e2e_owner")
    skip_register = os.environ.get("E2E_SKIP_REGISTER", "").lower() in {"1", "true", "yes"}

    _probe_live(api_base)
    token, owner_id = _register_or_login(
        api_base,
        email=email,
        password=password,
        username=username,
        skip_register=skip_register,
    )

    if reset:
        _soft_delete_baseline_txns(api_base, token)
        _soft_delete_prefixed_accounts(api_base, token)
        # Categories intentionally kept — soft-delete + same-name create is unsafe.

    checking_id = _ensure_account(api_base, token, name=CHECKING_NAME, initial_value=1_000.0, force_create=reset)
    savings_id = _ensure_account(api_base, token, name=SAVINGS_NAME, initial_value=500.0, force_create=reset)
    expense_category_id = _ensure_category(api_base, token, name=EXPENSE_CATEGORY_NAME, category_type="expense")
    income_category_id = _ensure_category(api_base, token, name=INCOME_CATEGORY_NAME, category_type="income")
    baseline_txn_id = _ensure_baseline_expense(
        api_base,
        token,
        account_id=checking_id,
        category_id=expense_category_id,
        force_create=reset,
    )

    artifact = {
        "apiBase": api_base,
        "email": email,
        "password": password,
        "username": username,
        "ownerId": owner_id,
        "accountIds": {
            "checking": checking_id,
            "savings": savings_id,
        },
        "accountNames": {
            "checking": CHECKING_NAME,
            "savings": SAVINGS_NAME,
        },
        "categoryIds": {
            "expense": expense_category_id,
            "income": income_category_id,
        },
        "categoryNames": {
            "expense": EXPENSE_CATEGORY_NAME,
            "income": INCOME_CATEGORY_NAME,
        },
        "baselineTxnId": baseline_txn_id,
        "baselineDescription": BASELINE_DESCRIPTION,
        "namePrefix": NAME_PREFIX.strip(),
        "seedId": uuid.uuid4().hex,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    return artifact


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Seed Playwright E2E fixtures (PPT-061).")
    parser.add_argument(
        "--api-base",
        default=os.environ.get("E2E_API_BASE", DEFAULT_API_BASE),
        help="Running API origin (default E2E_API_BASE or http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(os.environ.get("E2E_SEED_OUT", str(DEFAULT_OUT))),
        help="Path for seed.json artifact",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Soft-delete baseline txns + E2E accounts, then recreate (categories reused)",
    )
    args = parser.parse_args(argv)

    try:
        artifact = seed(api_base=args.api_base, out_path=args.out, reset=args.reset)
    except SeedError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"E2E seed OK → {args.out}")
    print(
        json.dumps(
            {
                "ownerId": artifact["ownerId"],
                "email": artifact["email"],
                "accountIds": artifact["accountIds"],
                "categoryIds": artifact["categoryIds"],
                "categoryNames": artifact["categoryNames"],
                "baselineTxnId": artifact["baselineTxnId"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

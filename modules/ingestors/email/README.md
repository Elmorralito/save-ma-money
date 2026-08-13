# papita-ingestor-email

Email / Gmail source plugin for Papita ingestion (`papita_ingestor_email`).

|                 |                                                                                                          |
| --------------- | -------------------------------------------------------------------------------------------------------- |
| Distribution    | `papita-ingestor-email`                                                                                  |
| Import root     | `papita_ingestor_email`                                                                                  |
| Python          | **≥3.12** (CI/dev). Packaging bounds `requires-python = ">=3.10,<3.15"` match model/api / ingestor-core. |
| Path dependency | `papita-ingestor-core` → `../../ingestor-core`                                                           |
| Epic            | PPT-076 / [#170](https://github.com/Elmorralito/save-ma-money/issues/170)                                |
| Scaffold        | PPT-077 / [#171](https://github.com/Elmorralito/save-ma-money/issues/171)                                |

## Role

Plugin package under `modules/ingestors/`. Hosts the Gmail OAuth2 source
(PPT-080 / [#174](https://github.com/Elmorralito/save-ma-money/issues/174)) and
bank-specific email parsers (PPT-081 /
[#175](https://github.com/Elmorralito/save-ma-money/issues/175)). Prefect
packaging is PPT-082 — not this package’s job. CI for the Gmail source uses
**mocks only** (no live Google credentials in Actions).

## Dependency graph (one-way)

```text
papita-ingestor-email  →  papita-ingestor-core  →  papita-transactions-model
```

`papita_txnsapi` / `@papita/web` **must not** import this package.

## Gmail source (PPT-080 / #174)

`GmailSource` implements `BaseIngestorSource` and self-registers as `"gmail"`:

```python
from papita_ingestor_core import FetchFilter, SourceRegistry
from papita_ingestor_email import GmailSettings, create_gmail_source

# After `import papita_ingestor_email` (or create_gmail_source):
assert SourceRegistry.get("gmail") is not None

with create_gmail_source(GmailSettings()) as source:  # reads GMAIL_* from env
    for record in source.fetch(FetchFilter(limit=10, extra={"sender": "bank@example.com"})):
        # record.content = raw MIME bytes; metadata has subject/sender/headers
        source.acknowledge(record)  # applies GMAIL_PROCESSED_LABEL
```

CI uses **mocked** `googleapiclient` only. Live smoke needs `GMAIL_*` in
`environments/local/.env` (see bootstrap below).

## Bank email parsers (PPT-081 / #175)

`BancolombiaParser`, `NequiParser`, and hybrid `FallbackEmailParser` implement
`BaseRecordParser` and register on `ParserRegistry` when the package (or
`papita_ingestor_email.parsers`) is imported:

```python
from papita_ingestor_core import ParserRegistry
from papita_ingestor_email import ensure_parsers_registered

ensure_parsers_registered()  # idempotent after ParserRegistry.clear()
parser = ParserRegistry.select_for(raw_record)  # bank parsers beat fallback
parsed = parser.parse(raw_record)  # currency COP; FKs None until PPT-082
```

| Parser                | `parser_id`         | Priority | Notes                                                                       |
| --------------------- | ------------------- | -------- | --------------------------------------------------------------------------- |
| `BancolombiaParser`   | `bancolombia-email` | 100      | Sender `*notificacionesbancolombia.com`; Recibiste / transferiste / Pagaste |
| `NequiParser`         | `nequi-email`       | 90       | **Synthetic** `@nequi.com.co` fixtures (not Nu / `nu.com.co`)               |
| `FallbackEmailParser` | `fallback-email`    | -100     | Email-shaped leftovers → `IngestorParseError("unrecognized email")`         |

Unrecognized path:

1. Without Fallback in `instances` → `LookupError` → runner DLQ.
2. With Fallback → typed `IngestorParseError` → same DLQ; never invents amounts / never returns `None`.

Unit fixtures live under `tests/fixtures/emails/` (sanitized MIME). Account / category FKs stay `None` from parsers; live FK enricher is out of
scope for PPT-082 (tests inject FKs or assert DLQ-then-ack). Nu payment and Nu
monthly extracto emails are out of scope for these parsers.

## Prefect email flow (PPT-082 / #176)

Hourly (configurable) Prefect flow wires `GmailSource` + bank parsers +
`IngestionBridgeService` via `IngestionRunner`. Owner tenancy is
`PAPITA_INGESTOR_OWNER_ID` only — never from MIME. Host runs load
`environments/$PAPITA_ENV/.env` automatically and call
`SQLDatabaseConnector.establish(DATABASE_URL)` before persist/DLQ.

**Known limit (H1=B / #176):** bank parsers leave account/category FKs `None`.
A live run against real Gmail will **DLQ-then-ack** parsed mail (no ledger
upsert) until a FK enricher exists. CLI preflight logs this warning and requires
Gmail auth env + an **active** `users.id` matching `PAPITA_INGESTOR_OWNER_ID`
(unless `PAPITA_INGESTOR_DRY_RUN=true`). Use dry-run for safe connect/parse smoke;
inject FKs only in tests.

```bash
# Prefect optional (root package-mode=false → Poetry group, not -E)
make ingestor-flow-install

# One-shot run (needs DATABASE_URL, PAPITA_INGESTOR_OWNER_ID, GMAIL_*)
# OWNER_ID must exist in users (FK on provenance / dead letters).
make ingestor-flow

# Serve on interval (default 60 minutes)
make ingestor-flow-serve

# Optional Compose worker — does not start with make api-up
make ingestor-up
make ingestor-down
```

Entrypoint: `python -m papita_ingestor_email.flows.email_flow` (`--once` or serve).
Schedule: `PAPITA_INGESTOR_SCHEDULE_INTERVAL_MINUTES` (default `60`).
Compose already injects env — pass `--skip-env-file` if you need to avoid
reloading the host `.env` inside the container (default load is harmless when
vars are already set: `override=False`).

## Local commands

```bash
make ingestor-install
make ingestor-flow-install   # when working on Prefect flow
make ingestor-test
make ingestor-lint
```

## Secrets

**R2 locked (PPT-080 / #174):** headless refresh-token env is the default runtime
path. Interactive `InstalledAppFlow` is bootstrap-only (to mint
`GMAIL_REFRESH_TOKEN`). If `GMAIL_TOKEN_FILE` points at a readable authorized-user
JSON, that file is preferred at connect time; otherwise
`GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` / `GMAIL_REFRESH_TOKEN` are required.

`GmailSettings` composes with (does not subclass) `BaseIngestorSettings` so
`GMAIL_*` and `PAPITA_INGESTOR_*` prefixes stay distinct.

Names only in [`.env.example`](.env.example). Put real values in
`environments/<env>/.env` (gitignored). Never commit `token.json`,
`credentials.json`, `client_secret*.json`, or refresh tokens — ignored via root
and module `.gitignore`.

| Variable                | Purpose                                                   |
| ----------------------- | --------------------------------------------------------- |
| `GMAIL_CLIENT_ID`       | OAuth Desktop client ID                                   |
| `GMAIL_CLIENT_SECRET`   | OAuth Desktop client secret                               |
| `GMAIL_REFRESH_TOKEN`   | Long-lived refresh token (headless default)               |
| `GMAIL_TOKEN_URI`       | Usually `https://oauth2.googleapis.com/token`             |
| `GMAIL_PROCESSED_LABEL` | Label applied on acknowledge (default `PAPITA_PROCESSED`) |
| `GMAIL_TOKEN_FILE`      | Optional secondary path to a token JSON (not the default) |

| Variable                                    | Purpose                                                         |
| ------------------------------------------- | --------------------------------------------------------------- |
| `PAPITA_INGESTOR_OWNER_ID`                  | Trusted tenant UUID for bridge persist (required for live runs) |
| `PAPITA_INGESTOR_LOOKBACK_HOURS`            | Fetch window when no explicit `FetchFilter.since` (default 24)  |
| `PAPITA_INGESTOR_SCHEDULE_INTERVAL_MINUTES` | Prefect serve interval (default 60)                             |
| `PAPITA_INGESTOR_FETCH_LIMIT` / `DRY_RUN`   | Runner knobs (`BaseIngestorSettings`)                           |
| `PAPITA_INGESTOR_FLOW_RETRIES`              | Prefect flow retries (default 2)                                |
| `DATABASE_URL`                              | B0 Postgres for `IngestionBridgeService`                        |

Runner knobs stay on `PAPITA_INGESTOR_*` — do not remap them to `GMAIL_*`.
Compose `EmailFlowSettings` + `GmailSettings` at the flow boundary.

**Status persistence (PPT-083 / #177):** non-dry runs upsert allowlisted connection
metadata and append/finish run rows via model services (never `GmailSettings`
secrets). Flow name `papita-email-ingestion`; serve deployment
`papita-email-ingestion-hourly`. **Trigger SSOT is this Prefect worker**
(`make ingestor-flow` / serve / Compose `ingestor`) — the API exposes
**read-only** `GET /api/v1/ingestion/*` status routes only (no HTTP run-once).
Catalog: [`modules/api/README.md` § Ingestion status](../../api/README.md#ingestion-status-endpoints-ppt-083).

## Local Gmail OAuth bootstrap

Use this once to obtain `GMAIL_REFRESH_TOKEN` for **optional local live smoke**.
Unit tests do not require it.

### 1. Google Cloud

1. Create or select a project in [Google Cloud Console](https://console.cloud.google.com/).
2. Enable **Gmail API** (APIs & Services → Library).
3. Configure the **OAuth consent screen** (External, or Internal for Workspace).
   - Add scope `https://www.googleapis.com/auth/gmail.modify` (read + label/modify).
   - While the app is in Testing, add your mailbox as a **test user**.
4. Create credentials → **OAuth client ID** → type **Desktop app**.
   - Note the client ID and secret (or download the client JSON for the bootstrap only).

### 2. One-time consent (refresh token)

With `google-auth-oauthlib` available in this package’s env (dev/bootstrap only):

```bash
# Run from a throwaway directory. Do not commit credentials.json or printed tokens.
poetry run python - <<'PY'
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
# force offline access if the library version requires it:
# flow.authorization_url(access_type="offline", prompt="consent")
creds = flow.run_local_server(port=0)
print("GMAIL_REFRESH_TOKEN=", creds.refresh_token)
print("GMAIL_TOKEN_URI=", creds.token_uri)
PY
```

Sign in as the mailbox user, approve scopes, copy the refresh token. Then delete
local `credentials.json` / any generated `token.json`.

If a later run returns no refresh token: revoke the app under
[Google Account → Third-party access](https://myaccount.google.com/permissions)
and consent again with offline access.

### 3. Wire env for local smoke

```bash
# environments/local/.env  (gitignored)
GMAIL_CLIENT_ID=....apps.googleusercontent.com
GMAIL_CLIENT_SECRET=...
GMAIL_REFRESH_TOKEN=...
GMAIL_TOKEN_URI=https://oauth2.googleapis.com/token
GMAIL_PROCESSED_LABEL=PAPITA_PROCESSED
```

### 4. What not to do

- Do not put Google secrets in GitHub Actions for PPT-080 CI.
- Do not commit OAuth client JSON or refresh tokens under `modules/` or the repo root.
- Mailbox OAuth is **not** Supabase JWT / BFF auth; set `PAPITA_INGESTOR_OWNER_ID`
  to an existing `users.id` for persist.

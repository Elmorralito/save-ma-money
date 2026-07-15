# PPT-031 Auth contract (G5) — Supabase Auth MVP

**Canonical detail:** [`ARCHITECTURE.md` Part VI](ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e)

**Status (2026-07-13):** G5 revised for **PPT-039** — Supabase Auth is MVP. Local HS256 is transitional/tests only.

| Topic               | Decision                                                                                                                                                       |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Access tokens       | Supabase JWT; API verifies via JWKS (`AUTH_PROVIDER=supabase`, `SUPABASE_URL`)                                                                                 |
| Tenant key          | JWT `sub` → `papita_transactions.users.id` (provision-on-first-seen)                                                                                           |
| Login identity      | **Email** is canonical; `users.username` is a derived handle (`USERNAME_REGEX`)                                                                                |
| Register / login    | Prefer client → Supabase Auth; API pass-through with `SUPABASE_ANON_KEY`                                                                                       |
| Auth errors         | Mapped to HTTP (`409` duplicate email, `429` rate limit, `401` bad credentials)                                                                                |
| Orphan cleanup      | If Auth user is created but Papita provision fails: Admin delete via `SUPABASE_SERVICE_ROLE_KEY` (register always; login only if Auth user created within 15m) |
| Google / GitHub SSO | Server PKCE: `GET /auth/oauth/{provider}` + `POST                                                                                                              | GET /auth/oauth/callback` (`exchange_code_for_session`); token handoff via `POST /auth/sso` |

| Refresh / logout | `POST /auth/refresh` + `POST /auth/logout` when `AUTH_PROVIDER=supabase` |
| Database | Any Postgres (Docker B0 or hosted); **not** coupled to Auth |

## OAuth SSO (dashboard + server PKCE)

1. Supabase → **Authentication** → **Providers** → enable **Google** and/or **GitHub**.
2. Add redirect URL(s) to the IdP + Supabase Auth → URL Configuration. Prefer the API callback:
   `http://localhost:8000/api/v1/auth/oauth/callback` (or set `SUPABASE_OAUTH_REDIRECT_TO`).
   API `redirect_to` is allowlisted to that configured URI or the API callback only.
3. Server flow (recommended):
   - `GET /api/v1/auth/oauth/{google|github}` → `{ url, code_verifier }`
   - Browser opens `url`; after redirect, client receives `?code=...`
   - `POST /api/v1/auth/oauth/callback` with `{ provider, auth_code, code_verifier }`
     (GoTrue `exchange_code_for_session`)
   - Or `GET /api/v1/auth/oauth/{provider}?follow=true` then land on `GET /oauth/callback`
     (PKCE verifier + provider + redirect_to in HttpOnly cookies; `Secure` when not DEBUG).
4. Soft-deleted/inactive `users` rows are not reactivated by OAuth/login provisioning.
5. Legacy token handoff: `POST /api/v1/auth/sso` with `{ provider, access_token, refresh_token }`.
6. `users.provider_type` uses `ProviderType` (`email` | `google` | `github`).

## Smoke

```bash
export PAPITA_ENV=local   # or staging
# environments/$PAPITA_ENV/.env must set AUTH_PROVIDER=supabase, SUPABASE_URL, SUPABASE_ANON_KEY
make auth-smoke
```

Target: Auth access JWT → `GET /api/v1/auth/me` (+ `GET /api/v1/accounts`).

## References

- [#49](https://github.com/Elmorralito/save-ma-money/issues/49) PPT-039
- [`PPT-039-supabase-auth-reissue.md`](../issues/PPT-039-supabase-auth-reissue.md)
- PPT-031-C [G7 supersede](../issues/PPT-031-C-supabase-decision-brief.md#g7-supersede-2026-07-13--auth-first)

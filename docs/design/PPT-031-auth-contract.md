# PPT-031 Auth contract (G5) — Supabase Auth MVP

**Canonical detail:** [`ARCHITECTURE.md` Part VI](ARCHITECTURE.md#part-vi--auth-contract-ppt-031-track-e)

**Status (2026-07-13):** G5 revised for **PPT-039** — Supabase Auth is MVP. Local HS256 is transitional/tests only.

| Topic            | Decision                                                                          |
| ---------------- | --------------------------------------------------------------------------------- |
| Access tokens    | Supabase JWT; API verifies via JWKS (`AUTH_PROVIDER=supabase`, `SUPABASE_URL`)    |
| Tenant key       | JWT `sub` → `papita_transactions.users.id` (provision-on-first-seen)              |
| Register / login | Prefer client → Supabase Auth; optional API pass-through with `SUPABASE_ANON_KEY` |
| Refresh / logout | Still **501** on Papita API (FR-11); use Supabase session APIs later              |
| Database         | Any Postgres (Docker B0 or hosted); **not** coupled to Auth                       |

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

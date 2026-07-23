**Parent program:** [#28](https://github.com/Elmorralito/save-ma-money/issues/28) (PPT-031) · **Parent epic:** [#42](https://github.com/Elmorralito/save-ma-money/issues/42) (PPT-032) · **PPT-044** · **Step:** Post-MVP API hardening (whole surface)

**GitHub issue:** [#89](https://github.com/Elmorralito/save-ma-money/issues/89)

## Summary

API-wide post-MVP hardening for `papita-txnsapi`. Full tasks, caveats, and acceptance: [#89](https://github.com/Elmorralito/save-ma-money/issues/89).

**Last review:** 2026-07-23 — implementation landed against live tree after PPT-043 Redis close-out; title remains **`fix/`**.

## Depends on

- [#42](https://github.com/Elmorralito/save-ma-money/issues/42) (PPT-032) — closed
- Soft (landed): [#83](https://github.com/Elmorralito/save-ma-money/issues/83) (PPT-043 Redis), [#50](https://github.com/Elmorralito/save-ma-money/issues/50) (PPT-040)

## Already done (regression only)

JWT alg pin on decode · JWT `type` + UUID `sub` · inactive user reject · auth login/register IP limits (direct socket) · masked 500s · CRUD cross-tenant 404 pattern · health `literal(1)` + allowlisted detail + injection tests · request logs omit headers/bodies · **tenant API rate limits + Redis denylist (PPT-043)** · **logout/denylist honesty under Supabase/Redis**

## Implementation status (2026-07-23)

| Phase | Theme                                                                                                | Status |
| ----- | ---------------------------------------------------------------------------------------------------- | ------ |
| P1    | Headers, TrustedHost, CORS fail-fast, docs gate, body-size docs                                      | Done   |
| P2    | JWT secret min length, `JWT_ALGORITHM` allowlist, `LOG_LEVEL` prod posture                           | Done   |
| P3    | Budgets JWT, write `extra="forbid"`, free-text bounds, reports foreign account **404**               | Done   |
| P5    | Bulk `max_length=100`, report window ≤366d, `refresh_balances` default **false**, health rate limits | Done   |
| P4    | Driverish `ValueError` mask; 500 masking regression                                                  | Done   |
| P6    | Probe timeout, `Cache-Control: no-store`, health 405 tests                                           | Done   |
| P7    | `tests/test_security_pack.py` + env/README/brief                                                     | Done   |

## Decisions locked

- Reports foreign `account_id` → **404** (CRUD parity)
- Keep `/health/database` public; rate-limit + `no-store`; do not expand detail vocabulary
- Bulk max **100**; report window **366** days
- `refresh_balances` default **false**
- CORS `*` forbidden when `DEBUG=false`

## Client-breaking change hardening (2026-07-23)

Strategy: keep secure defaults; make them discoverable and temporarily reversible for wire-contract breaks only.

| Mechanism                            | Purpose                                                                            |
| ------------------------------------ | ---------------------------------------------------------------------------------- |
| `GET /api/v1/meta/client-contract`   | Public probe of effective limits / compat / error codes                            |
| `X-Papita-*` response headers        | Per-response discovery (`Bulk-Max`, `Report-Window-Max-Days`, …)                   |
| `X-Papita-Error-Code`                | Stable codes for SDK branching                                                     |
| `API_COMPAT_LEGACY_*` flags          | Time-boxed legacy 400 / refresh default; emit `Deprecation` + `Sunset: 2026-10-01` |
| No compat for CORS `*` / public docs | Security posture must not regress                                                  |

See `modules/api/README.md` § PPT-044 client migration.

## Out of scope

WAF/CDN · new domain features · RLS redesign · keyset pagination product · public admin metrics · PPT-045 packaging (#93)

## Acceptance

See [#89](https://github.com/Elmorralito/save-ma-money/issues/89). B0 + B1 when contracts change.

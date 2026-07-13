**Parent program:** [#28](https://github.com/Elmorralito/save-ma-money/issues/28) (PPT-031) · **Parent epic:** [#42](https://github.com/Elmorralito/save-ma-money/issues/42) (PPT-032) · **PPT-044** · **Step:** Post-MVP API hardening (whole surface)

**GitHub issue:** [#89](https://github.com/Elmorralito/save-ma-money/issues/89)

## Summary

API-wide post-MVP hardening for `papita-txnsapi`. Full tasks, caveats, and acceptance: [#89](https://github.com/Elmorralito/save-ma-money/issues/89).

**Last review:** 2026-07-13 — validated against live code; title uses official Conventional Commit type **`fix/`** (not `harden/` / `perf/`); credited already-done controls; added missing bulk/report/budgets/JWT-algorithm gaps.

## Depends on

- [#42](https://github.com/Elmorralito/save-ma-money/issues/42) (PPT-032)
- Soft: [#83](https://github.com/Elmorralito/save-ma-money/issues/83) (PPT-043), [#50](https://github.com/Elmorralito/save-ma-money/issues/50) (PPT-040)

## Already done (regression only)

JWT alg pin on decode · JWT `type` + UUID `sub` · inactive user reject · auth login/register IP limits (direct socket) · masked 500s · CRUD cross-tenant 404 pattern · health `literal(1)` + allowlisted detail + injection tests · request logs omit headers/bodies

## Highest remaining gaps

| Priority | Gap                                                                                                                            |
| -------- | ------------------------------------------------------------------------------------------------------------------------------ |
| P1       | CORS `*` + credentials; docs always on; TrustedHost; security headers; body-size docs                                          |
| P2       | `JWT_SECRET_KEY` min length; **allowlist `JWT_ALGORITHM`**; prod `LOG_LEVEL`                                                   |
| P3       | Tenancy matrix gaps; reports `account_id` **400 vs 404**; JWT on `/budgets` 501s; `extra="forbid"` on writes; free-text bounds |
| P5       | Bulk `max_length`; report max window; `refresh_balances` default abuse; authenticated + health-DB rate limits                  |
| P4       | Safe `ValueError` allowlist; 500/422 regression tests                                                                          |
| P6       | Probe timeout; `/database` exposure; `Cache-Control`; quiet `/live` logs; health 405 tests                                     |
| P7       | Consolidated security pack (extend, don’t duplicate)                                                                           |

## Workstream index

| Phase | IDs     | Theme                                                        |
| ----- | ------- | ------------------------------------------------------------ |
| P0    | A0      | OpenAPI inventory + budgets JWT on stubs                     |
| P1    | T1–T5   | Headers, TrustedHost, CORS, docs gate, body size             |
| P2    | AU1–AU4 | Secret/alg allowlist; credit claims work; logout honesty     |
| P3    | TE1–TE4 | Tenancy matrix; forbid extras; injection; pagination/reports |
| P4    | E1–E2   | Error disclosure; DEBUG off                                  |
| P5    | R1–R3   | Extend rate limits; expensive routes                         |
| P6    | H1–H10  | Health/ops                                                   |
| P7    | O1–O4   | Logs, settings, regression pack, supply-chain                |

## Out of scope

PPT-043 Redis · new domain features · WAF/CDN · RLS redesign · keyset pagination product · public admin metrics

## Acceptance

See [#89](https://github.com/Elmorralito/save-ma-money/issues/89). B0 + B1 when contracts change.

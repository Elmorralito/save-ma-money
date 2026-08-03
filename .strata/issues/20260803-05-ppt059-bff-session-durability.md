---
id: 20260803-05
type: feature
status: in-progress
severity: med
area: modules/api
created: 2026-08-03
---

**What:** PPT-059 [#124](https://github.com/Elmorralito/save-ma-money/issues/124) — BFF session durability contract vs Redis (PPT-043): B0 memory OK (single worker); Redis required for staging / multi-worker; denylist ≠ BFF map; fail-closed when `REDIS_ENABLED`.

**Why:** Locks multi-worker / staging SPA cookie behavior; soft-aligns #83 (not a scaffold gate); hands Compose Redis listing to #122.

**Progress:**

- [x] Docs/contract (web + API README matrices, ops checklist, env.example comments, AGENTS)
- [x] `BffSessionStore.fail_closed` when `REDIS_ENABLED`; CSRF/auth/handlers → 503
- [x] Unit tests (fail-closed RedisError + no memory on miss)
- [x] #122 handoff noted (no nginx work here)
- [x] PR [#153](https://github.com/Elmorralito/save-ma-money/pull/153) opened
- [ ] Merge + close GitHub #124; delete this strata item

**Resolution:** (open — PR pending merge)

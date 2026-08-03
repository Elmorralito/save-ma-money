---
id: 20260803-06
type: feature
status: in-progress
severity: high
area: modules/web
created: 2026-08-03
---

# PPT-056 / #121 Vitest Playwright a11y and security hardening

**What:** Raise web quality/security bar — Vitest coverage, Playwright critical path
(wired to PPT-061 seed), axe WCAG 2.1 AA intent, Lighthouse lab CWV budgets,
BFF cookie / CSP / audit checklist.

**Why:** Epic Step 3 gate before launch packaging (#122). Depends on merged
#125 (auth matrix) + #126 (seed SSOT).

**Acceptance pointers:** `modules/web/README.md` § Quality; `web-ci` coverage;
`web-e2e.yml` Compose + Playwright; PR template web security checklist.

#!/usr/bin/env bash
# Apply PPT-039 Auth-first + epic #42 GitHub issue edits (requires valid gh auth).
# Usage: /bin/bash ./deploy/github_apply_ppt039_reissue.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! gh auth status -h github.com >/dev/null 2>&1; then
  echo "gh auth is not usable. Run: gh auth refresh -h github.com" >&2
  exit 1
fi

gh issue edit 49 --repo Elmorralito/save-ma-money \
  --title "feat/PPT-039: [api] Supabase Auth (replace local JWT issuance)" \
  --body-file docs/issues/_gh_body_PPT-039.md

gh issue edit 42 --repo Elmorralito/save-ma-money \
  --title "feat/PPT-032: [EPIC][api] FastAPI MVP on v3 model + Supabase Auth" \
  --body-file docs/issues/_gh_body_PPT-032-epic.md

gh issue comment 49 --repo Elmorralito/save-ma-money --body-file - <<'EOF'
## Scope pivot (2026-07-13)

PPT-039 is **repurposed to Supabase Auth only**. Prior B1 **Postgres pooler** ACs for this issue are **waived** (optional ops remain in-tree).

- Canonical write-up: `docs/issues/PPT-039-supabase-auth-reissue.md`
- Brief G7 supersede: `docs/issues/PPT-031-C-supabase-decision-brief.md`
- Epic updated: #42

### Handoff to #50
Prefer CI secrets: `SUPABASE_URL` (+ JWKS / test Auth project). `DATABASE_URL` = any Postgres — **not** required to be Supabase pooler for Auth DoD.
Smoke target: Supabase access JWT → `GET /api/v1/auth/me` (+ one tenant list).
EOF

gh issue comment 50 --repo Elmorralito/save-ma-money --body-file - <<'EOF'
## Secret / smoke contract update (from PPT-039 reissue)

Epic #42 / #49 now treat **Supabase Auth** as MVP. Dual-target CI should **not** require Supabase transaction-pooler `DATABASE_URL` for Auth gates.

| Secret | Role |
| --- | --- |
| `SUPABASE_URL` | JWKS / Auth API |
| Optional anon / service role | Client Auth / server provision (service role never in clients) |
| `DATABASE_URL` | Any Postgres (Docker or hosted) |

Smoke entrypoint (target): Auth JWT → `GET /api/v1/auth/me` (+ tenant list). Optional pooler smoke remains separate from Auth DoD.
See #49 comment and `docs/issues/PPT-039-supabase-auth-reissue.md`.
EOF

gh issue comment 28 --repo Elmorralito/save-ma-money --body-file - <<'EOF'
## G7 note (2026-07-13)

Epic #42 pivots MVP Supabase usage to **Auth only** (PPT-039 / #49). **Supabase-hosted Postgres is no longer an epic AC.** Brief supersede section added in `docs/issues/PPT-031-C-supabase-decision-brief.md`. Please treat prior G7 “B1 = required staging Postgres via pooler + local JWT” as superseded for PPT-032 close-out.
EOF

echo "Done. Verify:"
gh issue view 49 --repo Elmorralito/save-ma-money --json title,url
gh issue view 42 --repo Elmorralito/save-ma-money --json title,url

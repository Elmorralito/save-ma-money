# create-issue — reference

## Template map

| Type    | Path                                         | GitHub chooser name      |
| ------- | -------------------------------------------- | ------------------------ |
| epic    | `.github/ISSUE_TEMPLATE/01-epic.md`          | Epic (PPT program)       |
| program | `.github/ISSUE_TEMPLATE/02-program-issue.md` | Program issue (PPT)      |
| child   | `.github/ISSUE_TEMPLATE/03-child-issue.md`   | Child issue (under epic) |
| bug     | `.github/ISSUE_TEMPLATE/04-bug-report.md`    | Bug report               |

## Shape references (human-written exemplars)

| Type    | Examples                                                                                                                                                                                                         |
| ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Epic    | [#42](https://github.com/Elmorralito/save-ma-money/issues/42) (PPT-032)                                                                                                                                          |
| Program | [#52](https://github.com/Elmorralito/save-ma-money/issues/52), [#89](https://github.com/Elmorralito/save-ma-money/issues/89), [#93](https://github.com/Elmorralito/save-ma-money/issues/93)                      |
| Child   | PPT-032 children [#43](https://github.com/Elmorralito/save-ma-money/issues/43)–[#50](https://github.com/Elmorralito/save-ma-money/issues/50); e.g. [#45](https://github.com/Elmorralito/save-ma-money/issues/45) |

## Example titles

```text
feat/PPT-032: [EPIC][api] FastAPI MVP on v3 model + Supabase Auth
ops/PPT-045: [api] Standardize uvicorn packaging in Compose
fix/PPT-044: [api] Post-MVP API security and operational hardening
feat/PPT-036: [api] Accounts and categories CRUD (v3 model)
fix/PPT-046: [infra] Badge workflow loops on docs-only pushes
```

## Default parents

| Field                   | Default (confirm with user)                           |
| ----------------------- | ----------------------------------------------------- |
| Parent program          | `#28` (PPT-031)                                       |
| Parent epic (API track) | `#42` (PPT-032) when relevant                         |
| Child without epic      | Reject — ask for epic number or switch to **program** |

## Labels

**Epic track labels use `EPIC: PPT-{NNN}`** (one label per epic, shared by children).

| Type    | Suggest                                                                                   |
| ------- | ----------------------------------------------------------------------------------------- |
| epic    | `enhancement` + domain + **create/apply `EPIC: PPT-{NNN}`**                               |
| child   | `enhancement` + domain + **parent epic’s `EPIC: PPT-*`** (do not create a child-id label) |
| program | `enhancement` / `CI/CD` / `documentation` as apt; + parent epic `EPIC: PPT-*` if linked   |
| bug     | `bug` (+ parent epic `EPIC: PPT-*` only if under an epic)                                 |

Child issues still use their own `PPT-{NNN}` in the **title/body**; the GitHub label is the epic’s `EPIC: PPT-*`.

### PR skip labels (functional — CI reacts)

Apply on **PRs** (not issues) when intentionally bypassing a gate. Catalog + behavior:
[`.github/CI.md` § PR skip labels](../../../.github/CI.md#pr-skip-labels).

| Label              | Skips                        |
| ------------------ | ---------------------------- |
| `skip-dev-release` | Publish model (dev) TestPyPI |
| `skip-strata`      | Strata Check                 |
| `skip-web-ci`      | Web CI                       |
| `skip-web-e2e`     | Web E2E                      |
| `skip-quality`     | Code Quality Control         |
| `skip-migrations`  | Migration Check              |
| `skip-openapi`     | OpenAPI Web Contract         |

Do **not** create new `skip-*` labels without a matching workflow `if:`.

## `gh` tips

```bash
# Auth (skill step 5 — required before create if not already logged in)
gh auth status
gh auth login   # only when status fails / scopes missing

# Epic: create track label once, then file the issue
gh label create "EPIC: PPT-046" --repo Elmorralito/save-ma-money --color "0E8A16" \
  --description "Epic track PPT-046" 2>/dev/null || true
gh issue create --repo Elmorralito/save-ma-money --title "…" --body-file /tmp/body.md \
  --label enhancement --label "EPIC: PPT-046"

# Child: reuse parent epic label (e.g. EPIC: PPT-046 from epic #112) — do not create EPIC: PPT-058
gh issue view 112 --repo Elmorralito/save-ma-money --json labels --jq '[.labels[].name]'
gh issue create --repo Elmorralito/save-ma-money --title "…" --body-file /tmp/body.md \
  --label enhancement --label "EPIC: PPT-046"

# List labels
gh label list --repo Elmorralito/save-ma-money --limit 200
```

Multiple labels: repeat `--label` (do not pass one comma-separated string unless your `gh` version accepts it).
**Never** `gh label create` for a child’s own PPT id.

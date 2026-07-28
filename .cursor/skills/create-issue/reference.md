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

Typical sets (adjust to what `gh label list` shows):

| Type    | Suggest                                                        |
| ------- | -------------------------------------------------------------- |
| epic    | `enhancement`, `PPT-{NNN}`, domain (`API`, …)                  |
| program | `enhancement` or `CI/CD` / `documentation` as apt, `PPT-{NNN}` |
| child   | `enhancement`, `PPT-{NNN}`, domain                             |
| bug     | `bug`, `PPT-{NNN}` if mapped                                   |

## `gh` tips

```bash
# Auth (skill step 5 — required before create if not already logged in)
gh auth status
gh auth login   # only when status fails / scopes missing

# Dry-run style: print then create
gh issue create --repo Elmorralito/save-ma-money --title "…" --body-file /tmp/body.md --label enhancement --label PPT-045

# List PPT labels
gh label list --repo Elmorralito/save-ma-money --limit 200 | rg 'PPT-'
```

Multiple labels: repeat `--label` (do not pass one comma-separated string unless your `gh` version accepts it).

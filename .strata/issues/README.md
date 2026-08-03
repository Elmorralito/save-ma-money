# Issues — save-ma-money

The single backlog: findings, tasks, and initiatives, one file per item. Any tool can work it — the rules below are self-contained; the full pattern lives in `.strata/MANIFEST.md` and [strata DESIGN](https://github.com/belousov-petr/strata/blob/main/docs/DESIGN.md).

## Rules

- **Capture immediately.** The moment a finding or bug surfaces mid-task, use `/strata:capture` or copy `_TEMPLATE.md` to `<id>-<slug>.md`, write full rationale and diagnostics (Tried/Error/Hypothesis/Repro for bugs), status `open` — then return to what you were doing. Don't hold it in your head until save time.
- **Id:** `YYYYMMDD-NN` (date + per-day sequence), e.g. `20260609-01`. Stable, unique, sortable.
- **Types:** `bug | improvement | debt | task | feature | initiative` · **Statuses:** `open | in-progress | parked | resolved | wont-fix` · **Severity:** `high | med | low`
- **Status changes are frontmatter edits** — items don't move between folders while alive.
- **`parked` requires `revive-when:`** — a concrete trigger ("next time the dispatcher misroutes"), not "someday".
- **Closing** fills **Resolution** briefly (link ADR/learning if useful), then **delete** the item file. No `issues/archive/` — closed GitHub issues + `git log` are enough.
- **`ACTIVE.md` / `OPEN.md` / `PARKED.md` are generated** at `/strata:save` from item frontmatter. Edit items, never the views.

## Querying

```bash
grep -rl "status: open" .                      # everything open
grep -rl "type: bug" . | xargs grep -l "severity: high"
grep -rl "area: <path>" .                      # backlog for one area
grep -rl "status: parked" .                    # parked + check revive-when
```

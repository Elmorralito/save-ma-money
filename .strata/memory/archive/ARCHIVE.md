# Archive Index — save-ma-money Memory

Cold storage. **Not surfaced via `MEMORY.md`.** Files here are preserved for history and explicit searches, not auto-loaded. Skim this index when investigating older sessions or provenance; open individual files only when needed. (Closed issues have their own cold store: `../../issues/archive/`.)

## How to access

- **Explicit ask** — "check archive for X" → scan this index, open the relevant file.
- **Grep** — `grep -rl "keyword" .strata/memory/archive/` works normally.
- **Git history** — if the file was ever committed, `git log` still has it.

## Rollover rules

- `project_state.md` sessions older than "current + last completed" → rolled into a dated `YYYY-MM-sessions-*.md` file at `/strata:save`.
- Memory whose rationale was promoted to an ADR → archived here as `source-adr-NNNN-*` for provenance.
- Content extracted during migration (e.g. 0.0.2 → 0.0.3 issues extraction) → `source-issues-extraction-*`.
- Completed actions with external artifacts → appended to `action_log.md` (never deleted, never auto-loaded).

## Files

### Action log

| File            | What it is                                                                                                                                                                           |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `action_log.md` | Append-only, external-world only: dated entries for completed actions with a durable artifact (PR, email, posted comment). Grep on demand — "did we post X?", "when did we send Y?". |

### Session snapshots

_No files yet._

### Provenance (`source-*`)

_No files yet._

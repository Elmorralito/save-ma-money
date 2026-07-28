# Cursor project config

Agent operational instructions are **canonical in this directory**.

| Path                     | Role                                                                                          |
| ------------------------ | --------------------------------------------------------------------------------------------- |
| `AGENTS.md`              | Operational guide — build, test, API status, CI                                               |
| `CLAUDE.md`              | Thin Claude Code adapter → `AGENTS.md`                                                        |
| `rules/gen-custom/*.mdc` | Always-applied / glob code-style and conventions                                              |
| `skills/create-issue/`   | `/create-issue` — GitHub issues from ISSUE_TEMPLATE                                           |
| `skills/pr-description/` | PR body drafts from [`.github/PULL_REQUEST_TEMPLATE.md`](../.github/PULL_REQUEST_TEMPLATE.md) |

**Strata / Codex entry point:** [`.agents/AGENTS.md`](../.agents/AGENTS.md) and [`.agents/CLAUDE.md`](../.agents/CLAUDE.md) symlink here. `strata_check.sh` validates those paths. Edit files in **`.cursor/`** only.

- **MCP servers:** `mcp.json` when present (validated by `mcp-config-validate` pre-commit)
- **Strata memory:** [`.strata/`](../.strata/) — see `AGENTS.md` and [`.strata/MANIFEST.md`](../.strata/MANIFEST.md)

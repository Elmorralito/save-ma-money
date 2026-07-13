# Cursor project config

Agent operational instructions are **canonical in this directory**.

| File        | Role                                            |
| ----------- | ----------------------------------------------- |
| `AGENTS.md` | Operational guide — build, test, API status, CI |
| `CLAUDE.md` | Thin Claude Code adapter → `AGENTS.md`          |

**Strata / Codex entry point:** [`.agents/AGENTS.md`](../.agents/AGENTS.md) and [`.agents/CLAUDE.md`](../.agents/CLAUDE.md) symlink here. `strata_check.sh` validates those paths. Edit files in **`.cursor/`** only.

- **Code-style rules:** `rules/gen-custom/*.mdc` (always-applied workspace rules)
- **MCP servers:** `mcp.json` (validated by `mcp-config-validate` pre-commit hook when present)
- **Strata memory:** [`.strata/`](../.strata/) — see `AGENTS.md` and [`.strata/MANIFEST.md`](../.strata/MANIFEST.md)

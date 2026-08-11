# Agent adapters — symlink layout

This directory exposes agent instruction files and shared project skills for Codex,
Strata, Claude Code, and other multi-agent tools. **Do not edit copies here** for
anything that is symlinked to `.cursor/`.

## Adapter files

| Path        | Target                 |
| ----------- | ---------------------- |
| `AGENTS.md` | `../.cursor/AGENTS.md` |
| `CLAUDE.md` | `../.cursor/CLAUDE.md` |

**Canonical source:** [`.cursor/AGENTS.md`](../.cursor/AGENTS.md) and [`.cursor/CLAUDE.md`](../.cursor/CLAUDE.md).

## Skills

| Path under `.agents/skills/`                             | Kind                        | Notes                                       |
| -------------------------------------------------------- | --------------------------- | ------------------------------------------- |
| `create-issue` → `../../.cursor/skills/create-issue`     | Symlink                     | File GitHub issues (`/create-issue`)        |
| `plan-issue` → `../../.cursor/skills/plan-issue`         | Symlink                     | Plan existing child vs epic (`/plan-issue`) |
| `pr-description` → `../../.cursor/skills/pr-description` | Symlink                     | PR body drafts                              |
| `supabase/` (local)                                      | Marketplace / local install | Gitignored — not committed                  |
| `supabase-postgres-best-practices/` (local)              | Marketplace / local install | Gitignored — not committed                  |

**Canonical source for the three project skills:** [`.cursor/skills/`](../.cursor/skills/). Edit only there; `.agents/skills/{create,plan,pr}-*` are committed symlinks. Other `.agents/skills/*` installs stay local (see root `.gitignore`).

Skills are **independent** — do not chain `/create-issue` and `/plan-issue`.

**Runtime notes**

- Cursor loads skills from `.cursor/skills/` (and may also see `.agents/skills/` depending on product config).
- Codex / Claude Code / other Agents tooling that reads `.agents/skills/` gets the same project skill content via symlink.
- Cursor-only APIs inside a skill (e.g. `Task` subagents in `/plan-issue`) use the skill’s documented **parent fallback** when those APIs are unavailable.

## Strata / Cursor

**Strata:** `strata_check.sh` validates `.agents/AGENTS.md` and `.agents/CLAUDE.md`. Strict pairing accepts `.agents/**`, `.cursor/AGENTS.md`, `.cursor/CLAUDE.md`, or `.strata/**` alongside `modules/**` changes.

**Cursor:** Code-style rules live separately in `.cursor/rules/gen-custom/`. Skill index: [`.cursor/README.md`](../.cursor/README.md).

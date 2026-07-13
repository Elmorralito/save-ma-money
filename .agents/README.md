# Agent adapters — symlink layout

This directory exposes agent instruction files for Codex, Strata, and other multi-agent tools. **Do not edit copies here.**

| File        | Target                 |
| ----------- | ---------------------- |
| `AGENTS.md` | `../.cursor/AGENTS.md` |
| `CLAUDE.md` | `../.cursor/CLAUDE.md` |

**Canonical source:** [`.cursor/AGENTS.md`](../.cursor/AGENTS.md) and [`.cursor/CLAUDE.md`](../.cursor/CLAUDE.md).

**Strata:** `strata_check.sh` validates `.agents/AGENTS.md` and `.agents/CLAUDE.md`. Strict pairing accepts `.agents/**`, `.cursor/AGENTS.md`, `.cursor/CLAUDE.md`, or `.strata/**` alongside `modules/**` changes.

**Cursor:** Code-style rules live separately in `.cursor/rules/gen-custom/`.

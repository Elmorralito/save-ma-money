# Action Log — save-ma-money

The one deliberate non-issue log: an append-only, chronological ledger of completed actions that produced an **external-world artifact** — upstream PR/issue, email sent, comment posted, external API action or registration with a durable URL. Cold tier: never auto-loaded, grepped on demand.

Format per entry:

```markdown
## YYYY-MM-DD — <short session label>

- **<issue-id or label>** — <what was done> (<durable external URL>). <one line why it mattered>.
```

What does NOT qualify (keep noise out):

- Internal code edits — that's `git log`
- File reorganization — that's session narrative
- Decisions — that's ADR territory
- Work state — that's `issues/`

---

## 2026-07-15 — PPT-039 PR #91 babysit

- **PPT-039 / #91** — Dismissed CodeQL alerts 4–5 (OAuth PKCE cookie FPs) and replied on GHAS review threads ([PR #91](https://github.com/Elmorralito/save-ma-money/pull/91)). Clears merge-blocking security check noise for intentional PKCE HttpOnly cookies.

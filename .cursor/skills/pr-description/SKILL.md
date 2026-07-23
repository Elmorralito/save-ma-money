---
name: pr-description
description:
  Drafts pull request descriptions from the full branch commit history and
  diff vs base (not tip-only), merging repo PR/issue templates when present. Never
  includes secrets, tokens, or credentials in the PR text. Use when the user asks for
  a PR description, PR body, pull request write-up, or text for gh pr create / GitHub
  PR in this repository.
disable-model-invocation: true
---

# PR description (project)

Draft a paste-ready GitHub PR body for the **current branch**. Gather evidence with
the checklist below first. Do not invent CI status, test results, or issue links.
Prefer user-facing / operator impact over implementation trivia.

**Be extra careful:** never put secrets, tokens, credentials, or other sensitive
values in the PR title, body, commit table, checks, QA, risks, or references
(see Secrets redaction below).

This skill lives at `.cursor/skills/pr-description/` (repo-only). Do not depend on
`~/.cursor/skills/pr-description/`.

## Gather checklist (run before drafting)

Copy and complete. Skip nothing that applies.

```
PR description gather:
- [ ] 1. `git status -sb` — branch, tracking, dirty tree
- [ ] 2. Resolve `<base>`: prefer `origin/main`, else `main`, else merge-base with upstream
- [ ] 3. `git log --oneline <base>...HEAD` — ALL commits on the branch
- [ ] 4. `git log <base>...HEAD --format='%h %s'` (skim bodies with
        `git log <base>...HEAD` when subjects are thin)
- [ ] 5. `git diff --stat <base>...HEAD` — file change overview
- [ ] 6. Skim `git diff <base>...HEAD` for behavior (migrations, auth, API, env — not every hunk);
        never copy secret values from diffs into notes for the PR body
- [ ] 7. Load templates / conventions (see Templates below); note title format if PPT-NNN known
- [ ] 8. Checks/validation: only what was run or stated in this session / by the user
        (no secret values from command output or logs)
- [ ] 9. Risks/caveats: derive from migrations, secrets/env *names*, deferred work, breaking
        behavior, mixed unrelated concerns (suggest split if mixed)
- [ ] 10. Redact secrets: scan the entire draft for tokens, keys, passwords, connection
         strings (see Secrets redaction) before presenting to the user
```

Use **all** of `<base>...HEAD` (commits + diff), never the tip commit alone.

## Secrets redaction (mandatory)

Be **extra careful**. PR descriptions are public (or broadly visible). Treat any
credential-like string in diffs, logs, or commit messages as **do not paste**.

**Never include** (verbatim or partial fragments that remain usable):

- API keys, JWTs, refresh/access tokens, session cookies, PKCE verifiers
- Passwords, private keys, service-role / anon keys, webhook secrets
- Full `DATABASE_URL` / connection strings with credentials; OAuth client secrets
- Contents of `.env`, `environments/**/.env`, or similar secret files
- Personal data (emails/phones) unless already public in the issue and necessary —
  prefer placeholders (`AUTH_SMOKE_EMAIL`, `user@example.local`)

**Do:** name env _variables_ and config knobs only (`SUPABASE_SERVICE_ROLE_KEY` must
be set; never paste its value). Say “configured in local `.env` (not committed)” when
relevant. Quote commit subjects/bodies only after confirming they contain no secrets.
If a diff exposes a secret, warn the user to rotate it and scrub history if committed —
do not quote the secret in the PR text.

## Templates

**Structure SSOT:** [`.github/PULL_REQUEST_TEMPLATE.md`](../../../.github/PULL_REQUEST_TEMPLATE.md).
Fill that template (do not invent alternate section orders or drop required headings).

| Source                 | Path / pattern                                                                                                                |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| GitHub PR template     | [`.github/PULL_REQUEST_TEMPLATE.md`](../../../.github/PULL_REQUEST_TEMPLATE.md) — **required structure**                      |
| Issue / PR body drafts | [`docs/issues/README.md`](../../../docs/issues/README.md) Parts I–V; still-separate `docs/issues/PPT-044*.md` / `PPT-045*.md` |
| Title notation         | `.cursor/rules/gen-custom/github_issue_conventions.mdc` → `{semantic}/PPT-{NNN}: [{domain}] {sentence case}`                  |

## Output format

Write Markdown ready for `gh pr create` by **filling** `.github/PULL_REQUEST_TEMPLATE.md`:

1. Optional preamble: **Branch**, **Base**, commit/file counts, **Suggested title**
2. **Summary** — 2–4 sentences (why + what shipped)
3. **Out of scope / Highlights** — deferred work vs notable wins
4. **Changes** — grouped by area; behavior, not every hunk
5. **File changes** — `<details>` with `--stat` or path list (no secrets)
6. **Commits** — `hash` + subject (or short narrative if many)
7. **Checks, tests, and validation already done** — only observed results
8. **QA / test plan** — checkbox verification remaining
9. **Risks** — `[!CAUTION]` alert (breaking / migrations / env _names_ / follow-ups)
10. **Caveats** — `[!WARNING]` alert (limitations / “works if…”); use “None identified” if empty
11. **References** — issues / design docs only if known

Tone/shape reference: [examples.md](examples.md).

## Rules

- Base the description on **all** commits and the full diff vs `<base>`.
- Prefer user-facing / operator impact over implementation trivia.
- If unrelated concerns are mixed on the branch, call that out and suggest a split.
- Do not invent test results, CI status, or issue links.
- Keep the Summary short; put detail in Changes / Risks / Caveats / Out of scope.
- Keep the **template** section order; use `[!CAUTION]` for Risks and `[!WARNING]` for Caveats.
- Never reveal secrets, tokens, credentials, or sensitive values in the PR description.

## Additional resources

- Example shape/tone: [examples.md](examples.md)

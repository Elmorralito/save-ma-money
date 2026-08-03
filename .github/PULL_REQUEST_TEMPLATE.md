<!--
Title: prefer `{semantic}/PPT-{NNN}: [{domain}] {Sentence case}` when a program ID applies
       (see .cursor/rules/gen-custom/github_issue_conventions.mdc). Otherwise Conventional Commits.
Never paste secrets, tokens, passwords, private keys, or credentialed connection strings.
Name env *variables* only (e.g. SUPABASE_SERVICE_ROLE_KEY) — never their values.
Base the description on ALL commits + full diff vs the PR base (not tip-only).
-->

**Branch:** `<!-- branch -->` · **Base:** `main` · **<!-- N --> commits** · **<!-- N --> files**

<!-- Optional: **Suggested title:** `feat/PPT-0NN: [api] …` -->

## Summary

<!-- 2–4 sentences: why this change exists and what shipped. Out-of-scope goes below. -->

## Out of scope / Highlights

**Out of scope**

- <!-- deferred work, non-goals, follow-up issues -->

**Highlights**

- <!-- optional: notable wins / reviewer callouts that are not risks -->

## Changes

<!-- Group by area (API / model / migrations / docs / tests / ops / CI). Describe behavior, not every hunk. -->

**<!-- area -->**

- <!-- what changed -->

## File changes

<details>
<summary>File changes (~N files)</summary>

```
<!-- paste git diff --stat <base>...HEAD or a compact path list (no secret values) -->
```

</details>

## Commits

- `<!-- hash -->` <!-- subject -->

## Checks, tests, and validation already done

<!-- Only what was actually run or observed. Mark unverified items. Do not invent green CI. -->

- <!-- command / environment — pass|fail|not run -->

## QA / test plan

- [ ] <!-- remaining or recommended verification -->

## Risks

> [!CAUTION]
>
> ### Risks
>
> - <!-- merge/ops risks: breaking changes, migrations, env *names*, follow-ups reviewers must not miss -->
> - <!-- or: None identified -->

## Caveats

> [!WARNING]
>
> ### Caveats
>
> - <!-- limitations, deferred behavior, “works if…” notes -->
> - <!-- or: None identified -->

## Web security checklist (PPT-056 / #121)

<!-- Fill when the PR touches `modules/web/**` or BFF cookie/auth paths. Otherwise delete this section. -->

- [ ] No JWTs / access tokens in `localStorage` / `sessionStorage` (BFF HttpOnly `papita_sid` only)
- [ ] Cookie flags reviewed for the touched path (`HttpOnly` / `Secure` when not DEBUG / `SameSite`)
- [ ] CSRF: mutations send `X-Papita-CSRF`; token stays in memory (not WebStorage)
- [ ] No secrets in `VITE_*` (public bundle only); gitleaks-aware for accidental embeds
- [ ] `pnpm web:audit` considered (or Dependabot `npm-web`); no known high prod vulns left untracked
- [ ] CSP: documented posture OK for this PR (full CSP headers owned by launch packaging / #122)

## References

- <!-- issue IDs, design docs, parent epic — only if known -->

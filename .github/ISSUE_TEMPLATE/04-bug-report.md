---
name: Bug report
about: Something broken in model, API, CI, or ops tooling
title: "fix/PPT-0NN: [domain] Short bug title"
labels: ["bug"]
---

<!--
Prefer a PPT id when the bug maps to a program track; otherwise fix(domain): …
Never paste secrets, tokens, or credentialed connection strings.
-->

**Parent program / epic (if any):** <!-- #28 / #42 / none -->

## Summary

<!-- What is broken and user/operator impact. -->

## To reproduce

1. <!-- -->
2. <!-- -->
3. <!-- -->

## Expected

<!-- -->

## Actual

<!-- -->

## Environment

| Item            | Value                                    |
| --------------- | ---------------------------------------- |
| Branch / commit | <!-- -->                                 |
| `PAPITA_ENV`    | local / staging / …                      |
| Runtime         | Compose API (`make api-up`) / CI         |
| DB              | Docker Postgres / other (no credentials) |

## Logs / evidence

<!-- Redact secrets. Prefer paths + error types over full dumps. -->

## Acceptance criteria

- [ ] Bug no longer reproduces under steps above
- [ ] Regression test or documented manual check added when practical

## References

- <!-- Related issues / PRs / files -->

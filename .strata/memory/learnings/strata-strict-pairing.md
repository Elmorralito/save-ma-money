---
trigger: before git commit when modules/ or bin/ changed
applies-when: modules/**, bin/**
origin: success
---

**Lesson:** Pre-commit `strata-validate` runs strict mode locally. Pair every `modules/**` or `bin/**` diff with an
update under `.strata/` (or `.agents/AGENTS.md` / `.agents/CLAUDE.md`), then restage both before retrying commit. CI enforces the same
rule on PRs via `strata-check.yml`.

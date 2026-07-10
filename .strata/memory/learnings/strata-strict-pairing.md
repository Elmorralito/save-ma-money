---
trigger: before git commit when modules/ or deploy/ changed
applies-when: modules/**, deploy/**
origin: success
---

**Lesson:** Pre-commit `strata-validate` runs strict mode locally. Pair every `modules/**` or `deploy/**` diff with an
update under `.strata/` (or `AGENTS.md` / `CLAUDE.md`), then restage both before retrying commit. CI enforces the same
rule on PRs via `strata-check.yml`.

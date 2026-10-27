---
trigger: before merging Dependabot PRs that touch modules/** without agent memory
applies-when: modules/**, .strata/memory/learnings/**
origin: failure
---

**Lesson:** Dependabot bumps under `modules/**` must include a `.strata/` pairing update (learning or adapter touch) or CI strata-check fails in strict mode—even when the bump is mechanical.
Mon Oct 26 21:17:32 -05 2026

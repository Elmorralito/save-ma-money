---
trigger: before adding or wiring modules/ingestor* packages
applies-when: modules/ingestor-core/**, modules/ingestors/**, bin/make/ingestor.mk
origin: success
---

**Lesson:** Gate ingestor scaffolds with `ingestor-ci.yml` + `bin/make/ingestor.mk`; keep root pytest `--cov`/`testpaths` on model/api only (coverage ≥80% is PPT-084). Split Make by language under `bin/{bash,python,make}/` and path-filter domain CI to the matching `*.mk` — never the whole root Makefile.

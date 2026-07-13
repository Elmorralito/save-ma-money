---
trigger: before committing changes under modules/api/src
applies-when: modules/api/**
origin: failure
---

**Lesson:** Run `flake8`, `pylint`, and `mypy` on touched API files before commit. Import enum types at module level in
`schemas/converters.py` (quoted forward refs fail F821). Use keyword-only query params (`*`) when FastAPI handlers exceed
pylint's positional-arg limit (R0917). Guard `UUID | None` from DTOs with an explicit helper before passing to services.
Do not name FastAPI params `format` — use `export_format` + `Query(alias="format")` (W0622). Split fat mappers when
R0914 (too-many-locals) trips. Stage matching `.strata/` updates whenever `modules/**` changes so `strata-validate`
strict pairing passes.

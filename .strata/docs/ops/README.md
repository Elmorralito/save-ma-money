# Ops — save-ma-money

Procedures you perform: runbooks (`<slug>.md`), incident patterns (`incidents/<symptom>.md` — symptom, impact, root cause, remediation, verification), and `release-rollback.md` (how to roll back a bad release — write it before you need it).

The discriminator: _steps you execute_ live here; _facts you look up_ live in `../reference/`. Never store secret values — env var names and secret surfaces only.

| Procedure                      | Path                                                                                                                                                                 |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Env files / `PAPITA_ENV`       | [`environments.md`](environments.md) → [`environments/README.md`](../../../environments/README.md)                                                                   |
| API uvicorn (Compose, PPT-045) | `make api-up` → [`modules/api/README.md`](../../../modules/api/README.md) + [`docker/api/Dockerfile`](../../../docker/api/Dockerfile)                                |
| Model PyPI publish (PPT-024)   | `make package-model` + [`publish-model.yml`](../../../.github/workflows/publish-model.yml) → [`modules/model/README.md`](../../../modules/model/README.md) § Install |
| Redis B0/B1 checklist          | [`docs/ops/redis-deploy-checklist.md`](../../../docs/ops/redis-deploy-checklist.md) + [design § Ops](../../../docs/design/README.md#ops-redis--optional-b1-pooler)   |
| PPT-044 API hardening (design) | [`docs/design/ARCHITECTURE.md` Part VIII](../../../docs/design/ARCHITECTURE.md#part-viii--post-mvp-api-hardening-ppt-044-89)                                         |

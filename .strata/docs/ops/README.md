# Ops — save-ma-money

Procedures you perform: runbooks (`<slug>.md`), incident patterns (`incidents/<symptom>.md` — symptom, impact, root cause, remediation, verification), and `release-rollback.md` (how to roll back a bad release — write it before you need it).

The discriminator: _steps you execute_ live here; _facts you look up_ live in `../reference/`. Never store secret values — env var names and secret surfaces only.

| Procedure                         | Path                                                                                                                                          |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Env files / `PAPITA_ENV`          | [`environments.md`](environments.md) → [`environments/README.md`](../../../environments/README.md)                                            |
| B1 Supabase pooler deploy + smoke | [`b1-supabase-deploy-checklist.md`](b1-supabase-deploy-checklist.md) → human [`docs/ops/`](../../../docs/ops/b1-supabase-deploy-checklist.md) |

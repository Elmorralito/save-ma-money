---
trigger: before changing auth, register, login, users password storage, or JWT issuance
applies-when: modules/api/**/auth*, modules/api/**/security*, modules/api/**/supabase*, modules/model/**/users*
origin: failure
---

**Lesson:** Own **user management and authentication in the Supabase project** (Auth dashboard + JWKS). Papita API only verifies Supabase access JWTs and provisions/links `papita_transactions.users` by Auth `sub`.

Schema contract: `users.id` **is** Supabase Auth `auth.users.id` / JWT `sub`; `auth_provider='supabase'` and `password` is `NULL` for Auth-managed rows. Local Argon2 passwords are only for `auth_provider='local'` (unit tests). Do not revive local password issuance as the MVP IdP or treat Compose Postgres as the identity store — Docker must inject `AUTH_PROVIDER` / `SUPABASE_*`; smoke emails need real domains (not `.local` / `example.com`). On Supabase-hosted Postgres you may optionally add `FOREIGN KEY (id) REFERENCES auth.users(id)`; Docker B0 has no `auth` schema so that FK is skipped.

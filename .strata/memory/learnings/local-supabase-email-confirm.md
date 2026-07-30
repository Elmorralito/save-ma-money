---
trigger: before changing local register/login or AUTH_AUTO_CONFIRM_EMAIL
applies-when: modules/api/**/supabase_auth*, modules/api/**/auth*, modules/api/**/bff_auth*, environments/local/**
origin: failure
---

**Lesson:** For local Supabase Auth, prefer Admin `create_user` with `email_confirm=true` when `AUTH_AUTO_CONFIRM_EMAIL` is on (default for `PAPITA_ENV=local`) so anon `sign_up` does not burn SMTP and hit `over_email_send_rate_limit`. On login, Admin-confirm only after verifying `email_confirmed_at` is null — never treat every `invalid_credentials` as unconfirmed (wrong passwords must stay 401).

---
name: save-ma-money State
description: Auth + user management owned by Supabase project; Compose injects SUPABASE_*.
---

## WHERE WE LEFT OFF (current)

**Standing rule:** move / keep **user management and authentication in the Supabase
project**. Papita API verifies JWTs + links `users` by `sub` — it is not the IdP.

### Last completed (this session)

- PPT-045 / #93: uvicorn packaging — `make api-up` starts Compose API (in-container
  CMD); Settings `HOST`/`PORT` unused for bind; docs + redis smoke aligned

### Next action

- Land PPT-045 PR; close #93 when merged
- Do not commit `environments/**/.env`

### Uncommitted / staging notes

- Do not commit `environments/**/.env`
- B0 API runtime is Docker-only (`make api-up` / `stack-up`)

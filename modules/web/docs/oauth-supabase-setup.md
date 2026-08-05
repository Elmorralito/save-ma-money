# OAuth with Supabase + Google / GitHub (SPA BFF)

End-to-end operator guide for **Continue with Google** / **Continue with GitHub** on Papita login and register.

The SPA never holds JWTs. Buttons full-page navigate to BFF routes; the API sets the HttpOnly `papita_sid` cookie after Supabase PKCE completes.

| Piece                            | Value                                                                                                 |
| -------------------------------- | ----------------------------------------------------------------------------------------------------- |
| SPA start                        | `GET /api/v1/bff/auth/oauth/{google\|github}?return_to=/dashboard`                                    |
| SPA callback                     | `GET /api/v1/bff/auth/oauth/callback` → set `papita_sid` → 302 to SPA                                 |
| Bearer twin (token clients only) | `GET /api/v1/auth/oauth/{provider}` + `/auth/oauth/callback` (returns JWT JSON — **not** for the SPA) |
| UI                               | `LoginPage` / `RegisterPage` → `OAuthProviderButtons`                                                 |

Related: [`modules/web/README.md`](../README.md) § BFF cookie auth, [`environments/local/.env.example`](../../../environments/local/.env.example), [`modules/api/README.md`](../../api/README.md).

---

## Architecture (what must match)

```text
Browser (:5173 or :3000)
  → GET /api/v1/bff/auth/oauth/google   (same-origin; Vite/nginx proxies /api)
  → 302 Supabase / Google
  → Google consent
  → Supabase Auth callback
       https://<PROJECT_REF>.supabase.co/auth/v1/callback
  → 302 Papita BFF callback (allowlisted Redirect URL)
       http://localhost:5173/api/v1/bff/auth/oauth/callback   # Vite
  → API exchanges code + PKCE cookies → papita_sid → 302 /dashboard
```

Three URLs are easy to confuse:

| URL                                                    | Owner                      | Purpose                    |
| ------------------------------------------------------ | -------------------------- | -------------------------- |
| `https://<PROJECT_REF>.supabase.co/auth/v1/callback`   | Google / GitHub OAuth app  | IdP → Supabase             |
| `http://localhost:5173/api/v1/bff/auth/oauth/callback` | Supabase **Redirect URLs** | Supabase → Papita SPA/BFF  |
| Papita `SUPABASE_URL` / anon key                       | `environments/local/.env`  | API talks to Supabase Auth |

Google/GitHub **Client ID** and **Client Secret** live only in the Supabase provider UI — **not** in Papita `.env`.

---

## Prerequisites

1. Supabase project with Auth enabled.
2. Local stack: `AUTH_PROVIDER=supabase`, `SUPABASE_URL`, `SUPABASE_ANON_KEY` in `environments/local/.env`.
3. API image that includes BFF OAuth routes (`make api-up` after pulling this code).
4. SPA: `make web-dev` (Vite `:5173`) or `make web-up` (nginx `:3000`).
5. `ALLOWED_ORIGINS` includes the SPA origin(s), e.g.:

   ```bash
   ALLOWED_ORIGINS='["http://localhost:3000","http://127.0.0.1:3000","http://localhost:5173","http://127.0.0.1:5173"]'
   ```

   If your shell exports a stale `ALLOWED_ORIGINS`, Compose can ignore the file. Prefer:

   ```bash
   unset ALLOWED_ORIGINS
   make api-up
   ```

---

## 1. Google Cloud OAuth client

1. Open [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **Credentials**.
2. Configure the **OAuth consent screen** if prompted (External is fine for local/dev).
3. **Create credentials** → **OAuth client ID** → type **Web application**.
4. Under **Authorized redirect URIs**, add **exactly** Supabase’s Auth callback (shown on the Supabase Google provider page):

   ```text
   https://<PROJECT_REF>.supabase.co/auth/v1/callback
   ```

   Do **not** put `localhost:5173/...` here — that belongs in Supabase Redirect URLs (step 3).

5. Create → copy **Client ID** and **Client Secret**.

---

## 2. GitHub OAuth App

1. GitHub → **Settings** → **Developer settings** → [**OAuth Apps**](https://github.com/settings/developers) → **New OAuth App**.
2. **Homepage URL:** `http://localhost:5173` (or your SPA origin).
3. **Authorization callback URL:** same Supabase callback as Google:

   ```text
   https://<PROJECT_REF>.supabase.co/auth/v1/callback
   ```

4. Register → copy **Client ID**; generate **Client Secret**.

---

## 3. Enable providers in Supabase

### Google

1. Supabase Dashboard → project → **Authentication** → **Providers** → **Google**.
2. Enable **Sign in with Google**.
3. Paste Google **Client ID** + **Client Secret**.
4. Save.

### GitHub

1. Same menu → **GitHub**.
2. Enable the provider.
3. Paste GitHub **Client ID** + **Client Secret**.
4. Save.

Until a provider is enabled here, Supabase returns:

```text
Unsupported provider: provider is not enabled
```

---

## 4. Allowlist Papita BFF callbacks (Supabase Redirect URLs)

**Authentication** → **URL Configuration** → **Redirect URLs**. Add every host you actually use:

| How you run the SPA                          | Redirect URL to add                                    |
| -------------------------------------------- | ------------------------------------------------------ |
| `make web-dev` (Vite)                        | `http://localhost:5173/api/v1/bff/auth/oauth/callback` |
| `make web-up` (nginx)                        | `http://localhost:3000/api/v1/bff/auth/oauth/callback` |
| Direct API / no SPA proxy (rare for buttons) | `http://localhost:8000/api/v1/bff/auth/oauth/callback` |

Optional Bearer token-client callback (not used by SPA buttons):

```text
http://localhost:8000/api/v1/auth/oauth/callback
```

Also keep email-confirm landing URLs if you use password signup confirmation (PPT-068), e.g. `http://localhost:5173/auth/confirm`.

Optional local hint in `.env` (API still prefers the browser-facing callback from `Referer` / Origin when allowlisted):

```bash
# SUPABASE_OAUTH_REDIRECT_TO="http://localhost:5173/api/v1/bff/auth/oauth/callback"
```

---

## 5. Start Papita and smoke-test

```bash
unset ALLOWED_ORIGINS
make api-up          # rebuild API so /bff/auth/oauth/* exists
make web-dev         # http://localhost:5173
```

1. Open `http://localhost:5173/login` or `/register`.
2. Click **Continue with Google** (or GitHub).
3. Complete IdP consent.
4. Expect redirect to `/dashboard` with an authenticated session.
5. Confirm DevTools → Application → Cookies: `papita_sid` on Path `/api` (HttpOnly). No access/refresh JWT in `localStorage` / JS.

Failure path: `/login?oauth_error=1` with an on-page alert.

### Quick API probe (Vite proxy)

```bash
curl -sS -D - -o /dev/null \
  -H 'Referer: http://localhost:5173/login' \
  'http://localhost:5173/api/v1/bff/auth/oauth/google?return_to=/dashboard'
```

Expect **302** to `…supabase.co/auth/v1/authorize?…provider=google` and
`redirect_to=http://localhost:5173/api/v1/bff/auth/oauth/callback`.

---

## 6. Troubleshooting

| Symptom                                              | Likely cause                                                           | Fix                                                                 |
| ---------------------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `Unsupported provider: provider is not enabled`      | Provider off or secrets missing in Supabase                            | Enable Google/GitHub; paste Client ID/Secret; Save                  |
| 404 on `/api/v1/bff/auth/oauth/google`               | Old API image                                                          | `make api-up` on a branch that includes BFF OAuth                   |
| Redirect / cookie host mismatch (`:8000` vs `:5173`) | `ALLOWED_ORIGINS` missing `:5173`, or shell override                   | Fix `.env`, `unset ALLOWED_ORIGINS`, recreate API                   |
| Google error about redirect_uri mismatch             | Wrong URI on the **Google** OAuth client                               | Must be `https://<REF>.supabase.co/auth/v1/callback`                |
| Lands on login with `oauth_error=1`                  | PKCE cookies missing, exchange failed, or Redirect URL not allowlisted | Re-check Supabase Redirect URLs; use same host for start + callback |
| Buttons missing                                      | SPA not on current branch / stale Vite                                 | Restart `make web-dev`; hard-refresh                                |

---

## 7. Security / product notes

- SPA must **not** call Bearer `/auth/oauth/*` or `/auth/sso`, or store `code_verifier` / JWTs in JS.
- Favicons for buttons are self-hosted under `public/brand/` (CSP `img-src 'self'`).
- Google/GitHub emails are treated as IdP-verified — no second password email-confirm gate for those sessions.
- Staging/prod: use HTTPS SPA origins in Supabase Redirect URLs and `ALLOWED_ORIGINS`; set cookie `Secure` via non-DEBUG / `AUTH_COOKIE_SECURE`.

---

## Checklist

- [ ] Google OAuth Web client → Supabase Auth callback URI
- [ ] GitHub OAuth App → same Supabase Auth callback URI (if using GitHub)
- [ ] Supabase Providers → Google (and/or GitHub) enabled + secrets saved
- [ ] Supabase Redirect URLs include Vite and/or nginx BFF callbacks
- [ ] `ALLOWED_ORIGINS` includes SPA origins; shell `ALLOWED_ORIGINS` unset if stale
- [ ] `make api-up` + `make web-dev`
- [ ] Login/Register button → IdP → `/dashboard` + `papita_sid`

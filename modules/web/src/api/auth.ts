import { apiFetch } from "@/api/http";
import { clearCsrfToken, setCsrfToken } from "@/api/csrf";

export type BffUser = {
  id: string;
  username: string;
  email: string;
  display_name: string | null;
  phone: string | null;
  provider: string;
  auth_provider: string;
  created_at: string;
};

export type BffSession = {
  authenticated: boolean;
  user: BffUser | null;
  csrf_token: string | null;
  session_backend: string | null;
};

function rememberCsrf(session: BffSession): BffSession {
  if (session.authenticated && session.csrf_token) {
    setCsrfToken(session.csrf_token);
  }
  if (!session.authenticated) {
    clearCsrfToken();
  }
  return session;
}

/** GET /api/v1/bff/auth/session — SPA bootstrap (200 even when anonymous). */
export async function getBffSession(signal?: AbortSignal): Promise<BffSession> {
  const { data } = await apiFetch<BffSession>("/api/v1/bff/auth/session", {
    signal,
    skipAuthRefresh: true,
  });
  return rememberCsrf(data);
}

/** POST /api/v1/bff/auth/login — sets HttpOnly session cookie; no JWT in body. */
export async function bffLogin(input: { email: string; password: string }): Promise<BffSession> {
  const { data } = await apiFetch<BffSession>("/api/v1/bff/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
    skipAuthRefresh: true,
  });
  return rememberCsrf(data);
}

/** POST /api/v1/bff/auth/register — creates user; does not open a session. */
export async function bffRegister(input: {
  email: string;
  password: string;
  display_name?: string;
}): Promise<BffUser> {
  const { data } = await apiFetch<BffUser>("/api/v1/bff/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
    skipAuthRefresh: true,
  });
  return data;
}

/** POST /api/v1/bff/auth/refresh — rotate tokens server-side. */
export async function bffRefresh(signal?: AbortSignal): Promise<BffSession> {
  const { data } = await apiFetch<BffSession>("/api/v1/bff/auth/refresh", {
    method: "POST",
    signal,
    skipAuthRefresh: true,
  });
  return rememberCsrf(data);
}

/** POST /api/v1/bff/auth/logout — clears cookie + server session. */
export async function bffLogout(): Promise<void> {
  await apiFetch<undefined>("/api/v1/bff/auth/logout", {
    method: "POST",
    skipAuthRefresh: true,
  });
  clearCsrfToken();
}

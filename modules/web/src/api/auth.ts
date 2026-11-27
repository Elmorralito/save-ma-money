import {
  apiFetch,
  clearAuthTokens,
  getAccessExpiresAt,
  getAccessToken,
  getRefreshToken,
  isPapitaApiError,
  setAuthTokens,
} from "@/api/http";

export type BffUser = {
  id: string;
  username: string;
  email: string;
  display_name: string | null;
  phone: string | null;
  provider?: string;
  provider_type?: string;
  auth_provider: string;
  created_at: string | null;
};

export type BffSession = {
  authenticated: boolean;
  user: BffUser | null;
  csrf_token: string | null;
  session_backend: string | null;
  access_expires_at: number | null;
};

type TokenPayload = {
  access_token: string;
  token_type?: string;
  expires_in?: number | null;
  refresh_token?: string | null;
};

function unauthenticatedSession(): BffSession {
  return {
    authenticated: false,
    user: null,
    csrf_token: null,
    session_backend: "bearer",
    access_expires_at: null,
  };
}

/** Resolve current session via Bearer token or HttpOnly cookie + ``GET /api/v1/auth/me``. */
export async function getBffSession(signal?: AbortSignal): Promise<BffSession> {
  try {
    const { data: user } = await apiFetch<BffUser>("/api/v1/auth/me", {
      signal,
      skipAuthRefresh: true,
    });
    return {
      authenticated: true,
      user: {
        ...user,
        provider: user.provider ?? user.provider_type ?? "email",
      },
      csrf_token: null,
      session_backend: getAccessToken() ? "bearer" : "cookie",
      access_expires_at: getAccessExpiresAt(),
    };
  } catch (error) {
    if (isPapitaApiError(error) && (error.status === 401 || error.status === 403)) {
      clearAuthTokens();
      return unauthenticatedSession();
    }
    throw error;
  }
}

/** ``POST /api/v1/auth/login`` (OAuth2 form) + ``GET /api/v1/auth/me``. */
export async function bffLogin(input: { email: string; password: string }): Promise<BffSession> {
  const form = new URLSearchParams({
    username: input.email.trim(),
    password: input.password,
  });
  const { data: token } = await apiFetch<TokenPayload>("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
    skipAuthRefresh: true,
  });
  setAuthTokens({
    accessToken: token.access_token,
    refreshToken: token.refresh_token ?? null,
    expiresIn: token.expires_in ?? 3600,
  });
  return getBffSession();
}

/** ``POST /api/v1/auth/register`` — creates user; does not open a session. */
export async function bffRegister(input: {
  email: string;
  password: string;
  display_name?: string;
}): Promise<BffUser & { email_confirmation_required: boolean }> {
  const { data } = await apiFetch<BffUser & { email_confirmation_required?: boolean }>(
    "/api/v1/auth/register",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
      skipAuthRefresh: true,
    },
  );
  return {
    ...data,
    provider: data.provider ?? data.provider_type ?? "email",
    email_confirmation_required: Boolean(data.email_confirmation_required),
  };
}

/** ``POST /api/v1/auth/resend-confirmation`` — soft-success 204; no session. */
export async function bffResendConfirmation(input: {
  email: string;
  email_redirect_to?: string;
}): Promise<void> {
  const redirect =
    input.email_redirect_to ??
    (typeof window !== "undefined" ? `${window.location.origin}/auth/confirm` : undefined);
  await apiFetch<undefined>("/api/v1/auth/resend-confirmation", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: input.email.trim(),
      ...(redirect ? { email_redirect_to: redirect } : {}),
    }),
    skipAuthRefresh: true,
  });
}

/** ``POST /api/v1/auth/refresh`` — rotate tokens. */
export async function bffRefresh(signal?: AbortSignal): Promise<BffSession> {
  const refresh = getRefreshToken();
  if (!refresh) {
    clearAuthTokens();
    return unauthenticatedSession();
  }
  const { data: token } = await apiFetch<TokenPayload>("/api/v1/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
    signal,
    skipAuthRefresh: true,
  });
  setAuthTokens({
    accessToken: token.access_token,
    refreshToken: token.refresh_token ?? refresh,
    expiresIn: token.expires_in ?? 3600,
  });
  return getBffSession(signal);
}

/** ``POST /api/v1/auth/logout`` — clears in-memory tokens and HttpOnly session cookie. */
export async function bffLogout(): Promise<void> {
  const access = getAccessToken();
  const refresh = getRefreshToken();
  clearAuthTokens();
  try {
    await apiFetch<undefined>("/api/v1/auth/logout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...(access ? { access_token: access } : {}),
        refresh_token: refresh ?? "local-stateless",
      }),
      skipAuthRefresh: true,
    });
  } catch {
    // Stateless local mode returns 501 after clearing the HttpOnly cookie.
  }
}

export type BffOAuthProvider = "google";

/** Same-origin OAuth start URL (`/api/v1/auth/oauth/{provider}?follow=true&return_to=...`). */
export function bffOAuthStartUrl(
  provider: BffOAuthProvider,
  returnTo: string = "/dashboard",
): string {
  const params = new URLSearchParams({ follow: "true", return_to: returnTo });
  return `/api/v1/auth/oauth/${provider}?${params.toString()}`;
}

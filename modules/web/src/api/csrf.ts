/**
 * In-memory CSRF token for BFF cookie-authenticated mutations (PPT-049).
 *
 * Not persisted to localStorage — JWTs never live in JS storage; the CSRF token
 * is only a mutation header companion to the HttpOnly session cookie.
 */

let csrfToken: string | null = null;

export function getCsrfToken(): string | null {
  return csrfToken;
}

export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

export function clearCsrfToken(): void {
  csrfToken = null;
}

/**
 * Interpret Supabase email-confirm redirect query/hash (PPT-068).
 *
 * Presentation only — never persists tokens from the URL. BFF login remains the
 * session path after confirmation.
 */

export type ConfirmLandingStatus = "success" | "error" | "unknown";

export type ConfirmLandingInterpretation = {
  status: ConfirmLandingStatus;
  /** Short user-facing copy (never raw provider dumps beyond allowlisted error text). */
  message: string;
  /** True when the redirect included session material we intentionally ignore. */
  discardedSessionFragment: boolean;
};

function readParams(raw: string): URLSearchParams {
  const trimmed = raw.trim();
  if (!trimmed) {
    return new URLSearchParams();
  }
  if (trimmed.startsWith("?")) {
    return new URLSearchParams(trimmed.slice(1));
  }
  if (trimmed.startsWith("#")) {
    return new URLSearchParams(trimmed.slice(1));
  }
  return new URLSearchParams(trimmed);
}

function firstParam(params: URLSearchParams, keys: string[]): string | null {
  for (const key of keys) {
    const value = params.get(key);
    if (value !== null && value.trim() !== "") {
      return value.trim();
    }
  }
  return null;
}

function sanitizeErrorMessage(raw: string): string {
  const decoded = decodeURIComponent(raw.replace(/\+/g, " ")).trim();
  if (decoded.length === 0) {
    return "Email confirmation failed. Request a new link from sign-in, then try again.";
  }
  // Cap length so IdP dumps do not flood the UI.
  return decoded.length > 240 ? `${decoded.slice(0, 240)}…` : decoded;
}

/**
 * Map confirm redirect ``search`` + ``hash`` into a landing status.
 *
 * Supabase may use query (``type``, ``token_hash``, ``error``) or a hash fragment
 * that includes ``access_token``. Fragments must never be stored in JS storage.
 */
export function interpretEmailConfirmParams(input: {
  search: string;
  hash: string;
}): ConfirmLandingInterpretation {
  const query = readParams(input.search);
  const hash = readParams(input.hash);

  const error =
    firstParam(query, ["error_description", "error"]) ??
    firstParam(hash, ["error_description", "error"]);
  if (error !== null) {
    return {
      status: "error",
      message: sanitizeErrorMessage(error),
      discardedSessionFragment: Boolean(firstParam(hash, ["access_token", "refresh_token"])),
    };
  }

  const discardedSessionFragment = Boolean(firstParam(hash, ["access_token", "refresh_token"]));
  const type = (firstParam(query, ["type"]) ?? firstParam(hash, ["type"]) ?? "").toLowerCase();
  const hasConfirmSignal =
    discardedSessionFragment ||
    type === "signup" ||
    type === "email" ||
    type === "email_change" ||
    query.has("token_hash") ||
    query.has("token") ||
    query.has("code") ||
    hash.has("token_hash") ||
    hash.has("code");

  if (hasConfirmSignal) {
    return {
      status: "success",
      message:
        "Your email is confirmed. Sign in to open a secure session — confirmation links never store tokens in the browser.",
      discardedSessionFragment,
    };
  }

  return {
    status: "unknown",
    message:
      "If you already confirmed your email, sign in to continue. Otherwise open the link from your inbox again.",
    discardedSessionFragment: false,
  };
}

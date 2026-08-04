import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";

import { interpretEmailConfirmParams } from "@/auth/emailConfirmLanding";
import { Button } from "@/components/ui/button";

/**
 * Same-origin landing for Supabase email-confirm redirects (PPT-068).
 *
 * Does not bootstrap a BFF session and never writes JWT material from the URL
 * into ``localStorage`` / readable storage. Clears the hash fragment for hygiene.
 */
export function ConfirmEmailPage() {
  const location = useLocation();
  const interpretation = interpretEmailConfirmParams({
    search: location.search,
    hash: location.hash,
  });

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    if (!window.location.hash) {
      return;
    }
    // Drop fragment so access/refresh tokens are not left in the address bar.
    const cleaned = `${window.location.pathname}${window.location.search}`;
    window.history.replaceState(null, "", cleaned);
  }, []);

  const heading =
    interpretation.status === "error"
      ? "Confirmation failed"
      : interpretation.status === "success"
        ? "Email confirmed"
        : "Confirm your email";

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">{heading}</h1>
        <p
          className={
            interpretation.status === "error"
              ? "text-sm text-destructive"
              : "text-sm text-muted-foreground"
          }
          role={interpretation.status === "error" ? "alert" : "status"}
        >
          {interpretation.message}
        </p>
      </div>
      {interpretation.discardedSessionFragment ? (
        <p className="rounded-md border border-border bg-muted/40 px-3 py-2 text-sm" role="status">
          Any tokens in the confirmation link were ignored. Use sign-in to create an HttpOnly
          session cookie.
        </p>
      ) : null}
      <Button asChild className="w-full">
        <Link to="/login" state={{ emailConfirmed: true }}>
          Continue to sign in
        </Link>
      </Button>
      <p className="text-sm text-muted-foreground">
        Need a new link?{" "}
        <Link
          to="/check-email"
          className="font-medium text-primary underline-offset-4 hover:underline"
        >
          Check email / resend
        </Link>
      </p>
    </div>
  );
}

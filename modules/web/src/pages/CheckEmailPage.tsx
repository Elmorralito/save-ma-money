import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { bffResendConfirmation } from "@/api/auth";
import { isPapitaApiError } from "@/api/errors";
import { Button } from "@/components/ui/button";
import { formatApiError } from "@/lib/formatApiError";

type CheckEmailLocationState = {
  email?: string;
};

/**
 * Post-register pending confirmation screen (PPT-068).
 *
 * No session bootstrap — user remains anonymous until they confirm and sign in.
 */
export function CheckEmailPage() {
  const location = useLocation();
  const state =
    typeof location.state === "object" && location.state !== null
      ? (location.state as CheckEmailLocationState)
      : {};
  const email = typeof state.email === "string" ? state.email.trim() : "";
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const resendMutation = useMutation({
    mutationFn: bffResendConfirmation,
    onSuccess: () => {
      setError(null);
      setStatusMessage(
        "If that address still needs confirmation, we sent another email. Check your inbox.",
      );
    },
    onError: (err: unknown) => {
      setStatusMessage(null);
      setError(formatApiError(err, "Could not resend confirmation email"));
    },
  });

  function onResend() {
    if (!email) {
      setError("Enter your email on the register page first, then try again.");
      return;
    }
    setError(null);
    resendMutation.mutate({ email });
  }

  const showResend = email.length > 0;
  const isRateLimited =
    isPapitaApiError(resendMutation.error) && resendMutation.error.status === 429;

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Check your email</h1>
        <p className="text-sm text-muted-foreground">
          {email
            ? `We sent a confirmation link to ${email}. After you confirm, you will land on this app and can sign in.`
            : "We sent a confirmation link to your email. After you confirm, you will land on this app and can sign in."}
        </p>
      </div>
      <p className="rounded-md border border-border bg-muted/40 px-3 py-2 text-sm" role="status">
        No session is opened until your email is confirmed. JWTs never touch the browser.
      </p>
      {statusMessage ? (
        <p className="rounded-md border border-border bg-muted/40 px-3 py-2 text-sm" role="status">
          {statusMessage}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
      {showResend ? (
        <Button
          type="button"
          variant="outline"
          className="w-full"
          disabled={resendMutation.isPending || isRateLimited}
          onClick={onResend}
        >
          {resendMutation.isPending ? "Sending…" : "Resend confirmation email"}
        </Button>
      ) : null}
      <p className="text-sm text-muted-foreground">
        Already confirmed?{" "}
        <Link to="/login" className="font-medium text-primary underline-offset-4 hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}

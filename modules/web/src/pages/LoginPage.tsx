import { useQuery } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { Navigate, useLocation } from "react-router-dom";

import { bffSessionQueryOptions } from "@/auth/sessionQueries";
import { OAuthProviderButtons } from "@/components/OAuthProviderButtons";

export function LoginPage() {
  const location = useLocation();
  const sessionQuery = useQuery(bffSessionQueryOptions());
  const postLoginPath =
    typeof location.state === "object" &&
    location.state !== null &&
    "from" in location.state &&
    typeof (location.state as { from?: unknown }).from === "string"
      ? (location.state as { from: string }).from
      : "/dashboard";
  const oauthReturnTo =
    postLoginPath.startsWith("/") && !postLoginPath.startsWith("//") && postLoginPath !== "/"
      ? postLoginPath
      : "/dashboard";

  if (sessionQuery.data?.authenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  const oauthError = new URLSearchParams(location.search).get("oauth_error");

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>
        <p className="text-sm text-muted-foreground">
          Continue with your Google account to access your personal ledger.
        </p>
      </div>

      {oauthError ? (
        <p
          role="alert"
          className="rounded-lg border border-destructive/30 bg-destructive/5 px-3.5 py-2.5 text-sm text-destructive"
        >
          Google sign-in failed. Please try again.
        </p>
      ) : null}

      <OAuthProviderButtons returnTo={oauthReturnTo} />

      <div className="flex items-start gap-2.5 border-t border-border/70 pt-4 text-xs text-muted-foreground">
        <ShieldCheck aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-primary" />
        <p className="leading-relaxed">
          Passwordless sign-in via Google OAuth. Your session is stored in an HttpOnly cookie — no
          passwords to manage.
        </p>
      </div>
    </div>
  );
}

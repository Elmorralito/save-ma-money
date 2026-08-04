import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { bffLogin, bffResendConfirmation } from "@/api/auth";
import { isPapitaApiError } from "@/api/errors";
import { queryKeys } from "@/api/queryKeys";
import { bffSessionQueryOptions } from "@/auth/sessionQueries";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PasswordInput } from "@/components/ui/password-input";
import { formatApiError } from "@/lib/formatApiError";

function isEmailNotConfirmedError(error: unknown): boolean {
  return (
    isPapitaApiError(error) &&
    (error.code === "email_not_confirmed" ||
      error.message === "Email not confirmed" ||
      /confirm your email/i.test(error.message))
  );
}

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const sessionQuery = useQuery(bffSessionQueryOptions());
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [resendStatus, setResendStatus] = useState<string | null>(null);
  const [showResend, setShowResend] = useState(false);

  const loginMutation = useMutation({
    mutationFn: bffLogin,
    onSuccess: async (session) => {
      queryClient.setQueryData(queryKeys.auth.session(), session);
      const from =
        typeof location.state === "object" &&
        location.state !== null &&
        "from" in location.state &&
        typeof (location.state as { from?: unknown }).from === "string"
          ? (location.state as { from: string }).from
          : "/dashboard";
      await navigate(from === "/" ? "/dashboard" : from, { replace: true });
    },
    onError: (err: unknown) => {
      setResendStatus(null);
      setError(formatApiError(err, "Login failed"));
      setShowResend(isEmailNotConfirmedError(err));
    },
  });

  const resendMutation = useMutation({
    mutationFn: bffResendConfirmation,
    onSuccess: () => {
      setError(null);
      setResendStatus(
        "If that address still needs confirmation, we sent another email. Check your inbox.",
      );
    },
    onError: (err: unknown) => {
      setResendStatus(null);
      setError(formatApiError(err, "Could not resend confirmation email"));
    },
  });

  if (sessionQuery.data?.authenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setResendStatus(null);
    setShowResend(false);
    loginMutation.mutate({ email: email.trim(), password });
  }

  function onResend() {
    const trimmed = email.trim();
    if (!trimmed) {
      setError("Enter your email, then resend the confirmation link.");
      return;
    }
    setError(null);
    resendMutation.mutate({ email: trimmed });
  }

  const justRegistered =
    typeof location.state === "object" &&
    location.state !== null &&
    "registered" in location.state &&
    Boolean((location.state as { registered?: unknown }).registered);

  const emailConfirmed =
    typeof location.state === "object" &&
    location.state !== null &&
    "emailConfirmed" in location.state &&
    Boolean((location.state as { emailConfirmed?: unknown }).emailConfirmed);

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>
        <p className="text-sm text-muted-foreground">
          Session cookies only — JWTs never touch the browser.
        </p>
      </div>
      {emailConfirmed ? (
        <p className="rounded-md border border-border bg-muted/40 px-3 py-2 text-sm" role="status">
          Email confirmed. Sign in with your email and password to open a session.
        </p>
      ) : null}
      {justRegistered ? (
        <p className="rounded-md border border-border bg-muted/40 px-3 py-2 text-sm" role="status">
          Account created. Sign in with the same email and password.
        </p>
      ) : null}
      {resendStatus ? (
        <p className="rounded-md border border-border bg-muted/40 px-3 py-2 text-sm" role="status">
          {resendStatus}
        </p>
      ) : null}
      <form className="space-y-4" onSubmit={onSubmit}>
        <div className="space-y-2">
          <Label htmlFor="login-email">Email</Label>
          <Input
            id="login-email"
            type="email"
            name="email"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => {
              setEmail(event.target.value);
            }}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="login-password">Password</Label>
          <PasswordInput
            id="login-password"
            name="password"
            autoComplete="current-password"
            required
            minLength={8}
            value={password}
            onChange={(event) => {
              setPassword(event.target.value);
            }}
          />
        </div>
        {error ? (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}
        <Button type="submit" className="w-full" disabled={loginMutation.isPending}>
          {loginMutation.isPending ? "Signing in…" : "Sign in"}
        </Button>
      </form>
      {showResend ? (
        <Button
          type="button"
          variant="outline"
          className="w-full"
          disabled={resendMutation.isPending}
          onClick={onResend}
        >
          {resendMutation.isPending ? "Sending…" : "Resend confirmation email"}
        </Button>
      ) : null}
      <p className="text-sm text-muted-foreground">
        No account?{" "}
        <Link
          to="/register"
          className="font-medium text-primary underline-offset-4 hover:underline"
        >
          Register
        </Link>
      </p>
    </div>
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { bffLogin } from "@/api/auth";
import { isPapitaApiError } from "@/api/errors";
import { queryKeys } from "@/api/queryKeys";
import { bffSessionQueryOptions } from "@/auth/sessionQueries";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const sessionQuery = useQuery(bffSessionQueryOptions());
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

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
          : "/";
      await navigate(from, { replace: true });
    },
    onError: (err: unknown) => {
      setError(isPapitaApiError(err) ? err.message : "Login failed");
    },
  });

  if (sessionQuery.data?.authenticated) {
    return <Navigate to="/" replace />;
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    loginMutation.mutate({ email: email.trim(), password });
  }

  return (
    <main className="app">
      <h1>Sign in</h1>
      <p>Session cookies only — JWTs never touch the browser.</p>
      <form className="auth-form" onSubmit={onSubmit}>
        <label>
          Email
          <input
            type="email"
            name="email"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => {
              setEmail(event.target.value);
            }}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            name="password"
            autoComplete="current-password"
            required
            minLength={8}
            value={password}
            onChange={(event) => {
              setPassword(event.target.value);
            }}
          />
        </label>
        {error ? (
          <p role="alert" className="auth-error">
            {error}
          </p>
        ) : null}
        <button type="submit" disabled={loginMutation.isPending}>
          {loginMutation.isPending ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p>
        No account? <Link to="/register">Register</Link>
      </p>
    </main>
  );
}

import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { bffRegister } from "@/api/auth";
import { isPapitaApiError } from "@/api/errors";

export function RegisterPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const registerMutation = useMutation({
    mutationFn: bffRegister,
    onSuccess: async () => {
      await navigate("/login", { replace: true, state: { registered: true } });
    },
    onError: (err: unknown) => {
      setError(isPapitaApiError(err) ? err.message : "Registration failed");
    },
  });

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    registerMutation.mutate({
      email: email.trim(),
      password,
      display_name: displayName.trim() || undefined,
    });
  }

  return (
    <main className="app">
      <h1>Create account</h1>
      <p>Uses the API register path; sign in afterward to open a BFF session.</p>
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
          Display name
          <input
            type="text"
            name="display_name"
            autoComplete="name"
            value={displayName}
            onChange={(event) => {
              setDisplayName(event.target.value);
            }}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            name="password"
            autoComplete="new-password"
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
        <button type="submit" disabled={registerMutation.isPending}>
          {registerMutation.isPending ? "Creating…" : "Register"}
        </button>
      </form>
      <p>
        Already registered? <Link to="/login">Sign in</Link>
      </p>
    </main>
  );
}

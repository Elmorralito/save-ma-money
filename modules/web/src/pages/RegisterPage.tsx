import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { bffRegister } from "@/api/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PasswordInput } from "@/components/ui/password-input";
import { formatApiError } from "@/lib/formatApiError";

export function RegisterPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const registerMutation = useMutation({
    mutationFn: bffRegister,
    onSuccess: async (user) => {
      if (user.email_confirmation_required) {
        await navigate("/check-email", {
          replace: true,
          state: { email: user.email },
        });
        return;
      }
      await navigate("/login", { replace: true, state: { registered: true } });
    },
    onError: (err: unknown) => {
      setError(formatApiError(err, "Registration failed"));
    },
  });

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    registerMutation.mutate({
      email: email.trim(),
      password,
      display_name: displayName.trim() || undefined,
    });
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Create account</h1>
        <p className="text-sm text-muted-foreground">
          Creates your account via the API. When email confirmation is required, you will confirm
          before signing in.
        </p>
      </div>
      <form className="space-y-4" onSubmit={onSubmit}>
        <div className="space-y-2">
          <Label htmlFor="register-email">Email</Label>
          <Input
            id="register-email"
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
          <Label htmlFor="register-display-name">Display name</Label>
          <Input
            id="register-display-name"
            type="text"
            name="display_name"
            autoComplete="name"
            value={displayName}
            onChange={(event) => {
              setDisplayName(event.target.value);
            }}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="register-password">Password</Label>
          <PasswordInput
            id="register-password"
            name="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(event) => {
              setPassword(event.target.value);
            }}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="register-confirm-password">Confirm password</Label>
          <PasswordInput
            id="register-confirm-password"
            name="confirm_password"
            autoComplete="new-password"
            required
            minLength={8}
            value={confirmPassword}
            onChange={(event) => {
              setConfirmPassword(event.target.value);
            }}
          />
        </div>
        {error ? (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}
        <Button type="submit" className="w-full" disabled={registerMutation.isPending}>
          {registerMutation.isPending ? "Creating…" : "Register"}
        </Button>
      </form>
      <p className="text-sm text-muted-foreground">
        Already registered?{" "}
        <Link to="/login" className="font-medium text-primary underline-offset-4 hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";

import {
  bulkMaxTransactions,
  clientContractQueryOptions,
  healthQueryOptions,
  reportWindowMaxDays,
} from "@/api";
import { bffLogout } from "@/api/auth";
import { queryKeys } from "@/api/queryKeys";
import { bffSessionQueryOptions } from "@/auth/sessionQueries";

export function HomePage() {
  const title = import.meta.env.VITE_APP_TITLE ?? "Papita";
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const sessionQuery = useQuery(bffSessionQueryOptions());
  const healthQuery = useQuery(healthQueryOptions());
  const contractQuery = useQuery(clientContractQueryOptions());

  const logoutMutation = useMutation({
    mutationFn: bffLogout,
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.auth.all });
      await navigate("/login", { replace: true });
    },
  });

  const bulkMax = bulkMaxTransactions(contractQuery.data);
  const windowMax = reportWindowMaxDays(contractQuery.data);
  const user = sessionQuery.data?.user;

  return (
    <main className="app">
      <h1>{title}</h1>
      <p>
        BFF cookie session (PPT-049). Domain features land in later epic children.
        {user ? (
          <>
            {" "}
            Signed in as <strong>{user.email}</strong>.
          </>
        ) : null}
      </p>
      <p className="auth-actions">
        {user ? (
          <button
            type="button"
            onClick={() => {
              logoutMutation.mutate();
            }}
            disabled={logoutMutation.isPending}
          >
            {logoutMutation.isPending ? "Signing out…" : "Sign out"}
          </button>
        ) : (
          <>
            <Link to="/login">Sign in</Link>
            {" · "}
            <Link to="/register">Register</Link>
          </>
        )}
      </p>
      <section aria-label="API probe status">
        <h2>Contract probes</h2>
        <ul>
          <li>
            Health:{" "}
            {healthQuery.isPending
              ? "loading…"
              : healthQuery.isError
                ? "unavailable (start API with make api-up)"
                : (healthQuery.data?.status ?? "unknown")}
          </li>
          <li>
            Session:{" "}
            {sessionQuery.isPending
              ? "loading…"
              : sessionQuery.data?.authenticated
                ? "authenticated"
                : "anonymous"}
          </li>
          <li>
            Bulk max:{" "}
            {contractQuery.isPending ? "loading…" : contractQuery.isError ? "—" : (bulkMax ?? "—")}
          </li>
          <li>
            Report window max days:{" "}
            {contractQuery.isPending
              ? "loading…"
              : contractQuery.isError
                ? "—"
                : (windowMax ?? "—")}
          </li>
        </ul>
      </section>
    </main>
  );
}

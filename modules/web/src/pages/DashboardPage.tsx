import { useQuery } from "@tanstack/react-query";

import {
  bulkMaxTransactions,
  clientContractQueryOptions,
  healthQueryOptions,
  reportWindowMaxDays,
} from "@/api";
import { bffSessionQueryOptions } from "@/auth/sessionQueries";

/** Authenticated landing stub with temporary API probe panel (PPT-051). */
export function DashboardPage() {
  const sessionQuery = useQuery(bffSessionQueryOptions());
  const healthQuery = useQuery(healthQueryOptions());
  const contractQuery = useQuery(clientContractQueryOptions());

  const bulkMax = bulkMaxTransactions(contractQuery.data);
  const windowMax = reportWindowMaxDays(contractQuery.data);
  const user = sessionQuery.data?.user;

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Shell ready for reports and balances (PPT-054). Domain rules stay in the API.
          {user ? (
            <>
              {" "}
              Signed in as <span className="font-medium text-foreground">{user.email}</span>.
            </>
          ) : null}
        </p>
      </div>

      <section
        aria-label="API probe status"
        className="rounded-lg border border-border bg-card p-4 text-card-foreground"
      >
        <h2 className="mb-3 text-sm font-semibold">Contract probes</h2>
        <ul className="space-y-1.5 text-sm text-muted-foreground">
          <li>
            Health:{" "}
            <span className="text-foreground">
              {healthQuery.isPending
                ? "loading…"
                : healthQuery.isError
                  ? "unavailable (start API with make api-up)"
                  : (healthQuery.data?.status ?? "unknown")}
            </span>
          </li>
          <li>
            Session:{" "}
            <span className="text-foreground">
              {sessionQuery.isPending
                ? "loading…"
                : sessionQuery.data?.authenticated
                  ? "authenticated"
                  : "anonymous"}
            </span>
          </li>
          <li>
            Bulk max:{" "}
            <span className="text-foreground">
              {contractQuery.isPending
                ? "loading…"
                : contractQuery.isError
                  ? "—"
                  : (bulkMax ?? "—")}
            </span>
          </li>
          <li>
            Report window max days:{" "}
            <span className="text-foreground">
              {contractQuery.isPending
                ? "loading…"
                : contractQuery.isError
                  ? "—"
                  : (windowMax ?? "—")}
            </span>
          </li>
        </ul>
      </section>
    </div>
  );
}

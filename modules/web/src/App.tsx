import { useQuery } from "@tanstack/react-query";

import {
  bulkMaxTransactions,
  clientContractQueryOptions,
  healthQueryOptions,
  reportWindowMaxDays,
} from "@/api";

import "./App.css";

function App() {
  const title = import.meta.env.VITE_APP_TITLE ?? "Papita";
  const healthQuery = useQuery(healthQueryOptions());
  const contractQuery = useQuery(clientContractQueryOptions());

  const bulkMax = bulkMaxTransactions(contractQuery.data);
  const windowMax = reportWindowMaxDays(contractQuery.data);

  return (
    <main className="app">
      <h1>{title}</h1>
      <p>
        Thin API client wiring (PPT-048). Domain features land in later epic children; auth cookies
        land in PPT-049.
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

export default App;

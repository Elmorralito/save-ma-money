import { useQuery } from "@tanstack/react-query";
import type { ReactElement, ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { bffSessionQueryOptions } from "@/auth/sessionQueries";

/** Route guard — redirects anonymous users to login with return location. */
export function RequireAuth({ children }: { children: ReactNode }): ReactElement {
  const location = useLocation();
  const sessionQuery = useQuery(bffSessionQueryOptions());

  if (sessionQuery.isPending) {
    return (
      <main className="app">
        <p>Checking session…</p>
      </main>
    );
  }

  if (!sessionQuery.data?.authenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}

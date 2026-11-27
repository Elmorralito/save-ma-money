import { useQuery } from "@tanstack/react-query";
import type { ReactElement, ReactNode } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";

import { bffSessionQueryOptions } from "@/auth/sessionQueries";
import { Button } from "@/components/ui/button";
import { formatApiError } from "@/lib/formatApiError";

/** Route guard — redirects anonymous users to login with return location. */
export function RequireAuth({ children }: { children: ReactNode }): ReactElement {
  const location = useLocation();
  const sessionQuery = useQuery(bffSessionQueryOptions());

  if (sessionQuery.isPending) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background px-4">
        <p className="text-sm text-muted-foreground">Checking session…</p>
      </div>
    );
  }

  if (sessionQuery.isError) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background px-4">
        <div
          role="alert"
          className="w-full max-w-md space-y-4 rounded-2xl border border-destructive/30 bg-card p-6 text-center shadow-sm"
        >
          <p className="text-sm font-medium text-foreground">Unable to verify your session</p>
          <p className="text-xs text-muted-foreground">
            {formatApiError(
              sessionQuery.error,
              "Temporary error contacting the authentication server.",
            )}
          </p>
          <div className="flex items-center justify-center gap-2">
            <Button
              type="button"
              size="sm"
              onClick={() => {
                void sessionQuery.refetch();
              }}
            >
              Retry
            </Button>
            <Button asChild type="button" variant="outline" size="sm">
              <Link to="/login">Sign in</Link>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (!sessionQuery.data?.authenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}

import { Outlet } from "react-router-dom";

import { BrandLogo } from "@/components/layout/BrandLogo";

/** Centered chrome for unauthenticated routes (login / register). */
export function PublicLayout() {
  const title = import.meta.env.VITE_APP_TITLE ?? "Papita";

  return (
    <div className="flex min-h-svh flex-col bg-background">
      <header className="border-b border-border px-4 py-3">
        <BrandLogo title={title} className="text-foreground" />
      </header>
      <div className="flex flex-1 items-start justify-center px-4 py-10 sm:items-center">
        <div className="w-full max-w-md rounded-lg border border-border bg-card p-6 text-card-foreground shadow-sm sm:p-8">
          <Outlet />
        </div>
      </div>
    </div>
  );
}

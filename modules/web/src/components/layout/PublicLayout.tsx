import { Outlet } from "react-router-dom";

/** Centered chrome for unauthenticated routes (login / register). */
export function PublicLayout() {
  const title = import.meta.env.VITE_APP_TITLE ?? "Papita";

  return (
    <div className="flex min-h-svh flex-col bg-background">
      <header className="border-b border-border px-4 py-3">
        <p className="text-sm font-semibold tracking-tight text-foreground">{title}</p>
      </header>
      <div className="flex flex-1 items-start justify-center px-4 py-10 sm:items-center">
        <div className="w-full max-w-md">
          <Outlet />
        </div>
      </div>
    </div>
  );
}

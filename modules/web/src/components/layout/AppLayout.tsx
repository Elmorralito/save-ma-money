import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Menu, X } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { bffLogout } from "@/api/auth";
import { queryKeys } from "@/api/queryKeys";
import { APP_NAV_ITEMS } from "@/components/layout/navItems";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { bffSessionQueryOptions } from "@/auth/sessionQueries";
import { cn } from "@/lib/utils";

function navLinkClassName({ isActive }: { isActive: boolean }): string {
  return cn(
    "block rounded-md px-3 py-2 text-sm font-medium transition-colors",
    isActive
      ? "bg-sidebar-accent text-sidebar-accent-foreground"
      : "text-sidebar-foreground hover:bg-sidebar-accent/70 hover:text-sidebar-accent-foreground",
  );
}

/** Authenticated app shell: responsive nav + header session chip. */
export function AppLayout() {
  const title = import.meta.env.VITE_APP_TITLE ?? "Papita";
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const sessionQuery = useQuery(bffSessionQueryOptions());
  const user = sessionQuery.data?.user;

  const logoutMutation = useMutation({
    mutationFn: bffLogout,
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.auth.all });
      setIsMobileNavOpen(false);
      await navigate("/login", { replace: true });
    },
  });

  function closeMobileNav() {
    setIsMobileNavOpen(false);
  }

  return (
    <div className="flex min-h-svh w-full max-w-full overflow-x-hidden bg-background">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 max-w-[85vw] flex-col border-r border-sidebar-border bg-sidebar transition-transform duration-200 md:static md:translate-x-0",
          isMobileNavOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        )}
        aria-label="Main navigation"
      >
        <div className="flex h-14 items-center justify-between px-4">
          <p className="truncate text-sm font-semibold tracking-tight text-sidebar-foreground">
            {title}
          </p>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={closeMobileNav}
            aria-label="Close navigation"
          >
            <X />
          </Button>
        </div>
        <Separator className="bg-sidebar-border" />
        <nav className="flex flex-1 flex-col gap-1 p-3" aria-label="App sections">
          {APP_NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={navLinkClassName}
              onClick={closeMobileNav}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {isMobileNavOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-foreground/30 md:hidden"
          aria-label="Dismiss navigation overlay"
          onClick={closeMobileNav}
        />
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center gap-3 border-b border-border px-3 sm:px-4">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => {
              setIsMobileNavOpen(true);
            }}
            aria-label="Open navigation"
            aria-expanded={isMobileNavOpen}
          >
            <Menu />
          </Button>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm text-muted-foreground md:hidden">{title}</p>
          </div>
          <div className="flex min-w-0 items-center gap-2">
            {user ? (
              <span className="max-w-28 truncate text-sm text-muted-foreground sm:max-w-48">
                {user.email}
              </span>
            ) : null}
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={logoutMutation.isPending}
              onClick={() => {
                logoutMutation.mutate();
              }}
            >
              {logoutMutation.isPending ? "Signing out…" : "Sign out"}
            </Button>
          </div>
        </header>
        <main className="min-w-0 flex-1 px-3 py-6 sm:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

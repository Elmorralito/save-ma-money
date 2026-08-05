import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Menu, PanelLeftClose } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { bffLogout } from "@/api/auth";
import { queryKeys } from "@/api/queryKeys";
import { BrandLogo } from "@/components/layout/BrandLogo";
import { APP_NAV_ITEMS } from "@/components/layout/navItems";
import { sessionUserLabel } from "@/components/layout/sessionUserLabel";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { bffSessionQueryOptions } from "@/auth/sessionQueries";
import { cn } from "@/lib/utils";

const NAV_OPEN_STORAGE_KEY = "papita.navOpen";

function navLinkClassName({ isActive }: { isActive: boolean }): string {
  return cn(
    "block rounded-md px-3 py-2 text-sm font-medium transition-colors",
    isActive
      ? "bg-sidebar-accent text-sidebar-accent-foreground"
      : "text-sidebar-foreground hover:bg-sidebar-accent/70 hover:text-sidebar-accent-foreground",
  );
}

function readStoredNavOpen(): boolean {
  if (typeof window === "undefined") {
    return true;
  }
  try {
    const raw = window.localStorage.getItem(NAV_OPEN_STORAGE_KEY);
    if (raw === "0") {
      return false;
    }
    if (raw === "1") {
      return true;
    }
  } catch {
    // ignore quota / private mode
  }
  // Default: open on desktop, closed on small screens (jsdom has no matchMedia).
  if (typeof window.matchMedia !== "function") {
    return true;
  }
  return window.matchMedia("(min-width: 768px)").matches;
}

function isMobileViewport(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }
  return window.matchMedia("(max-width: 767px)").matches;
}

/** Authenticated app shell: hideable nav + header session chip. */
export function AppLayout() {
  const title = import.meta.env.VITE_APP_TITLE ?? "Papita";
  const [isNavOpen, setIsNavOpen] = useState(readStoredNavOpen);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const sessionQuery = useQuery(bffSessionQueryOptions());
  const user = sessionQuery.data?.user;
  const isSessionPending = sessionQuery.isPending;
  const isSessionError = sessionQuery.isError;

  useEffect(() => {
    try {
      window.localStorage.setItem(NAV_OPEN_STORAGE_KEY, isNavOpen ? "1" : "0");
    } catch {
      // ignore quota / private mode
    }
  }, [isNavOpen]);

  const logoutMutation = useMutation({
    mutationFn: bffLogout,
    onSettled: async () => {
      await queryClient.removeQueries({ queryKey: queryKeys.auth.all });
      setIsNavOpen(false);
      await navigate("/login", { replace: true });
    },
  });

  function closeNav() {
    setIsNavOpen(false);
  }

  function toggleNav() {
    setIsNavOpen((open) => !open);
  }

  let sessionChip: string | null = null;
  if (isSessionPending) {
    sessionChip = "Session…";
  } else if (isSessionError) {
    sessionChip = "Session unavailable";
  } else if (user) {
    sessionChip = sessionUserLabel(user);
  }

  const canSignOut = !isSessionPending && (Boolean(user) || isSessionError);

  return (
    <div className="flex min-h-svh w-full max-w-full overflow-x-hidden bg-background">
      <aside
        id="app-main-nav"
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 max-w-[85vw] flex-col border-r border-sidebar-border bg-sidebar transition-transform duration-200",
          isNavOpen ? "translate-x-0" : "-translate-x-full",
        )}
        aria-label="Main navigation"
        aria-hidden={!isNavOpen}
        // Closed drawer must not remain in the tab order (aria-hidden alone is insufficient).
        {...(!isNavOpen ? { inert: true } : {})}
      >
        <div className="flex h-14 items-center justify-between gap-2 px-4">
          <BrandLogo
            title={title}
            className="min-w-0 text-sidebar-foreground"
            imageClassName="size-8"
          />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="shrink-0"
            onClick={closeNav}
            aria-label="Hide navigation"
          >
            <PanelLeftClose />
          </Button>
        </div>
        <Separator className="bg-sidebar-border" />
        <nav className="flex flex-1 flex-col gap-1 p-3" aria-label="App sections">
          {APP_NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={navLinkClassName}
              onClick={() => {
                // Collapse the drawer on small screens after navigation.
                if (isMobileViewport()) {
                  closeNav();
                }
              }}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {isNavOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-foreground/30 md:hidden"
          aria-label="Dismiss navigation overlay"
          onClick={closeNav}
        />
      ) : null}

      <div
        className={cn(
          "flex min-w-0 flex-1 flex-col transition-[padding] duration-200",
          isNavOpen ? "md:pl-64" : "md:pl-0",
        )}
      >
        <header className="flex h-14 items-center gap-3 border-b border-border px-3 sm:px-4">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={toggleNav}
            aria-label={isNavOpen ? "Hide navigation" : "Show navigation"}
            aria-expanded={isNavOpen}
            aria-controls="app-main-nav"
          >
            {isNavOpen ? <PanelLeftClose /> : <Menu />}
          </Button>
          <div className="min-w-0 flex-1">
            <BrandLogo
              title={title}
              className={cn("text-muted-foreground", isNavOpen && "md:hidden")}
              imageClassName="size-7"
            />
          </div>
          <div className="flex min-w-0 items-center gap-2" aria-live="polite">
            {sessionChip ? (
              <span
                className="max-w-28 truncate text-sm text-muted-foreground sm:max-w-48"
                data-testid="session-user-chip"
              >
                {sessionChip}
              </span>
            ) : null}
            {canSignOut ? (
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
            ) : null}
          </div>
        </header>
        <main className="min-w-0 flex-1 px-3 py-6 sm:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

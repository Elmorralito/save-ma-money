import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeftRight,
  BarChart3,
  Calculator,
  CalendarClock,
  Landmark,
  LayoutDashboard,
  LogOut,
  Mail,
  Menu,
  PanelLeftClose,
  Settings,
  Tags,
  User,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";

import { bffLogout } from "@/api/auth";
import { queryKeys } from "@/api/queryKeys";
import { BrandLogo } from "@/components/layout/BrandLogo";
import { GlobalSearchBar } from "@/components/layout/GlobalSearchBar";
import { LanguageSwitcher } from "@/components/layout/LanguageSwitcher";
import { APP_NAV_ITEMS } from "@/components/layout/navItems";
import { sessionUserLabel } from "@/components/layout/sessionUserLabel";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { bffSessionQueryOptions } from "@/auth/sessionQueries";
import { useMessages } from "@/i18n/LocaleProvider";
import { cn } from "@/lib/utils";

const NAV_OPEN_STORAGE_KEY = "papita.navOpen";

const NAV_ICONS: Record<string, LucideIcon> = {
  "/dashboard": LayoutDashboard,
  "/accounts": Landmark,
  "/categories": Tags,
  "/transactions": ArrowLeftRight,
  "/payment-dues": CalendarClock,
  "/reports": BarChart3,
  "/projections": Calculator,
  "/integrations": Mail,
  "/settings": Settings,
};

function navLinkClassName({ isActive }: { isActive: boolean }): string {
  return cn(
    "group flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
    isActive
      ? "bg-white/[0.09] text-white ring-1 ring-emerald-400/25"
      : "text-sidebar-foreground/75 hover:bg-white/[0.05] hover:text-white",
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
  const messages = useMessages();
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
          "fixed inset-y-0 left-0 z-40 flex w-64 max-w-[85vw] flex-col overflow-hidden border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-transform duration-200",
          isNavOpen ? "translate-x-0" : "-translate-x-full",
        )}
        aria-label="Main navigation"
        aria-hidden={!isNavOpen}
        // Closed drawer must not remain in the tab order (aria-hidden alone is insufficient).
        {...(!isNavOpen ? { inert: true } : {})}
      >
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -inset-x-6 -top-12 h-56 opacity-70"
          style={{
            backgroundImage:
              "radial-gradient(circle at 30% 20%, oklch(0.32 0.09 200 / 0.40), transparent 68%), radial-gradient(circle at 80% 70%, oklch(0.28 0.08 165 / 0.25), transparent 65%)",
          }}
        />
        <div className="relative z-10 flex h-14 items-center justify-between gap-2 px-4">
          <BrandLogo title={title} className="min-w-0 text-white" imageClassName="size-7" />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="shrink-0 text-sidebar-foreground/75 hover:bg-white/10 hover:text-white"
            onClick={closeNav}
            aria-label="Hide navigation"
          >
            <PanelLeftClose />
          </Button>
        </div>
        <Separator className="relative z-10 bg-white/10" />
        <nav className="relative z-10 flex flex-1 flex-col gap-1 p-3" aria-label="App sections">
          {APP_NAV_ITEMS.map((item) => {
            const Icon = NAV_ICONS[item.to];
            return (
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
                {({ isActive }) => (
                  <>
                    {Icon ? (
                      <Icon
                        aria-hidden="true"
                        className={cn(
                          "size-4 shrink-0 transition-colors",
                          isActive
                            ? "text-emerald-300"
                            : "text-sidebar-foreground/55 group-hover:text-emerald-300/80",
                        )}
                      />
                    ) : null}
                    <span>{messages.nav[item.to] ?? item.label}</span>
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
        <div className="relative z-10 border-t border-white/10 px-4 py-3">
          <p className="text-xs text-white/65">
            {title} · {messages.personalLedger}
          </p>
        </div>
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
        <header className="papita-header-accent sticky top-0 z-20 grid h-16 grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-4 border-b border-border px-4 sm:px-6">
          <div className="flex items-center gap-2.5">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="size-9 shrink-0 rounded-full"
              onClick={toggleNav}
              aria-label={isNavOpen ? "Hide navigation" : "Show navigation"}
              aria-expanded={isNavOpen}
              aria-controls="app-main-nav"
            >
              {isNavOpen ? <PanelLeftClose /> : <Menu />}
            </Button>
            <BrandLogo
              title={title}
              className={cn("shrink-0 text-foreground", isNavOpen && "md:hidden")}
              imageClassName="size-7"
            />
          </div>
          <div className="mx-auto w-full max-w-2xl min-w-0">
            <GlobalSearchBar />
          </div>
          <div className="flex shrink-0 items-center gap-2" aria-live="polite">
            <LanguageSwitcher compact />
            <span aria-hidden="true" className="hidden h-5 w-px bg-border sm:inline-block" />
            {sessionChip ? (
              <Link
                to="/settings"
                title={sessionChip}
                className="inline-flex h-9 max-w-36 items-center gap-1.5 rounded-full border border-border bg-card/90 px-3 text-xs font-medium text-foreground transition-colors hover:border-primary/40 hover:bg-card sm:max-w-44"
                data-testid="session-user-chip"
              >
                <User aria-hidden="true" className="size-3.5 shrink-0 text-primary" />
                <span className="truncate">{sessionChip}</span>
              </Link>
            ) : null}
            {canSignOut ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-9 gap-1.5 rounded-full bg-card/90 px-3 text-xs text-muted-foreground hover:border-destructive/40 hover:bg-destructive/5 hover:text-destructive"
                disabled={logoutMutation.isPending}
                aria-label={logoutMutation.isPending ? messages.signingOut : messages.signOut}
                onClick={() => {
                  logoutMutation.mutate();
                }}
              >
                <LogOut aria-hidden="true" className="size-3.5 shrink-0" />
                <span className="hidden lg:inline">
                  {logoutMutation.isPending ? messages.signingOut : messages.signOut}
                </span>
              </Button>
            ) : null}
          </div>
        </header>
        <main className="papita-main-interactive min-w-0 flex-1 px-[1.375rem] py-4 text-sm">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

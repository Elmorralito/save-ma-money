import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { GlobalSearchBox } from "@/components/layout/GlobalSearchBox";
import { type GlobalSearchHit, hitHref } from "@/lib/globalSearch";
import { cn } from "@/lib/utils";

type Scope = "all" | "account";

const ACCOUNT_DETAIL_RE = /^\/accounts\/([0-9a-fA-F-]{36})(?:\/|$)/;

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

/** True when the node participates in layout (rules out `display: none`). */
function isElementVisible(el: HTMLElement | null): boolean {
  return !!el && el.getClientRects().length > 0;
}

/**
 * Header command bar: one server-side holistic search over every entity the
 * authenticated user owns (accounts, transactions, payment dues, categories,
 * projections). Press `/` anywhere or `⌘K`/`Ctrl+K` to focus.
 *
 * When viewing `/accounts/:id`, offers a quick scope toggle (`All` vs `This account`).
 */
export function GlobalSearchBar({ className }: { className?: string }) {
  const navigate = useNavigate();
  const location = useLocation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [value, setValue] = useState("");
  const [scope, setScope] = useState<Scope>("all");
  const [error, setError] = useState<string | null>(null);

  const activeAccountId = useMemo(() => {
    const match = ACCOUNT_DETAIL_RE.exec(location.pathname);
    return match ? match[1] : null;
  }, [location.pathname]);

  const effectiveScope: Scope = activeAccountId ? scope : "all";

  // Global `/` and `Cmd+K` / `Ctrl+K` focus shortcuts (mirrors Piggies-VetPharma-Track)
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const isCmdK = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k";
      const isSlash =
        event.key === "/" &&
        !event.metaKey &&
        !event.ctrlKey &&
        !event.altKey &&
        !isTypingTarget(event.target);
      if (!isCmdK && !isSlash) return;
      const input = inputRef.current;
      if (input == null || !isElementVisible(input)) return;
      event.preventDefault();
      input.focus();
      input.select();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const handleError = useCallback((next: string | null) => {
    setError(next);
  }, []);

  function pick(hit: GlobalSearchHit) {
    setValue("");
    inputRef.current?.blur();
    navigate(hitHref(hit));
  }

  return (
    <div className={cn("w-full", className)}>
      <div className="flex items-center gap-2">
        <div className="min-w-0 flex-1">
          <GlobalSearchBox
            label="Search accounts, transactions, payment dues, categories, and projections"
            inputRef={inputRef}
            value={value}
            onValueChange={setValue}
            onPick={pick}
            onError={handleError}
            accountId={effectiveScope === "account" ? activeAccountId : null}
            echoPick={false}
          />
        </div>

        {activeAccountId ? (
          <div
            role="group"
            aria-label="Search scope"
            className="hidden shrink-0 overflow-hidden rounded-lg border border-border text-[11px] sm:inline-flex"
          >
            <button
              type="button"
              aria-pressed={effectiveScope === "all"}
              onClick={() => setScope("all")}
              className={cn(
                "px-2 py-1 transition-colors",
                effectiveScope === "all"
                  ? "bg-primary text-primary-foreground font-medium"
                  : "bg-muted/40 text-muted-foreground hover:bg-muted",
              )}
            >
              All
            </button>
            <button
              type="button"
              aria-pressed={effectiveScope === "account"}
              onClick={() => setScope("account")}
              className={cn(
                "border-l border-border px-2 py-1 transition-colors",
                effectiveScope === "account"
                  ? "bg-primary text-primary-foreground font-medium"
                  : "bg-muted/40 text-muted-foreground hover:bg-muted",
              )}
            >
              This account
            </button>
          </div>
        ) : null}

        <kbd
          aria-hidden="true"
          title="Press / or ⌘K to search"
          className="hidden h-6 min-w-6 shrink-0 items-center justify-center rounded-md border border-border bg-background px-1.5 font-sans text-[11px] font-medium text-muted-foreground lg:inline-flex"
        >
          /
        </kbd>
      </div>

      {error ? (
        <p role="alert" className="mt-1 text-[11px] leading-snug text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}

import { Search, X } from "lucide-react";
import { type KeyboardEvent, type RefObject, useEffect, useId, useRef, useState } from "react";

import { useLocale } from "@/i18n/LocaleProvider";
import { formatDate } from "@/lib/formatDate";
import { formatMoney } from "@/lib/formatMoney";
import {
  type GlobalSearchHit,
  type GlobalSearchKind,
  type GlobalSearchResponse,
  KIND_BADGE,
  KIND_LABEL,
  fetchGlobalSearch,
} from "@/lib/globalSearch";
import { cn } from "@/lib/utils";

type Props = {
  /** Optional hard filter to one account (e.g. while viewing an account detail page). */
  accountId?: string | null;
  /** Restrict to these kinds; omit for all kinds. */
  kinds?: GlobalSearchKind[];
  disabled?: boolean;
  placeholder?: string;
  /** Visible label for assistive tech; rendered sr-only. */
  label: string;
  /** Called when the user picks a hit. */
  onPick: (hit: GlobalSearchHit) => void;
  /** Controlled display text. */
  value: string;
  onValueChange: (next: string) => void;
  onError?: (error: string | null) => void;
  onResult?: (response: GlobalSearchResponse) => void;
  inputClassName?: string;
  /** Expose the input so a parent can focus it (keyboard shortcut). */
  inputRef?: RefObject<HTMLInputElement | null>;
  /** Replace the picked title in the box; default echoes the title. */
  echoPick?: boolean;
};

const SYNTAX_HINT = "Try: txn >500000 · due nu · loan · currency:USD · date:>=2026-01-01";

/**
 * Debounced combobox over `GET /api/v1/search` with typed, badged hits.
 * Patterned after Piggies-VetPharma-Track's `GlobalSearchBox`.
 */
export function GlobalSearchBox({
  accountId,
  kinds,
  disabled = false,
  placeholder,
  label,
  onPick,
  value,
  onValueChange,
  onError,
  onResult,
  inputClassName,
  inputRef,
  echoPick = false,
}: Props) {
  const { messages } = useLocale();
  const resolvedPlaceholder = placeholder ?? messages.search.placeholder;
  const listboxId = useId();
  const localRef = useRef<HTMLInputElement>(null);
  const ref = inputRef ?? localRef;
  const [hits, setHits] = useState<GlobalSearchHit[]>([]);
  const [searching, setSearching] = useState(false);
  const [pickedLabel, setPickedLabel] = useState<string | null>(null);
  const [active, setActive] = useState(-1);
  const [open, setOpen] = useState(false);
  const [searchedOnce, setSearchedOnce] = useState(false);
  const kindsKey = (kinds ?? []).join(",");

  useEffect(() => {
    const trimmed = value.trim();
    if (disabled || trimmed.length < 2 || (pickedLabel && trimmed === pickedLabel)) {
      queueMicrotask(() => {
        setHits([]);
        setSearching(false);
        setSearchedOnce(false);
        setOpen(false);
      });
      return;
    }

    const controller = new AbortController();
    const handle = window.setTimeout(() => {
      const input = ref.current;
      // Hidden responsive twin must not fire duplicate search requests.
      if (input == null || input.getClientRects().length === 0) {
        setSearching(false);
        return;
      }
      void (async () => {
        setSearching(true);
        try {
          const data = await fetchGlobalSearch({
            q: trimmed,
            accountId,
            kinds: kindsKey ? (kindsKey.split(",") as GlobalSearchKind[]) : undefined,
            limit: 20,
            signal: controller.signal,
          });
          if (controller.signal.aborted) return;
          setHits(data.items ?? []);
          setActive(-1);
          setOpen(true);
          setSearchedOnce(true);
          onResult?.(data);
          onError?.(null);
        } catch (err) {
          if (
            controller.signal.aborted ||
            (err instanceof DOMException && err.name === "AbortError")
          ) {
            return;
          }
          setHits([]);
          onError?.(err instanceof Error ? err.message : "Search request failed");
        } finally {
          if (!controller.signal.aborted) setSearching(false);
        }
      })();
    }, 280);

    return () => {
      window.clearTimeout(handle);
      controller.abort();
    };
    // onError/onResult are stable callbacks from the parent.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, accountId, kindsKey, disabled, pickedLabel]);

  function pick(hit: GlobalSearchHit) {
    setPickedLabel(hit.title);
    setHits([]);
    setOpen(false);
    if (echoPick) onValueChange(hit.title);
    onPick(hit);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setOpen(false);
      setHits([]);
      if (!value) ref.current?.blur();
      return;
    }
    if (hits.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActive((index) => (index + 1) % hits.length);
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((index) => (index <= 0 ? hits.length - 1 : index - 1));
      return;
    }
    if (event.key === "Enter" && open) {
      const target = hits[active >= 0 ? active : 0];
      if (!target) return;
      event.preventDefault();
      pick(target);
    }
  }

  const showList = open && hits.length > 0;
  const showEmpty =
    open && searchedOnce && !searching && hits.length === 0 && value.trim().length >= 2;

  return (
    <div className="relative">
      <label className="relative flex items-center">
        <span className="sr-only">{label}</span>
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute left-3 size-4 text-muted-foreground"
        />
        <input
          ref={ref}
          type="search"
          value={value}
          disabled={disabled}
          onChange={(event) => {
            setPickedLabel(null);
            setOpen(true);
            onValueChange(event.target.value);
          }}
          onFocus={() => {
            if (value.trim().length >= 2) setOpen(true);
          }}
          onBlur={() => window.setTimeout(() => setOpen(false), 140)}
          onKeyDown={onKeyDown}
          placeholder={resolvedPlaceholder}
          autoComplete="off"
          role="combobox"
          aria-expanded={showList || showEmpty}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={active >= 0 && hits[active] ? `${listboxId}-${active}` : undefined}
          className={cn(
            "h-10 w-full rounded-full border border-border/90 bg-background pl-9 pr-8 text-[0.9375rem] tracking-[-0.01em] tabular-nums text-foreground shadow-2xs placeholder:text-muted-foreground transition-colors focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/20",
            inputClassName,
          )}
        />
        {value ? (
          <button
            type="button"
            aria-label={messages.search.clear}
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => {
              setPickedLabel(null);
              setHits([]);
              setOpen(false);
              onValueChange("");
              ref.current?.focus();
            }}
            className="absolute right-2 rounded-md p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X aria-hidden="true" className="size-3.5" />
          </button>
        ) : null}
      </label>

      {searching ? (
        <div className="absolute right-0 left-0 top-full z-50 mt-1.5 rounded-xl border border-border bg-card px-3 py-2 text-xs text-muted-foreground shadow-md">
          {messages.search.searching}
        </div>
      ) : null}

      {showEmpty ? (
        <div className="absolute right-0 left-0 top-full z-50 mt-1.5 rounded-2xl border border-border bg-card text-xs text-muted-foreground shadow-lg">
          <p className="px-3.5 py-3">
            {messages.search.noMatchesPrefix} “{value.trim()}”.
          </p>
          <p className="border-t border-border/70 px-3.5 py-2 text-[11px] leading-relaxed">
            {messages.search.syntaxHint || SYNTAX_HINT}
          </p>
        </div>
      ) : null}

      {showList ? (
        <div className="absolute right-0 left-0 top-full z-50 mt-1.5 overflow-hidden rounded-2xl border border-border bg-card text-foreground shadow-lg">
          <ul
            id={listboxId}
            role="listbox"
            className="max-h-96 overflow-auto divide-y divide-border/60"
          >
            {hits.map((hit, index) => {
              const isActive = index === active;
              return (
                <li
                  key={`${hit.kind}-${hit.id}`}
                  id={`${listboxId}-${index}`}
                  role="option"
                  aria-selected={isActive}
                >
                  <button
                    type="button"
                    onMouseDown={(event) => event.preventDefault()}
                    onMouseEnter={() => setActive(index)}
                    onClick={() => pick(hit)}
                    className={cn(
                      "w-full px-3 py-2.5 text-left text-sm transition-colors",
                      isActive ? "bg-primary/10" : "hover:bg-muted/70",
                    )}
                  >
                    <span className="flex items-start gap-2.5">
                      <span
                        className={cn(
                          "mt-0.5 shrink-0 rounded-md border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                          KIND_BADGE[hit.kind] ?? "bg-muted text-muted-foreground border-border",
                        )}
                      >
                        {KIND_LABEL[hit.kind] ?? hit.kind}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-medium text-foreground">
                          {hit.title}
                        </span>
                        <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                          {hit.subtitle}
                          {hit.occurred_at ? ` · ${formatDate(hit.occurred_at)}` : ""}
                        </span>
                      </span>
                      {hit.amount !== null && hit.currency ? (
                        <span className="mt-0.5 shrink-0 font-mono text-xs font-medium text-foreground">
                          {formatMoney(hit.amount, hit.currency)}
                        </span>
                      ) : null}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
          <p className="border-t border-border/70 bg-muted/30 px-3 py-2 text-[11px] leading-relaxed text-muted-foreground">
            {SYNTAX_HINT}
          </p>
        </div>
      ) : null}
    </div>
  );
}

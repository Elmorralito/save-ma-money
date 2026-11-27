import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertCircle, ChevronUp, Loader2, RotateCcw, Send, Settings, Sparkles } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { getAIConfig, getAIStatus, sendAIChat } from "@/api/ai";
import { bridgeChat, detectCliBridge } from "@/api/cliBridge";
import { Button } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/native-select";
import { useLocale } from "@/i18n/LocaleProvider";
import { formatApiError } from "@/lib/formatApiError";
import { cn } from "@/lib/utils";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  meta?: string;
};

export type ScopedAISpec = {
  /** Logical module slug (e.g. "reports", "dashboard", "accounts"). */
  module: string;
  /** View or tab slug (e.g. "waterfall", "variance", "debt", "spending"). */
  view?: string;
  /** Specific card, chart, or table slug (e.g. "bucket-breakdown-table"). */
  control?: string;
  /** Human-readable section/card title displayed in the copilot bar. */
  title: string;
  /** Optional display currency scoped to this card/module. */
  currency?: string;
  /** Non-PII summary object describing the current card/table/filter state. */
  surfaceContext?: Record<string, unknown>;
  /** 1-3 quick prompts tailored to this exact control/view/card. */
  suggestedPrompts?: readonly string[];
};

type ScopedAITriggerProps = {
  open: boolean;
  onToggle: () => void;
  panelId?: string;
  label?: string;
  compact?: boolean;
  tone?: "light" | "dark";
  className?: string;
};

/** Organic inline trigger placed directly inside module headers, view toolbars, and cards. */
export function ScopedAITrigger({
  open,
  onToggle,
  panelId,
  label,
  compact = true,
  tone = "light",
  className,
}: ScopedAITriggerProps) {
  const { messages } = useLocale();
  const resolvedLabel = label ?? (open ? messages.ai.hideLabel : messages.ai.analyzeLabel);

  return (
    <button
      type="button"
      aria-expanded={open}
      aria-controls={panelId}
      aria-label={resolvedLabel}
      title={resolvedLabel}
      onClick={onToggle}
      className={cn(
        "inline-flex items-center justify-center gap-1.5 font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
        compact ? "h-7 rounded-lg px-2 text-[11px]" : "h-8 rounded-lg px-3 text-xs",
        tone === "dark"
          ? open
            ? "border border-emerald-400/50 bg-emerald-500 text-slate-950"
            : "border border-white/20 bg-white/[0.08] text-emerald-200 hover:bg-white/15 hover:text-white"
          : open
            ? "border border-primary bg-primary text-primary-foreground"
            : "border border-primary/25 bg-primary/[0.06] text-primary hover:border-primary/45 hover:bg-primary/12",
        className,
      )}
    >
      <Sparkles aria-hidden="true" className="size-3.5 shrink-0" />
      <span>{compact ? messages.ai.triggerLabel : resolvedLabel}</span>
    </button>
  );
}

type ScopedAIPanelProps = ScopedAISpec & {
  open: boolean;
  onClose?: () => void;
  id?: string;
  className?: string;
};

/** Contextual inline AI workspace embedded inside a module, view, chart, or table card. */
export function ScopedAIPanel({
  open,
  onClose,
  id,
  module: moduleName,
  view,
  control,
  title,
  currency,
  surfaceContext,
  suggestedPrompts = [],
  className,
}: ScopedAIPanelProps) {
  const { locale, messages } = useLocale();
  const at = messages.ai;
  const generatedId = useId();
  const panelId = id ?? generatedId;

  const [prompt, setPrompt] = useState("");
  const [connectionOverride, setConnectionOverride] = useState<string | null>(null);
  const [includeContextOverride, setIncludeContextOverride] = useState<boolean | null>(null);
  const [thread, setThread] = useState<ChatMessage[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const statusQuery = useQuery({
    queryKey: ["ai-status"],
    queryFn: ({ signal }) => getAIStatus(signal),
    enabled: open,
    staleTime: 60_000,
  });
  const configQuery = useQuery({
    queryKey: ["ai-config"],
    queryFn: ({ signal }) => getAIConfig(signal),
    enabled: open,
    staleTime: 60_000,
  });
  const bridgeQuery = useQuery({
    queryKey: ["cli-bridge-status"],
    queryFn: () => detectCliBridge(),
    enabled: open,
    staleTime: 30_000,
  });

  const connection = connectionOverride ?? configQuery.data?.default_connection ?? "";
  const includeContext =
    includeContextOverride ?? configQuery.data?.include_financial_context_by_default ?? true;
  const bridge = bridgeQuery.data;
  const useBrowserCliBridge =
    connection.startsWith("cli:") &&
    Boolean(bridge?.installed && bridge.nativeHostReady && bridge.originGranted);

  useEffect(() => {
    if (open && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [open, thread]);

  const chatMutation = useMutation({
    mutationFn: (text: string) => {
      if (useBrowserCliBridge) {
        const surfaceBlock = surfaceContext
          ? `\n\n<ui_surface_context>\n${JSON.stringify({ module: moduleName, view, control, locale, data: surfaceContext })}\n</ui_surface_context>`
          : "";
        return bridgeChat({
          connection,
          model: configQuery.data?.model ?? null,
          systemPrompt: `You are Papita's read-only personal finance assistant. Answer concisely in locale ${locale} using only the provided UI context. Never invent balances or transactions.${surfaceBlock}`,
          userPrompt: text,
        });
      }
      return sendAIChat({
        prompt: text,
        connection: connection || null,
        include_financial_context: includeContext,
        currency: currency ?? null,
        module: moduleName,
        view: view ?? null,
        control: control ?? null,
        locale,
        surface_context: surfaceContext ?? null,
      });
    },
    onSuccess: (res) => {
      setThread((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}-${String(prev.length)}`,
          role: "assistant",
          content: res.reply,
          meta: `${res.provider}${res.model ? ` · ${res.model}` : ""}${res.context_included ? ` · ${at.snapshotAttached}` : ""}`,
        },
      ]);
    },
    onError: (err) => {
      setThread((prev) => [
        ...prev,
        {
          id: `e-${Date.now()}-${String(prev.length)}`,
          role: "assistant",
          content: formatApiError(err, at.requestFailed),
          meta: "error",
        },
      ]);
    },
  });

  if (!open) {
    return null;
  }

  function submitPrompt(text: string) {
    const trimmed = text.trim();
    if (!trimmed || chatMutation.isPending) return;
    setThread((prev) => [
      ...prev,
      { id: `u-${Date.now()}-${String(prev.length)}`, role: "user", content: trimmed },
    ]);
    setPrompt("");
    chatMutation.mutate(trimmed);
  }

  const connections =
    bridge?.installed && bridge.nativeHostReady && bridge.clis.length > 0
      ? [...bridge.clis, ...(statusQuery.data?.connections ?? []).filter((c) => c.kind !== "cli")]
      : (statusQuery.data?.connections ?? []);
  const isModuleEnabled =
    moduleName === "reports"
      ? (configQuery.data?.reports_ai_enabled ?? true)
      : moduleName === "payment-dues" || moduleName === "payment_dues"
        ? (configQuery.data?.payment_dues_ai_enabled ?? true)
        : true;
  const isEnabled =
    (useBrowserCliBridge || (configQuery.data?.enabled ?? statusQuery.data?.enabled ?? false)) &&
    isModuleEnabled;
  const isAvailable =
    useBrowserCliBridge || (statusQuery.data?.available ?? connections.some((c) => c.ready));
  const isStatusLoaded = !statusQuery.isPending && !configQuery.isPending;
  const isReadyToChat = isEnabled && isAvailable;

  return (
    <div
      id={panelId}
      role="region"
      aria-label={`${at.assistantTitle}: ${title}`}
      className={cn(
        "rounded-xl border border-primary/25 bg-primary/[0.03] p-3.5 text-foreground animate-in fade-in-0 slide-in-from-top-1 duration-150",
        className,
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/70 pb-2.5">
        <div className="flex min-w-0 items-center gap-2">
          <span className="inline-flex size-6 shrink-0 items-center justify-center rounded-md bg-primary/12 text-primary">
            <Sparkles aria-hidden="true" className="size-3.5" />
          </span>
          <div className="min-w-0">
            <p className="truncate text-xs font-semibold text-foreground">{title}</p>
            <p className="truncate text-[11px] text-muted-foreground">
              {at.assistantTitle} · {moduleName}
              {view ? ` / ${view}` : ""}
              {control ? ` / ${control}` : ""}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <NativeSelect
            aria-label={at.selectConnection}
            value={connection}
            onChange={(event) => setConnectionOverride(event.target.value)}
            className="h-7 max-w-[11rem] text-[11px]"
          >
            {connections.length > 0 ? (
              connections.map((conn) => (
                <option key={conn.id} value={conn.id}>
                  {conn.id} {conn.ready ? "●" : "○"}
                </option>
              ))
            ) : (
              <option value={connection || "cli:agy"}>{connection || "cli:agy"}</option>
            )}
          </NativeSelect>

          <label className="inline-flex cursor-pointer items-center gap-1 rounded-md px-1.5 py-1 text-[11px] text-muted-foreground hover:bg-muted/60">
            <input
              type="checkbox"
              checked={includeContext}
              onChange={(event) => setIncludeContextOverride(event.target.checked)}
              className="size-3 accent-primary"
            />
            <span>{at.snapshotLabel}</span>
          </label>

          {thread.length > 0 ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-[11px]"
              onClick={() => setThread([])}
              aria-label={at.clear}
              title={at.clear}
            >
              <RotateCcw className="mr-1 size-3" />
              {at.clear}
            </Button>
          ) : null}

          <Button asChild variant="ghost" size="icon" className="size-7" title={at.configureCta}>
            <Link to="/settings?tab=ai" aria-label={at.configureCta}>
              <Settings className="size-3.5" />
            </Link>
          </Button>

          {onClose ? (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="size-7"
              aria-label={at.close}
              title={at.close}
              onClick={onClose}
            >
              <ChevronUp className="size-3.5" />
            </Button>
          ) : null}
        </div>
      </div>

      {isStatusLoaded && !isReadyToChat ? (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-warning/35 bg-warning-soft/50 p-3 text-xs">
          <div className="flex min-w-0 items-start gap-2">
            <AlertCircle className="mt-0.5 size-4 shrink-0 text-warning" />
            <div className="space-y-0.5">
              <p className="font-semibold text-foreground">
                {!isEnabled ? at.disabledTitle : at.unavailableTitle}
              </p>
              <p className="text-muted-foreground">{at.configureBody}</p>
            </div>
          </div>
          <Button asChild size="sm" variant="outline">
            <Link to="/settings?tab=ai">
              <Settings className="mr-1.5 size-3.5" />
              {at.configureCta}
            </Link>
          </Button>
        </div>
      ) : (
        <div className="mt-3 space-y-2.5">
          {suggestedPrompts.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {suggestedPrompts.map((starter) => (
                <button
                  key={starter}
                  type="button"
                  disabled={chatMutation.isPending || (isStatusLoaded && !isReadyToChat)}
                  onClick={() => submitPrompt(starter)}
                  className="rounded-full border border-border bg-background px-2.5 py-1 text-left text-[11px] font-medium text-foreground transition-colors hover:border-primary/45 hover:bg-primary/5 disabled:opacity-50"
                >
                  {starter}
                </button>
              ))}
            </div>
          ) : null}

          {thread.length === 0 && suggestedPrompts.length === 0 ? (
            <p className="text-[11px] text-muted-foreground">{at.emptyHint}</p>
          ) : null}

          {thread.length > 0 || chatMutation.isPending ? (
            <div
              ref={scrollRef}
              className="max-h-72 space-y-2 overflow-y-auto rounded-lg border border-border/70 bg-background/85 p-2.5"
            >
              {thread.map((msg) => (
                <div
                  key={msg.id}
                  className={cn(
                    "rounded-lg px-3 py-2 text-xs leading-relaxed",
                    msg.role === "user"
                      ? "ml-8 bg-primary text-primary-foreground"
                      : "mr-4 border border-border bg-card text-foreground",
                  )}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  {msg.meta ? <p className="mt-1 text-[10px] opacity-70">{msg.meta}</p> : null}
                </div>
              ))}
              {chatMutation.isPending ? (
                <div className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground">
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>{at.thinking}</span>
                </div>
              ) : null}
            </div>
          ) : null}

          <form
            onSubmit={(event) => {
              event.preventDefault();
              submitPrompt(prompt);
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={prompt}
              disabled={isStatusLoaded && !isReadyToChat}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder={
                isStatusLoaded && !isReadyToChat ? at.disabledPlaceholder : at.askPlaceholder
              }
              className="h-8 flex-1 rounded-lg border border-border bg-background px-3 text-xs focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50"
            />
            <Button
              type="submit"
              size="sm"
              className="h-8 px-3"
              aria-label={at.send}
              disabled={
                !prompt.trim() || chatMutation.isPending || (isStatusLoaded && !isReadyToChat)
              }
            >
              <Send className="size-3.5" />
            </Button>
          </form>
        </div>
      )}
    </div>
  );
}

/** Convenience controller hook for pairing a header ScopedAITrigger with a body ScopedAIPanel. */
export function useScopedAIToggle(initialOpen = false) {
  const [open, setOpen] = useState(initialOpen);
  const panelId = useId();
  return {
    open,
    panelId,
    toggle: () => setOpen((prev) => !prev),
    close: () => setOpen(false),
  };
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Filter,
  FlaskConical,
  Mail,
  Plus,
  Save,
  ShieldAlert,
  ShieldCheck,
  SlidersHorizontal,
  Trash2,
  Unlink,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import {
  disconnectGmailConnection,
  gmailOAuthStartUrl,
  listIngestionConnections,
  testEmailParse,
  upsertEmailIngestionConnection,
  type EmailIngestionConnection,
  type EmailParserMode,
  type EmailParseTestResult,
  type EmailParsingRule,
  type EmailRuleTransactionType,
} from "@/api/ingestion";
import { accountsListQueryOptions, categoriesListQueryOptions } from "@/api/queries";
import { queryKeys } from "@/api/queryKeys";
import { ScopedAIPanel, ScopedAITrigger, useScopedAIToggle } from "@/components/ai/ScopedAICopilot";
import { ActionIconButton } from "@/components/ui/action-icon-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { useLocale } from "@/i18n/LocaleProvider";
import { formatApiError } from "@/lib/formatApiError";
import { formatMoney } from "@/lib/formatMoney";
import { cn } from "@/lib/utils";

const PICKER_PARAMS = { limit: 100, skip: 0 } as const;

const PARSER_MODE_OPTIONS: ReadonlyArray<{ value: EmailParserMode; label: string }> = [
  { value: "auto", label: "Auto (built-in + fallback regex)" },
  { value: "bancolombia-email", label: "Bancolombia Alerts" },
  { value: "global66-email", label: "Global66 Wires" },
  { value: "nequi-email", label: "Nequi Alerts" },
  { value: "nu-email", label: "Nu Bank (Colombia)" },
  { value: "custom_regex", label: "Custom Regex" },
];

const QUICK_BANK_SENDERS: ReadonlyArray<{ domain: string; label: string; tone: string }> = [
  {
    domain: "notificacionesbancolombia.com",
    label: "Bancolombia",
    tone: "border-amber-500/30 bg-amber-500/10 text-amber-800 hover:bg-amber-500/20 dark:text-amber-300",
  },
  {
    domain: "nu.com.co",
    label: "Nu Bank",
    tone: "border-violet-500/30 bg-violet-500/10 text-violet-800 hover:bg-violet-500/20 dark:text-violet-300",
  },
  {
    domain: "global66.com",
    label: "Global66",
    tone: "border-emerald-500/30 bg-emerald-500/10 text-emerald-800 hover:bg-emerald-500/20 dark:text-emerald-300",
  },
  {
    domain: "nequi.com.co",
    label: "Nequi",
    tone: "border-rose-500/30 bg-rose-500/10 text-rose-800 hover:bg-rose-500/20 dark:text-rose-300",
  },
];

const TEST_SAMPLES = {
  nuPayment: {
    label: "Nu Bank",
    tone: "border-violet-500/30 bg-violet-500/10 text-violet-800 hover:bg-violet-500/20 dark:text-violet-300",
    activeTone:
      "border-violet-600 bg-violet-600 text-white shadow-xs ring-2 ring-violet-500/30 dark:bg-violet-500",
    sender: "Nu <nu@nu.com.co>",
    subject: "¡Ya entró tu pago!",
    body: [
      "Recibimos el pago que hiciste de tu Tarjeta de crédito Nu.",
      "Tu pago fue de $1.975.723,00",
      "Lo has realizado el 06 noviembre 2026 4:24:05 PM",
      "Producto origen DRH391",
      "Producto destino **** **** **** 3250",
      "ID transacción ab2e1376-eae2-3169-85a6-ceba1221efad",
    ].join("\n"),
  },
  bancolombia: {
    label: "Bancolombia",
    tone: "border-amber-500/30 bg-amber-500/10 text-amber-800 hover:bg-amber-500/20 dark:text-amber-300",
    activeTone:
      "border-amber-600 bg-amber-600 text-white shadow-xs ring-2 ring-amber-500/30 dark:bg-amber-500",
    sender: "alertasynotificaciones@notificacionesbancolombia.com",
    subject: "Alerta Bancolombia",
    body: "Bancolombia le informa que Pagaste $2,207,730.00 a TARJETA VISA desde tu producto *7756 el 24/11/2026 14:30.",
  },
  global66: {
    label: "Global66",
    tone: "border-emerald-500/30 bg-emerald-500/10 text-emerald-800 hover:bg-emerald-500/20 dark:text-emerald-300",
    activeTone:
      "border-emerald-600 bg-emerald-600 text-white shadow-xs ring-2 ring-emerald-500/30 dark:bg-emerald-500",
    sender: "notificaciones@global66.com",
    subject: "Tu transferencia internacional está en camino",
    body: "Transaction No. 17020398 — $590.40 USD sent to Interactive Brokers (UMB National Association 913010600302) on November 14, 2026.",
  },
} as const;

const TXN_TYPE_OPTIONS: ReadonlyArray<{ value: EmailRuleTransactionType; label: string }> = [
  { value: "auto", label: "Auto" },
  { value: "expense", label: "Expense" },
  { value: "income", label: "Income" },
  { value: "transfer", label: "Transfer" },
];

function parserBadgeStyle(mode: EmailParserMode): { label: string; className: string } {
  switch (mode) {
    case "bancolombia-email":
      return {
        label: "Bancolombia",
        className: "border-amber-500/30 bg-amber-500/12 text-amber-800 dark:text-amber-300",
      };
    case "nu-email":
      return {
        label: "Nu Bank",
        className: "border-violet-500/30 bg-violet-500/12 text-violet-800 dark:text-violet-300",
      };
    case "global66-email":
      return {
        label: "Global66",
        className: "border-emerald-500/30 bg-emerald-500/12 text-emerald-800 dark:text-emerald-300",
      };
    case "nequi-email":
      return {
        label: "Nequi",
        className: "border-rose-500/30 bg-rose-500/12 text-rose-800 dark:text-rose-300",
      };
    case "custom_regex":
      return {
        label: "Regex",
        className: "border-sky-500/30 bg-sky-500/12 text-sky-800 dark:text-sky-300",
      };
    default:
      return {
        label: "Auto",
        className: "border-border bg-muted text-foreground",
      };
  }
}

function senderChipStyle(domain: string): string {
  const lower = domain.toLowerCase();
  if (lower.includes("bancolombia")) {
    return "border-amber-500/30 bg-amber-500/12 text-amber-900 dark:text-amber-200";
  }
  if (lower.includes("nu.com")) {
    return "border-violet-500/30 bg-violet-500/12 text-violet-900 dark:text-violet-200";
  }
  if (lower.includes("global66")) {
    return "border-emerald-500/30 bg-emerald-500/12 text-emerald-900 dark:text-emerald-200";
  }
  if (lower.includes("nequi")) {
    return "border-rose-500/30 bg-rose-500/12 text-rose-900 dark:text-rose-200";
  }
  return "border-primary/25 bg-primary/10 text-primary";
}

function txnTypeBadgeStyle(type: string | null | undefined): string {
  switch ((type ?? "").toLowerCase()) {
    case "income":
      return "border-emerald-500/30 bg-emerald-500/12 text-emerald-800 dark:text-emerald-300";
    case "expense":
      return "border-rose-500/30 bg-rose-500/12 text-rose-800 dark:text-rose-300";
    case "transfer":
      return "border-sky-500/30 bg-sky-500/12 text-sky-800 dark:text-sky-300";
    default:
      return "border-border bg-muted text-muted-foreground";
  }
}

function createEmptyRule(): EmailParsingRule {
  return {
    id: crypto.randomUUID(),
    name: "New bank rule",
    enabled: true,
    parser_mode: "auto",
    sender_match: "",
    subject_match: "",
    amount_regex: "",
    transaction_type: "auto",
    currency: "COP",
    default_account_id: null,
    default_category_id: null,
    description_template: "",
  };
}

export type EmailIngestionPageProps = {
  /** When true, renders embedded inside Settings → Integrations without outer page wrapper or duplicate hero header. */
  embedded?: boolean;
  /** Controlled auto-save flag from the parent Settings header when embedded. */
  externalAutoSave?: boolean;
  /** Incremented by the parent Settings header Save button to trigger a save when embedded. */
  saveSignal?: number;
};

export function EmailIngestionPage({
  embedded = false,
  externalAutoSave,
  saveSignal = 0,
}: EmailIngestionPageProps) {
  const { locale } = useLocale();
  const ingestionAi = useScopedAIToggle();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const gmailCallbackStatus = searchParams.get("gmail");

  const connectionsQuery = useQuery({
    queryKey: queryKeys.ingestion.connections({ limit: 20, skip: 0 }),
    queryFn: ({ signal }) => listIngestionConnections({ limit: 20, skip: 0, signal }),
  });
  const accountsQuery = useQuery(accountsListQueryOptions(PICKER_PARAMS));
  const categoriesQuery = useQuery(categoriesListQueryOptions(PICKER_PARAMS));

  const connection = useMemo<EmailIngestionConnection | null>(() => {
    const items = (connectionsQuery.data?.items ?? []) as unknown as EmailIngestionConnection[];
    return items.find((item) => item.provider === "email") ?? items[0] ?? null;
  }, [connectionsQuery.data]);

  const accounts = accountsQuery.data?.items ?? [];
  const categories = categoriesQuery.data?.items ?? [];

  const [enabled, setEnabled] = useState(true);
  const [gmailAccessEnabled, setGmailAccessEnabled] = useState(false);
  const [lookbackHours, setLookbackHours] = useState(168);
  const [senders, setSenders] = useState<string[]>([]);
  const [senderInput, setSenderInput] = useState("");
  const [subjects, setSubjects] = useState<string[]>([]);
  const [subjectInput, setSubjectInput] = useState("");
  const [sourceLabel, setSourceLabel] = useState("");
  const [rules, setRules] = useState<EmailParsingRule[]>([]);
  const [expandedRuleId, setExpandedRuleId] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [autoSaveState, setAutoSave] = useState(true);
  const autoSave = externalAutoSave ?? autoSaveState;
  const lastSavedSnapshotRef = useRef<string | null>(null);
  const lastSaveSignalRef = useRef(saveSignal);

  // Test parser sandbox state
  const [selectedSample, setSelectedSample] = useState<keyof typeof TEST_SAMPLES | null>(
    "nuPayment",
  );
  const [testSender, setTestSender] = useState<string>(TEST_SAMPLES.nuPayment.sender);
  const [testSubject, setTestSubject] = useState<string>(TEST_SAMPLES.nuPayment.subject);
  const [testBody, setTestBody] = useState<string>(TEST_SAMPLES.nuPayment.body);
  const [testResult, setTestResult] = useState<EmailParseTestResult | null>(null);

  useEffect(() => {
    if (!connection || hydrated) {
      return;
    }
    queueMicrotask(() => {
      setEnabled(connection.enabled);
      setGmailAccessEnabled(Boolean(connection.gmail_access_enabled));
      setLookbackHours(connection.lookback_hours || 24);
      setSenders(connection.email_senders ?? []);
      setSubjects(connection.email_subjects ?? []);
      setSourceLabel(connection.email_source_label ?? "");
      setRules(connection.parsing_rules ?? []);
      setHydrated(true);
    });
    lastSavedSnapshotRef.current = JSON.stringify({
      enabled: connection.enabled,
      gmail_access_enabled: Boolean(connection.gmail_access_enabled),
      lookback_hours: Math.min(720, Math.max(1, Number(connection.lookback_hours || 24) || 24)),
      email_senders: connection.email_senders ?? [],
      email_subjects: connection.email_subjects ?? [],
      email_source_label: (connection.email_source_label ?? "").trim() || null,
      parsing_rules: connection.parsing_rules ?? [],
    });
  }, [connection, hydrated]);

  const configPayload = useMemo(
    () => ({
      enabled,
      gmail_access_enabled: gmailAccessEnabled,
      lookback_hours: Math.min(720, Math.max(1, Number(lookbackHours) || 24)),
      email_senders: senders,
      email_subjects: subjects,
      email_source_label: sourceLabel.trim() || null,
      parsing_rules: rules,
    }),
    [enabled, gmailAccessEnabled, lookbackHours, senders, subjects, sourceLabel, rules],
  );
  const serializedConfig = useMemo(() => JSON.stringify(configPayload), [configPayload]);

  const saveMutation = useMutation({
    mutationFn: () => upsertEmailIngestionConnection(configPayload),
    onSuccess: async () => {
      lastSavedSnapshotRef.current = serializedConfig;
      await queryClient.invalidateQueries({ queryKey: queryKeys.ingestion.all });
      toast.success("Email ingestion configuration saved");
    },
    onError: (err: unknown) => {
      toast.error(formatApiError(err, "Could not save email settings"));
    },
  });

  const { mutate: triggerSave, isPending: isSaving } = saveMutation;

  useEffect(() => {
    if (!hydrated || !autoSave) {
      return;
    }
    if (lastSavedSnapshotRef.current === serializedConfig) {
      return;
    }
    const timer = window.setTimeout(() => {
      if (!isSaving) {
        triggerSave();
      }
    }, 900);
    return () => {
      window.clearTimeout(timer);
    };
  }, [autoSave, hydrated, isSaving, serializedConfig, triggerSave]);

  useEffect(() => {
    if (saveSignal === lastSaveSignalRef.current) {
      return;
    }
    lastSaveSignalRef.current = saveSignal;
    if (!isSaving) {
      triggerSave();
    }
  }, [isSaving, saveSignal, triggerSave]);

  const disconnectMutation = useMutation({
    mutationFn: disconnectGmailConnection,
    onSuccess: async () => {
      setGmailAccessEnabled(false);
      await queryClient.invalidateQueries({ queryKey: queryKeys.ingestion.all });
      toast.success("Gmail token revoked and disconnected");
    },
    onError: (err: unknown) => {
      toast.error(formatApiError(err, "Could not disconnect Gmail"));
    },
  });

  const testParseMutation = useMutation({
    mutationFn: () =>
      testEmailParse({
        sender: testSender.trim(),
        subject: testSubject.trim(),
        body: testBody,
        rules,
      }),
    onSuccess: (res) => {
      setTestResult(res);
    },
    onError: (err: unknown) => {
      toast.error(formatApiError(err, "Parse test failed"));
    },
  });

  const addSenderDomain = useCallback((raw: string) => {
    const trimmed = raw.trim().toLowerCase();
    if (!trimmed) {
      return;
    }
    setSenders((prev) => (prev.includes(trimmed) ? prev : [...prev, trimmed]));
  }, []);

  const addSender = useCallback(() => {
    addSenderDomain(senderInput);
    setSenderInput("");
  }, [addSenderDomain, senderInput]);

  const addSubject = useCallback(() => {
    const trimmed = subjectInput.trim();
    if (!trimmed) {
      setSubjectInput("");
      return;
    }
    setSubjects((prev) => (prev.includes(trimmed) ? prev : [...prev, trimmed]));
    setSubjectInput("");
  }, [subjectInput]);

  const updateRule = useCallback((idx: number, patch: Partial<EmailParsingRule>) => {
    setRules((prev) => prev.map((r, i) => (i === idx ? { ...r, ...patch } : r)));
  }, []);

  const removeRule = useCallback((idx: number) => {
    setRules((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const accountNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const a of accounts) map.set(a.id, a.name);
    return map;
  }, [accounts]);

  const categoryNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const c of categories) map.set(c.id, c.name);
    return map;
  }, [categories]);

  const isGmailConnected = Boolean(connection?.gmail_connected);
  const activeRuleCount = useMemo(() => rules.filter((r) => r.enabled).length, [rules]);

  const headerBlock = embedded ? (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-card px-5 py-3.5 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full px-3 py-1 font-medium",
            isGmailConnected && gmailAccessEnabled
              ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
              : "bg-amber-500/15 text-amber-800 dark:text-amber-200",
          )}
        >
          {isGmailConnected && gmailAccessEnabled ? (
            <ShieldCheck aria-hidden="true" className="size-3.5" />
          ) : (
            <ShieldAlert aria-hidden="true" className="size-3.5" />
          )}
          {isGmailConnected && gmailAccessEnabled
            ? `Polling active · ${connection?.gmail_connected_email ?? "Gmail"}`
            : isGmailConnected
              ? "Gmail connected · Polling paused"
              : "Gmail not connected"}
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-3 py-1 font-medium text-foreground tabular-nums">
          <Filter aria-hidden="true" className="size-3.5 text-emerald-600 dark:text-emerald-400" />
          {senders.length} {senders.length === 1 ? "sender" : "senders"}
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-3 py-1 font-medium text-foreground tabular-nums">
          <SlidersHorizontal
            aria-hidden="true"
            className="size-3.5 text-violet-600 dark:text-violet-400"
          />
          {activeRuleCount} {activeRuleCount === 1 ? "rule" : "rules"}
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-3 py-1 font-medium text-foreground tabular-nums">
          <Clock aria-hidden="true" className="size-3.5 text-amber-600 dark:text-amber-400" />
          {lookbackHours}h lookback
        </span>
      </div>
      {saveMutation.isPending ? (
        <span className="text-[11px] font-medium text-muted-foreground">Syncing Gmail config…</span>
      ) : null}
      <ScopedAITrigger
        open={ingestionAi.open}
        panelId={ingestionAi.panelId}
        onToggle={ingestionAi.toggle}
      />
    </div>
  ) : (
    <>
      {/* Obsidian command banner — standalone route only */}
      <header className="relative overflow-hidden rounded-2xl bg-[#04090c] p-6 text-white">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -top-24 -right-20 size-72 rounded-full bg-emerald-500/18 blur-3xl"
        />
        <div className="relative grid gap-5 lg:grid-cols-[1fr_272px] lg:items-center">
          <div className="space-y-4">
            <div className="max-w-2xl space-y-2">
              <h1 className="text-2xl font-semibold tracking-tight text-white">
                Email &amp; Gmail Ingestion
              </h1>
              <p className="text-sm leading-relaxed text-slate-300">
                Authorize your mailbox with encrypted per-user tokens, filter bank alert domains,
                and route Bancolombia, Nu Bank, Global66, and Nequi notifications straight to your
                ledger.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full px-3 py-1 font-medium",
                  isGmailConnected && gmailAccessEnabled
                    ? "bg-emerald-500/20 text-emerald-300"
                    : "bg-amber-500/20 text-amber-200",
                )}
              >
                {isGmailConnected && gmailAccessEnabled ? (
                  <ShieldCheck aria-hidden="true" className="size-3.5" />
                ) : (
                  <ShieldAlert aria-hidden="true" className="size-3.5" />
                )}
                {isGmailConnected && gmailAccessEnabled
                  ? `Polling active · ${connection?.gmail_connected_email ?? "Gmail"}`
                  : isGmailConnected
                    ? "Gmail connected · Polling paused"
                    : "Gmail not connected"}
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 font-medium text-slate-200 tabular-nums">
                <Filter aria-hidden="true" className="size-3.5 text-emerald-400" />
                {senders.length} {senders.length === 1 ? "sender" : "senders"}
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 font-medium text-slate-200 tabular-nums">
                <SlidersHorizontal aria-hidden="true" className="size-3.5 text-violet-300" />
                {activeRuleCount} {activeRuleCount === 1 ? "rule" : "rules"}
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 font-medium text-slate-200 tabular-nums">
                <Clock aria-hidden="true" className="size-3.5 text-amber-300" />
                {lookbackHours}h
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-3 rounded-xl border border-white/10 bg-white/[0.05] p-4">
            <label className="flex cursor-pointer items-center justify-between gap-3">
              <div className="space-y-0.5">
                <div className="text-xs font-semibold text-white">Auto-save changes</div>
                <div className="text-[11px] text-slate-400">
                  {saveMutation.isPending
                    ? "Syncing configuration…"
                    : autoSave
                      ? "Persists edits automatically"
                      : "Manual save required"}
                </div>
              </div>
              <input
                type="checkbox"
                checked={autoSave}
                onChange={(event) => {
                  setAutoSave(event.target.checked);
                }}
                className="sr-only"
                aria-label="Auto-save changes"
              />
              <span
                aria-hidden="true"
                className={cn(
                  "relative h-5 w-9 shrink-0 rounded-full transition-colors",
                  autoSave ? "bg-emerald-500/40" : "bg-white/15",
                )}
              >
                <span
                  className={cn(
                    "absolute top-0.5 left-0.5 size-4 rounded-full transition-transform",
                    autoSave ? "translate-x-4 bg-emerald-400" : "translate-x-0 bg-slate-300",
                  )}
                />
              </span>
            </label>

            <Button
              type="button"
              disabled={saveMutation.isPending}
              onClick={() => {
                saveMutation.mutate();
              }}
              className="w-full bg-emerald-500 text-slate-950 hover:bg-emerald-400"
            >
              <Save aria-hidden="true" className="mr-1.5 size-4" />
              {saveMutation.isPending ? "Saving…" : "Save now"}
            </Button>
            <ScopedAITrigger
              open={ingestionAi.open}
              panelId={ingestionAi.panelId}
              onToggle={ingestionAi.toggle}
              compact={false}
              tone="dark"
              className="w-full"
            />
          </div>
        </div>
      </header>
    </>
  );

  const alertsBlock = (
    <>
      <ScopedAIPanel
        id={ingestionAi.panelId}
        open={ingestionAi.open}
        onClose={ingestionAi.close}
        module="integrations"
        view="email-ingestion"
        control="parser-and-rules"
        title="Email & Gmail Ingestion"
        surfaceContext={{
          gmail_connected: isGmailConnected,
          gmail_access_enabled: gmailAccessEnabled,
          lookback_hours: lookbackHours,
          senders,
          active_rule_count: activeRuleCount,
          test_sample_sender: testSender,
          test_sample_subject: testSubject,
          test_result: testResult,
        }}
        suggestedPrompts={
          locale === "es-CO"
            ? [
                "Revisa estas reglas y remitentes de correo para evitar duplicados o falsos positivos.",
                "¿Qué patrón regex o regla conviene si un correo bancario no extrae bien el monto?",
              ]
            : [
                "Review these sender filters and parsing rules to reduce false matches.",
                "Help interpret this sample email parse result or suggest a regex refinement.",
              ]
        }
      />
      {gmailCallbackStatus === "connected" ? (
        <div
          role="status"
          className="flex items-center gap-2.5 rounded-xl border border-emerald-500/35 bg-emerald-500/10 px-4 py-3 text-sm font-medium text-emerald-900 dark:text-emerald-200"
        >
          <CheckCircle2
            aria-hidden="true"
            className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400"
          />
          <span>Gmail connected and authorized with encrypted per-user refresh token.</span>
        </div>
      ) : null}

      {gmailCallbackStatus === "error" ? (
        <div
          role="alert"
          className="rounded-xl border border-destructive/35 bg-destructive/10 px-4 py-3 text-sm font-medium text-destructive"
        >
          Could not complete Gmail authorization. Please try connecting again.
        </div>
      ) : null}
    </>
  );

  const accessBlock = (
    <section aria-label="Gmail access" className="rounded-2xl border border-border bg-card p-5">
      <div className="grid gap-4 lg:grid-cols-12 lg:items-center">
        <div className="flex flex-wrap items-center justify-between gap-3 lg:col-span-5">
          <div className="flex items-start gap-3">
            <span
              className={cn(
                "flex size-10 shrink-0 items-center justify-center rounded-xl",
                isGmailConnected
                  ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                  : "bg-amber-500/15 text-amber-700 dark:text-amber-300",
              )}
            >
              <Mail aria-hidden="true" className="size-5" />
            </span>
            <div className="space-y-0.5">
              <h2 className="text-base font-semibold tracking-tight">Gmail Mailbox Access</h2>
              <p className="text-xs text-muted-foreground">
                {connection?.gmail_connected_email
                  ? `Authorized: ${connection.gmail_connected_email}`
                  : "Grant gmail.modify scope (encrypted per user)."}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant={isGmailConnected ? "outline" : "default"}
              size="sm"
              disabled={isGmailConnected}
              onClick={() => {
                window.location.assign(gmailOAuthStartUrl());
              }}
            >
              <ShieldCheck aria-hidden="true" className="mr-1.5 size-4" />
              {isGmailConnected ? "Connected" : "Connect"}
            </Button>
            {isGmailConnected ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={disconnectMutation.isPending}
                onClick={() => {
                  disconnectMutation.mutate();
                }}
                className="text-destructive hover:text-destructive"
              >
                <Unlink aria-hidden="true" className="mr-1.5 size-4" />
                Revoke
              </Button>
            ) : null}
          </div>
        </div>

        <div className="grid gap-2.5 sm:grid-cols-2 lg:col-span-7">
          <label
            className={cn(
              "flex cursor-pointer items-center justify-between gap-3 rounded-xl border px-3.5 py-2.5 text-sm transition-colors",
              gmailAccessEnabled
                ? "border-emerald-500/35 bg-emerald-500/8"
                : "border-border bg-muted/25 hover:bg-muted/40",
            )}
          >
            <div>
              <p className="text-xs font-semibold">Allow Gmail access</p>
              <p className="text-[11px] text-muted-foreground">Fail-closed when off.</p>
            </div>
            <input
              type="checkbox"
              aria-label="Allow Gmail access"
              className="size-4 accent-emerald-600"
              checked={gmailAccessEnabled}
              onChange={(event) => {
                setGmailAccessEnabled(event.target.checked);
              }}
            />
          </label>
          <label
            className={cn(
              "flex cursor-pointer items-center justify-between gap-3 rounded-xl border px-3.5 py-2.5 text-sm transition-colors",
              enabled
                ? "border-emerald-500/35 bg-emerald-500/8"
                : "border-border bg-muted/25 hover:bg-muted/40",
            )}
          >
            <div>
              <p className="text-xs font-semibold">Hourly scheduled ingestion</p>
              <p className="text-[11px] text-muted-foreground">Auto-poll &amp; label processed.</p>
            </div>
            <input
              type="checkbox"
              aria-label="Hourly scheduled ingestion"
              className="size-4 accent-emerald-600"
              checked={enabled}
              onChange={(event) => {
                setEnabled(event.target.checked);
              }}
            />
          </label>
        </div>
      </div>
    </section>
  );

  const filtersBlock = (
    <section
      aria-label="Mailbox filters"
      className="space-y-4 rounded-2xl border border-border bg-card p-5"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3.5">
        <div className="flex items-start gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-sky-500/15 text-sky-700 dark:text-sky-300">
            <Filter aria-hidden="true" className="size-4" />
          </span>
          <div>
            <h2 className="text-base font-semibold tracking-tight">
              Mailbox Scope &amp; Bank Senders
            </h2>
            <p className="text-xs text-muted-foreground">
              Only DKIM/SPF-verified messages from these senders are fetched.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">Quick add:</span>
          {QUICK_BANK_SENDERS.map((bank) => {
            const alreadyAdded = senders.includes(bank.domain);
            return (
              <button
                key={bank.domain}
                type="button"
                disabled={alreadyAdded}
                onClick={() => {
                  addSenderDomain(bank.domain);
                }}
                className={cn(
                  "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors disabled:opacity-45",
                  bank.tone,
                )}
              >
                <Plus aria-hidden="true" className="size-3" />
                {bank.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.15fr_0.85fr] lg:items-start">
        <div className="space-y-2.5">
          <Label htmlFor="email-sender-input" className="text-xs">
            Allowed sender domains or addresses
          </Label>
          <div className="flex gap-2">
            <Input
              id="email-sender-input"
              placeholder="e.g. nu.com.co"
              value={senderInput}
              onChange={(event) => {
                setSenderInput(event.target.value);
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  addSender();
                }
              }}
            />
            <Button type="button" variant="outline" onClick={addSender}>
              Add
            </Button>
          </div>
          <div className="flex flex-wrap gap-1.5 pt-0.5">
            {senders.map((s) => (
              <span
                key={s}
                className={cn(
                  "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium",
                  senderChipStyle(s),
                )}
              >
                {s}
                <button
                  type="button"
                  aria-label={`Remove sender ${s}`}
                  onClick={() => {
                    setSenders((prev) => prev.filter((item) => item !== s));
                  }}
                  className="rounded-full p-0.5 hover:bg-black/10 dark:hover:bg-white/10"
                >
                  <X className="size-3" />
                </button>
              </span>
            ))}
            {senders.length === 0 ? (
              <p className="text-xs text-muted-foreground">No senders added yet (fail-closed).</p>
            ) : null}
          </div>
        </div>

        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="email-source-label" className="text-xs">
                Gmail label (optional)
              </Label>
              <Input
                id="email-source-label"
                placeholder="e.g. FINANCES"
                value={sourceLabel}
                onChange={(event) => {
                  setSourceLabel(event.target.value);
                }}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="email-lookback-hours" className="text-xs">
                Lookback (hrs)
              </Label>
              <Input
                id="email-lookback-hours"
                type="number"
                min={1}
                max={720}
                value={lookbackHours}
                onChange={(event) => {
                  setLookbackHours(Number(event.target.value));
                }}
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="email-subject-input" className="text-xs">
              Subject keywords (optional)
            </Label>
            <div className="flex gap-2">
              <Input
                id="email-subject-input"
                placeholder="e.g. Alerta, Ya entró tu pago"
                value={subjectInput}
                onChange={(event) => {
                  setSubjectInput(event.target.value);
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    addSubject();
                  }
                }}
              />
              <Button type="button" variant="outline" onClick={addSubject}>
                Add
              </Button>
            </div>
            {subjects.length > 0 ? (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {subjects.map((subj) => (
                  <span
                    key={subj}
                    className="inline-flex items-center gap-1 rounded-full border border-border bg-muted px-2.5 py-0.5 text-xs font-medium text-foreground"
                  >
                    {subj}
                    <button
                      type="button"
                      aria-label={`Remove subject ${subj}`}
                      onClick={() => {
                        setSubjects((prev) => prev.filter((item) => item !== subj));
                      }}
                      className="rounded-full p-0.5 hover:bg-foreground/10"
                    >
                      <X className="size-3" />
                    </button>
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );

  const rulesBlock = (
    <section
      aria-label="Parsing rules"
      className="space-y-4 rounded-2xl border border-border bg-card p-5"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-violet-500/15 text-violet-700 dark:text-violet-300">
            <SlidersHorizontal aria-hidden="true" className="size-5" />
          </span>
          <div className="space-y-0.5">
            <h2 className="text-base font-semibold tracking-tight">
              Bank Parsing &amp; Routing Rules
            </h2>
            <p className="text-sm text-muted-foreground">
              Map each bank parser to its target account and category. Click any rule to edit
              details.
            </p>
          </div>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => {
            const created = createEmptyRule();
            setRules((prev) => [...prev, created]);
            setExpandedRuleId(created.id ?? null);
          }}
        >
          <Plus aria-hidden="true" className="mr-1.5 size-4" />
          Add rule
        </Button>
      </div>

      {rules.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-muted/20 px-4 py-8 text-center text-sm text-muted-foreground">
          No custom routing rules yet. Built-in parsers (Bancolombia, Global66, Nequi, Nu Bank)
          still match automatically — add a rule to assign a default account and category.
        </div>
      ) : (
        <div className="divide-y divide-border overflow-hidden rounded-xl border border-border">
          {rules.map((rule, idx) => {
            const ruleKey = rule.id ?? String(idx);
            const isExpanded = expandedRuleId === ruleKey;
            const badge = parserBadgeStyle(rule.parser_mode);
            const accountLabel = rule.default_account_id
              ? (accountNameById.get(rule.default_account_id) ?? "Assigned")
              : "Unassigned";
            const categoryLabel = rule.default_category_id
              ? (categoryNameById.get(rule.default_category_id) ?? "Assigned")
              : "Unassigned";

            return (
              <div
                key={ruleKey}
                className={cn(
                  "transition-colors",
                  !rule.enabled && "opacity-60",
                  isExpanded ? "bg-muted/25" : "bg-card hover:bg-muted/15",
                )}
              >
                {/* Compact summary bar */}
                <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
                  <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2.5">
                    <input
                      type="checkbox"
                      aria-label={`Enable rule ${rule.name}`}
                      className="size-4 shrink-0 accent-emerald-600"
                      checked={rule.enabled}
                      onChange={(event) => {
                        updateRule(idx, { enabled: event.target.checked });
                      }}
                    />
                    <span
                      className={cn(
                        "inline-flex shrink-0 items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
                        badge.className,
                      )}
                    >
                      {badge.label}
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        setExpandedRuleId(isExpanded ? null : ruleKey);
                      }}
                      className="truncate text-left text-sm font-semibold text-foreground hover:text-primary"
                    >
                      {rule.name || "Untitled rule"}
                    </button>
                    <span className="hidden items-center gap-1.5 text-xs text-muted-foreground md:inline-flex">
                      <ArrowRight aria-hidden="true" className="size-3" />
                      <span className="font-medium text-foreground/80">{accountLabel}</span>
                      <span>/</span>
                      <span>{categoryLabel}</span>
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <span
                      className={cn(
                        "inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium capitalize",
                        txnTypeBadgeStyle(rule.transaction_type),
                      )}
                    >
                      {rule.transaction_type}
                    </span>
                    <span className="rounded-md bg-muted px-1.5 py-0.5 text-[11px] font-medium tabular-nums text-muted-foreground">
                      {rule.currency}
                    </span>
                    <ActionIconButton
                      icon={isExpanded ? ChevronUp : ChevronDown}
                      label={isExpanded ? `Collapse ${rule.name}` : `Edit ${rule.name}`}
                      tone="sky"
                      ariaExpanded={isExpanded}
                      onClick={() => {
                        setExpandedRuleId(isExpanded ? null : ruleKey);
                      }}
                    />
                    <ActionIconButton
                      icon={Trash2}
                      label={`Remove ${rule.name}`}
                      tone="rose"
                      onClick={() => {
                        removeRule(idx);
                      }}
                    />
                  </div>
                </div>

                {/* Expanded inline editor */}
                {isExpanded ? (
                  <div className="grid gap-3 border-t border-border/70 px-4 py-4 sm:grid-cols-2 lg:grid-cols-4">
                    <div className="space-y-1 sm:col-span-2">
                      <Label className="text-xs">Rule name</Label>
                      <Input
                        value={rule.name}
                        onChange={(event) => {
                          updateRule(idx, { name: event.target.value });
                        }}
                      />
                    </div>

                    <div className="space-y-1">
                      <Label className="text-xs">Parser</Label>
                      <NativeSelect
                        value={rule.parser_mode}
                        onChange={(event) => {
                          updateRule(idx, { parser_mode: event.target.value as EmailParserMode });
                        }}
                      >
                        {PARSER_MODE_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </NativeSelect>
                    </div>

                    <div className="space-y-1">
                      <Label className="text-xs">Transaction type</Label>
                      <NativeSelect
                        value={rule.transaction_type}
                        onChange={(event) => {
                          updateRule(idx, {
                            transaction_type: event.target.value as EmailRuleTransactionType,
                          });
                        }}
                      >
                        {TXN_TYPE_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </NativeSelect>
                    </div>

                    <div className="space-y-1">
                      <Label className="text-xs">Sender contains</Label>
                      <Input
                        placeholder="e.g. nu.com.co"
                        value={rule.sender_match}
                        onChange={(event) => {
                          updateRule(idx, { sender_match: event.target.value });
                        }}
                      />
                    </div>

                    <div className="space-y-1">
                      <Label className="text-xs">Subject contains</Label>
                      <Input
                        placeholder="Optional keyword"
                        value={rule.subject_match}
                        onChange={(event) => {
                          updateRule(idx, { subject_match: event.target.value });
                        }}
                      />
                    </div>

                    <div className="space-y-1">
                      <Label className="text-xs">Target account</Label>
                      <NativeSelect
                        value={rule.default_account_id ?? ""}
                        onChange={(event) => {
                          updateRule(idx, { default_account_id: event.target.value || null });
                        }}
                      >
                        <option value="">Unassigned</option>
                        {accounts.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.name} ({a.currency})
                          </option>
                        ))}
                      </NativeSelect>
                    </div>

                    <div className="space-y-1">
                      <Label className="text-xs">Target category</Label>
                      <NativeSelect
                        value={rule.default_category_id ?? ""}
                        onChange={(event) => {
                          updateRule(idx, { default_category_id: event.target.value || null });
                        }}
                      >
                        <option value="">Unassigned</option>
                        {categories.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))}
                      </NativeSelect>
                    </div>

                    <div className="space-y-1">
                      <Label className="text-xs">Currency (ISO)</Label>
                      <Input
                        maxLength={3}
                        value={rule.currency}
                        onChange={(event) => {
                          updateRule(idx, { currency: event.target.value.toUpperCase() });
                        }}
                      />
                    </div>

                    <div className="space-y-1 sm:col-span-3">
                      <Label className="text-xs">
                        Custom amount regex (capture group 1 — optional)
                      </Label>
                      <Input
                        placeholder="e.g. \$([\d.,]+)"
                        value={rule.amount_regex}
                        onChange={(event) => {
                          updateRule(idx, { amount_regex: event.target.value });
                        }}
                      />
                    </div>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );

  const sandboxBlock = (
    <section
      aria-label="Test email parser"
      className="space-y-4 rounded-2xl border border-border bg-card p-5"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-700 dark:text-emerald-300">
            <FlaskConical aria-hidden="true" className="size-5" />
          </span>
          <div className="space-y-0.5">
            <h2 className="text-base font-semibold tracking-tight">Live Parser Sandbox</h2>
            <p className="text-sm text-muted-foreground">
              Dry-run any bank notification against your active rules — nothing is written to the
              ledger.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {(Object.keys(TEST_SAMPLES) as Array<keyof typeof TEST_SAMPLES>).map((key) => {
            const sample = TEST_SAMPLES[key];
            const isSelected = selectedSample === key;
            return (
              <button
                key={key}
                type="button"
                aria-pressed={isSelected}
                onClick={() => {
                  setSelectedSample(key);
                  setTestSender(sample.sender);
                  setTestSubject(sample.subject);
                  setTestBody(sample.body);
                  setTestResult(null);
                }}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-all",
                  isSelected ? sample.activeTone : sample.tone,
                )}
              >
                {isSelected ? <CheckCircle2 aria-hidden="true" className="size-3.5" /> : null}
                {sample.label}
              </button>
            );
          })}
          <Button
            type="button"
            size="sm"
            disabled={testParseMutation.isPending}
            onClick={() => {
              testParseMutation.mutate();
            }}
          >
            <FlaskConical aria-hidden="true" className="mr-1.5 size-4" />
            {testParseMutation.isPending ? "Testing…" : "Run test"}
          </Button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="test-email-sender" className="text-xs">
            Sample sender
          </Label>
          <Input
            id="test-email-sender"
            value={testSender}
            onChange={(event) => {
              setTestSender(event.target.value);
            }}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="test-email-subject" className="text-xs">
            Sample subject
          </Label>
          <Input
            id="test-email-subject"
            value={testSubject}
            onChange={(event) => {
              setTestSubject(event.target.value);
            }}
          />
        </div>
        <div className="space-y-1.5 sm:col-span-2">
          <Label htmlFor="test-email-body" className="text-xs">
            Sample email body
          </Label>
          <textarea
            id="test-email-body"
            rows={4}
            className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            value={testBody}
            onChange={(event) => {
              setTestBody(event.target.value);
            }}
          />
        </div>
      </div>

      {testResult ? (
        testResult.matched ? (
          <div className="grid gap-4 rounded-xl border border-emerald-500/35 bg-emerald-500/10 p-4 text-xs sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <p className="font-medium text-emerald-900/75 dark:text-emerald-200/75">
                Matched rule
              </p>
              <p className="mt-1 text-sm font-semibold text-emerald-950 dark:text-emerald-100">
                {testResult.matched_rule_name ?? "Built-in"}
              </p>
              <p className="mt-0.5 text-emerald-900/75 dark:text-emerald-200/75">
                Parser: {testResult.parser_used}
              </p>
            </div>
            <div>
              <p className="font-medium text-emerald-900/75 dark:text-emerald-200/75">
                Extracted amount
              </p>
              <p className="mt-1 text-base font-bold tabular-nums text-emerald-800 dark:text-emerald-300">
                {testResult.amount !== null && testResult.amount !== undefined
                  ? formatMoney(testResult.amount, testResult.currency ?? "COP")
                  : "—"}
              </p>
              <span
                className={cn(
                  "mt-1 inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium capitalize",
                  txnTypeBadgeStyle(testResult.transaction_type),
                )}
              >
                {testResult.transaction_type}
              </span>
            </div>
            <div>
              <p className="font-medium text-emerald-900/75 dark:text-emerald-200/75">
                Target account &amp; category
              </p>
              <p className="mt-1 font-semibold text-emerald-950 dark:text-emerald-100">
                {testResult.default_account_id
                  ? (accountNameById.get(testResult.default_account_id) ?? "Assigned")
                  : "Unassigned"}
              </p>
              <p className="mt-0.5 text-emerald-900/80 dark:text-emerald-200/80">
                {testResult.default_category_id
                  ? (categoryNameById.get(testResult.default_category_id) ?? "Assigned")
                  : "Unassigned"}
              </p>
            </div>
            <div>
              <p className="font-medium text-emerald-900/75 dark:text-emerald-200/75">
                Ledger description
              </p>
              <p className="mt-1 font-medium text-emerald-950 dark:text-emerald-100">
                {testResult.description || "—"}
              </p>
            </div>
          </div>
        ) : (
          <div
            role="alert"
            className="flex items-start gap-2.5 rounded-xl border border-amber-500/35 bg-amber-500/10 px-4 py-3 text-xs font-medium text-amber-900 dark:text-amber-200"
          >
            <ShieldAlert
              aria-hidden="true"
              className="mt-0.5 size-4 shrink-0 text-amber-600 dark:text-amber-400"
            />
            <span>{testResult.error ?? "No rule matched this email."}</span>
          </div>
        )
      ) : null}
    </section>
  );

  return (
    <div
      className={cn("flex flex-col gap-7", embedded ? "w-full" : "mx-auto w-full max-w-6xl pb-10")}
    >
      {headerBlock}
      {alertsBlock}
      {accessBlock}

      <details open className="group space-y-3">
        <summary className="flex cursor-pointer list-none items-center justify-between rounded-xl border border-border bg-muted/35 px-4 py-2.5 text-xs font-semibold text-foreground transition-colors hover:bg-muted/60 [&::-webkit-details-marker]:hidden">
          <span className="inline-flex items-center gap-2">
            <Filter aria-hidden="true" className="size-3.5 text-sky-600 dark:text-sky-400" />
            Mailbox Scope &amp; Bank Senders
            <span className="rounded-full bg-background px-2 py-0.5 text-[11px] font-medium tabular-nums text-muted-foreground">
              {senders.length} {senders.length === 1 ? "sender" : "senders"}
            </span>
          </span>
          <ChevronDown
            aria-hidden="true"
            className="size-4 text-muted-foreground transition-transform duration-200 group-open:rotate-180"
          />
        </summary>
        {filtersBlock}
      </details>

      <details open className="group space-y-3">
        <summary className="flex cursor-pointer list-none items-center justify-between rounded-xl border border-border bg-muted/35 px-4 py-2.5 text-xs font-semibold text-foreground transition-colors hover:bg-muted/60 [&::-webkit-details-marker]:hidden">
          <span className="inline-flex items-center gap-2">
            <SlidersHorizontal
              aria-hidden="true"
              className="size-3.5 text-violet-600 dark:text-violet-400"
            />
            Bank Parsing &amp; Routing Rules
            <span className="rounded-full bg-background px-2 py-0.5 text-[11px] font-medium tabular-nums text-muted-foreground">
              {activeRuleCount} active
            </span>
          </span>
          <ChevronDown
            aria-hidden="true"
            className="size-4 text-muted-foreground transition-transform duration-200 group-open:rotate-180"
          />
        </summary>
        {rulesBlock}
      </details>

      <details className="group space-y-3">
        <summary className="flex cursor-pointer list-none items-center justify-between rounded-xl border border-border bg-muted/35 px-4 py-2.5 text-xs font-semibold text-foreground transition-colors hover:bg-muted/60 [&::-webkit-details-marker]:hidden">
          <span className="inline-flex items-center gap-2">
            <FlaskConical
              aria-hidden="true"
              className="size-3.5 text-emerald-600 dark:text-emerald-400"
            />
            Live Parser Sandbox (dry-run)
          </span>
          <ChevronDown
            aria-hidden="true"
            className="size-4 text-muted-foreground transition-transform duration-200 group-open:rotate-180"
          />
        </summary>
        {sandboxBlock}
      </details>
    </div>
  );
}

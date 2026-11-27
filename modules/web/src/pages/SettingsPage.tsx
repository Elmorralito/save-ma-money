import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  ChevronDown,
  Download,
  Globe,
  Landmark,
  LayoutGrid,
  Mail,
  RotateCcw,
  Save,
  ShieldCheck,
  Sparkles,
  User,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { listIngestionConnections, type EmailIngestionConnection } from "@/api/ingestion";
import { accountsListQueryOptions, categoriesListQueryOptions } from "@/api/queries";
import { queryKeys } from "@/api/queryKeys";
import {
  getUserSettings,
  resetUserSettings,
  updateUserSettings,
  type SupportedCurrency,
  type SupportedDateFormat,
  type SupportedLocale,
  type SupportedPageSize,
  type UserPreferences,
} from "@/api/settings";
import { AISettingsPanel } from "@/components/settings/AISettingsPanel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { isLocale } from "@/i18n/locales";
import { useLocale } from "@/i18n/LocaleProvider";
import { formatApiError } from "@/lib/formatApiError";
import { cn } from "@/lib/utils";
import { EmailIngestionPage } from "@/pages/EmailIngestionPage";

const PICKER_PARAMS = { limit: 100, skip: 0 } as const;

const CURRENCY_OPTIONS: readonly SupportedCurrency[] = [
  "COP",
  "USD",
  "EUR",
  "GBP",
  "MXN",
  "CLP",
  "PEN",
  "BRL",
];
const LOCALE_OPTIONS: ReadonlyArray<{ value: SupportedLocale; label: string }> = [
  { value: "es-CO", label: "Spanish (Colombia — es-CO)" },
  { value: "en-US", label: "English (United States — en-US)" },
  { value: "es-ES", label: "Spanish (Spain — es-ES)" },
  { value: "en-GB", label: "English (United Kingdom — en-GB)" },
];
const TIMEZONE_OPTIONS = [
  "America/Bogota",
  "America/New_York",
  "America/Mexico_City",
  "America/Santiago",
  "America/Lima",
  "Europe/Madrid",
  "Europe/London",
  "UTC",
] as const;
const DATE_FORMAT_OPTIONS: readonly SupportedDateFormat[] = [
  "YYYY-MM-DD",
  "DD/MM/YYYY",
  "MM/DD/YYYY",
];
const PAGE_SIZE_OPTIONS: readonly SupportedPageSize[] = [10, 25, 50, 100];

const DEFAULT_PREFERENCES: UserPreferences = {
  base_currency: "COP",
  locale: "es-CO",
  timezone: "America/Bogota",
  date_format: "YYYY-MM-DD",
  default_page_size: 25,
  hide_balances_by_default: false,
  default_account_id: null,
  default_income_category_id: null,
  default_expense_category_id: null,
  credit_card_cashflow_only: true,
  auto_refresh_balances: true,
  fiscal_month_start_day: 1,
  payment_due_reminder_days: 5,
  low_runway_months_threshold: 3,
  high_utilization_pct_threshold: 30,
  large_transaction_alert_amount: null,
  redact_card_numbers: true,
  require_dkim_spf_for_email_ingestion: true,
  session_idle_timeout_minutes: 120,
};

type SectionFilter =
  "profile" | "display" | "ledger" | "alerts" | "security" | "integrations" | "ai" | "all";

type NavGroup = {
  key: "account" | "services" | "view";
  heading: string;
  items: ReadonlyArray<{ id: SectionFilter; label: string; icon: LucideIcon }>;
};

const NAV_GROUPS: ReadonlyArray<NavGroup> = [
  {
    key: "account",
    heading: "Account & Preferences",
    items: [
      { id: "profile", label: "Profile & Identity", icon: User },
      { id: "display", label: "Currency & Display", icon: Globe },
      { id: "ledger", label: "Ledger & Rules", icon: Landmark },
      { id: "alerts", label: "Alerts & Thresholds", icon: Bell },
      { id: "security", label: "Privacy & Security", icon: ShieldCheck },
    ],
  },
  {
    key: "services",
    heading: "Connected Services",
    items: [
      { id: "integrations", label: "Email & Gmail", icon: Mail },
      { id: "ai", label: "AI & LLM", icon: Sparkles },
    ],
  },
  {
    key: "view",
    heading: "View",
    items: [{ id: "all", label: "Show all sections", icon: LayoutGrid }],
  },
];

const VALID_TABS = new Set<SectionFilter>([
  "profile",
  "display",
  "ledger",
  "alerts",
  "security",
  "integrations",
  "ai",
  "all",
]);

export function SettingsPage() {
  const queryClient = useQueryClient();
  const { setLocale, applyUserDefaultLocale, messages } = useLocale();
  const st = messages.settings;
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = ((): SectionFilter => {
    const param = searchParams.get("tab") as SectionFilter | null;
    if (param && VALID_TABS.has(param)) {
      return param;
    }
    if (searchParams.get("gmail")) {
      return "integrations";
    }
    return "profile";
  })();
  const [activeTab, setActiveTab] = useState<SectionFilter>(initialTab);
  const [hydrated, setHydrated] = useState(false);

  const selectTab = (tab: SectionFilter) => {
    setActiveTab(tab);
    const next = new URLSearchParams(searchParams);
    if (tab === "profile") {
      next.delete("tab");
    } else {
      next.set("tab", tab);
    }
    setSearchParams(next, { replace: true });
  };

  const [displayName, setDisplayName] = useState("");
  const [phone, setPhone] = useState("");
  const [prefs, setPrefs] = useState<UserPreferences>(DEFAULT_PREFERENCES);
  const [largeTxnInput, setLargeTxnInput] = useState("");
  const [autoSave, setAutoSave] = useState<boolean>(() => {
    try {
      return window.localStorage.getItem("papita:settings:autosave") === "true";
    } catch {
      return false;
    }
  });
  const [autoSaveStatus, setAutoSaveStatus] = useState<"idle" | "saving" | "saved">("idle");
  const [emailSaveSignal, setEmailSaveSignal] = useState(0);
  const [aiSaveSignal, setAiSaveSignal] = useState(0);
  const lastSavedSnapshotRef = useRef<string>("");

  const settingsQuery = useQuery({
    queryKey: ["user-settings"],
    queryFn: ({ signal }) => getUserSettings(signal),
  });
  const accountsQuery = useQuery(accountsListQueryOptions(PICKER_PARAMS));
  const categoriesQuery = useQuery(categoriesListQueryOptions(PICKER_PARAMS));
  const connectionsQuery = useQuery({
    queryKey: queryKeys.ingestion.connections({ limit: 20, skip: 0 }),
    queryFn: ({ signal }) => listIngestionConnections({ limit: 20, skip: 0, signal }),
  });

  const settings = settingsQuery.data;
  const accounts = accountsQuery.data?.items ?? [];
  const categories = categoriesQuery.data?.items ?? [];
  const emailConn =
    ((connectionsQuery.data?.items ?? []) as unknown as EmailIngestionConnection[])[0] ?? null;

  const currentSnapshot = JSON.stringify({
    displayName: displayName.trim(),
    phone: phone.trim(),
    prefs,
    largeTxnInput: largeTxnInput.trim(),
  });
  // eslint-disable-next-line react-hooks/refs
  const isDirty = hydrated && currentSnapshot !== lastSavedSnapshotRef.current;

  useEffect(() => {
    if (!settings || hydrated) {
      return;
    }
    const nextDisplay = settings.display_name ?? "";
    const nextPhone = settings.phone ?? "";
    const nextLarge =
      settings.preferences.large_transaction_alert_amount !== null
        ? String(settings.preferences.large_transaction_alert_amount)
        : "";
    queueMicrotask(() => {
      setDisplayName(nextDisplay);
      setPhone(nextPhone);
      setPrefs(settings.preferences);
      if (isLocale(settings.preferences.locale)) {
        applyUserDefaultLocale(settings.preferences.locale);
      }
      setLargeTxnInput(nextLarge);
      setHydrated(true);
    });
    lastSavedSnapshotRef.current = JSON.stringify({
      displayName: nextDisplay.trim(),
      phone: nextPhone.trim(),
      prefs: settings.preferences,
      largeTxnInput: nextLarge.trim(),
    });
  }, [settings, hydrated]);

  const saveMutation = useMutation({
    mutationFn: (opts?: { silent?: boolean }) => {
      const parsedLarge = largeTxnInput.trim() ? Number(largeTxnInput.trim()) : null;
      return updateUserSettings({
        display_name: displayName.trim() || null,
        phone: phone.trim() || null,
        preferences: {
          ...prefs,
          large_transaction_alert_amount:
            parsedLarge !== null && Number.isFinite(parsedLarge) && parsedLarge > 0
              ? parsedLarge
              : null,
        },
      }).then((updated) => ({ updated, silent: Boolean(opts?.silent) }));
    },
    onSuccess: ({ updated, silent }) => {
      queryClient.setQueryData(["user-settings"], updated);
      void queryClient.invalidateQueries({ queryKey: queryKeys.auth.session() });
      lastSavedSnapshotRef.current = currentSnapshot;
      if (silent) {
        setAutoSaveStatus("saved");
      } else {
        setAutoSaveStatus("idle");
        toast.success("Settings saved to your profile.");
      }
    },
    onError: (err) => {
      setAutoSaveStatus("idle");
      toast.error(formatApiError(err, "Could not save settings."));
    },
  });

  useEffect(() => {
    try {
      window.localStorage.setItem("papita:settings:autosave", String(autoSave));
    } catch {
      // Ignore storage errors in restricted contexts.
    }
  }, [autoSave]);

  useEffect(() => {
    if (!autoSave || !hydrated || settingsQuery.isPending) {
      return;
    }
    if (currentSnapshot === lastSavedSnapshotRef.current) {
      return;
    }
    setAutoSaveStatus("saving");
    const timer = window.setTimeout(() => {
      saveMutation.mutate({ silent: true });
    }, 700);
    return () => {
      window.clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoSave, hydrated, currentSnapshot, settingsQuery.isPending]);

  const resetMutation = useMutation({
    mutationFn: () => resetUserSettings(),
    onSuccess: (updated) => {
      queryClient.setQueryData(["user-settings"], updated);
      setPrefs(updated.preferences);
      setLargeTxnInput("");
      lastSavedSnapshotRef.current = JSON.stringify({
        displayName: displayName.trim(),
        phone: phone.trim(),
        prefs: updated.preferences,
        largeTxnInput: "",
      });
      setAutoSaveStatus("idle");
      toast.success("Preferences reset to secure defaults.");
    },
    onError: (err) => {
      toast.error(formatApiError(err, "Could not reset preferences."));
    },
  });

  const exportSettings = () => {
    if (!settings) return;
    const blob = new Blob([JSON.stringify(settings, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `papita-settings-${settings.username}.json`;
    link.click();
    URL.revokeObjectURL(url);
    toast.success("Settings exported as JSON.");
  };

  const showSection = (id: SectionFilter) => activeTab === "all" || activeTab === id;
  const showProfileSaveActions = activeTab !== "integrations" && activeTab !== "ai";

  const handleUnifiedSave = () => {
    if (activeTab === "integrations") {
      setEmailSaveSignal((n) => n + 1);
      return;
    }
    if (activeTab === "ai") {
      setAiSaveSignal((n) => n + 1);
      return;
    }
    if (activeTab === "all") {
      saveMutation.mutate({});
      setEmailSaveSignal((n) => n + 1);
      setAiSaveSignal((n) => n + 1);
      return;
    }
    saveMutation.mutate({});
  };

  const renderSettingsShell = (
    variantLayout: "original" | "unified-1" | "unified-2",
    extraClass?: string,
  ) => (
    <div className={cn("mx-auto w-full max-w-6xl space-y-6 pb-12", extraClass)}>
      <header className="relative overflow-hidden rounded-2xl bg-[#04090c] p-6 text-white">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -top-24 -right-20 size-72 rounded-full bg-emerald-500/18 blur-3xl"
        />
        <div className="relative grid gap-5 lg:grid-cols-[1fr_272px] lg:items-center">
          <div className="space-y-4">
            <div className="max-w-2xl space-y-2">
              <div className="flex flex-wrap items-center gap-2.5">
                <h1 className="text-2xl font-semibold tracking-tight text-white">{st.title}</h1>
                {isDirty && !autoSave ? (
                  <span className="inline-flex items-center rounded-full bg-amber-500/20 px-2.5 py-0.5 text-[11px] font-medium text-amber-200">
                    {st.unsavedChanges}
                  </span>
                ) : null}
              </div>
              <p className="text-sm leading-relaxed text-slate-300">{st.subtitle}</p>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 font-medium text-slate-200 tabular-nums">
                <Globe aria-hidden="true" className="size-3.5 text-emerald-400" />
                {prefs.base_currency} · {prefs.locale}
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 font-medium text-slate-200 tabular-nums">
                <Landmark aria-hidden="true" className="size-3.5 text-violet-300" />
                {st.header.fiscalDayPrefix} {prefs.fiscal_month_start_day}{" "}
                {st.header.fiscalDaySuffix}
              </span>
              <span
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full px-3 py-1 font-medium",
                  emailConn?.gmail_access_enabled
                    ? "bg-emerald-500/20 text-emerald-300"
                    : "bg-amber-500/20 text-amber-200",
                )}
              >
                <Mail aria-hidden="true" className="size-3.5" />
                {emailConn?.gmail_access_enabled ? st.header.gmailActive : st.header.gmailPaused}
              </span>
              <button
                type="button"
                onClick={exportSettings}
                disabled={!settings}
                className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/[0.06] px-3 py-1 font-medium text-slate-200 transition-colors hover:bg-white/12 disabled:opacity-45"
              >
                <Download aria-hidden="true" className="size-3.5 text-sky-300" />
                {st.export}
              </button>
              {showProfileSaveActions ? (
                <button
                  type="button"
                  disabled={resetMutation.isPending}
                  onClick={() => resetMutation.mutate()}
                  className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/[0.06] px-3 py-1 font-medium text-slate-200 transition-colors hover:bg-white/12 disabled:opacity-45"
                >
                  <RotateCcw aria-hidden="true" className="size-3.5 text-amber-300" />
                  {st.reset}
                </button>
              ) : null}
            </div>
          </div>

          <div className="flex flex-col gap-3 rounded-xl border border-white/10 bg-white/[0.05] p-4">
            <label className="flex cursor-pointer select-none items-center justify-between gap-3">
              <div className="space-y-0.5">
                <div className="text-xs font-semibold text-white">{st.autosave}</div>
                <div className="text-[11px] text-slate-400">
                  {autoSaveStatus === "saving"
                    ? st.saving
                    : autoSaveStatus === "saved"
                      ? st.saved
                      : autoSave
                        ? st.header.autosaveOnHint
                        : st.header.autosaveManualHint}
                </div>
              </div>
              <input
                type="checkbox"
                checked={autoSave}
                onChange={(event) => {
                  setAutoSave(event.target.checked);
                  if (!event.target.checked) setAutoSaveStatus("idle");
                }}
                className="sr-only"
                aria-label={st.autosave}
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
              disabled={saveMutation.isPending || settingsQuery.isPending}
              onClick={handleUnifiedSave}
              className="w-full bg-emerald-500 text-slate-950 hover:bg-emerald-400"
            >
              <Save aria-hidden="true" className="mr-1.5 size-4" />
              {saveMutation.isPending ? st.saving : st.saveChanges}
            </Button>
          </div>
        </div>
      </header>

      {settingsQuery.isError ? (
        <p
          role="alert"
          className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive"
        >
          {formatApiError(settingsQuery.error, st.header.loadError)}
        </p>
      ) : null}

      {/* Two-column Settings Workspace */}
      <div className="grid gap-6 lg:grid-cols-[14.5rem_1fr] lg:items-start">
        {/* Left Navigation Rail */}
        <nav aria-label="Settings sections" className="space-y-5 lg:sticky lg:top-20">
          {NAV_GROUPS.map((group) => (
            <div key={group.key} className="space-y-1">
              <p className="px-2.5 text-[11px] font-semibold text-muted-foreground/80">
                {st.groups[group.key] ?? group.heading}
              </p>
              <div className="flex flex-wrap gap-1 lg:flex-col">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const active = activeTab === item.id;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      aria-current={active ? "page" : undefined}
                      onClick={() => selectTab(item.id)}
                      className={cn(
                        "flex items-center justify-between gap-2 rounded-lg px-2.5 py-2 text-left text-sm font-medium transition-colors",
                        active
                          ? "bg-primary/10 text-primary"
                          : "text-muted-foreground hover:bg-muted/70 hover:text-foreground",
                      )}
                    >
                      <span className="flex items-center gap-2.5">
                        <Icon aria-hidden="true" className="size-4 shrink-0" />
                        <span>{st.tabs[item.id] ?? item.label}</span>
                      </span>
                      {item.id === "integrations" ? (
                        <span
                          className={cn(
                            "size-2 shrink-0 rounded-full",
                            emailConn?.gmail_access_enabled ? "bg-emerald-500" : "bg-amber-500",
                          )}
                          title={
                            emailConn?.gmail_access_enabled
                              ? st.header.gmailActive
                              : st.header.gmailPaused
                          }
                        />
                      ) : null}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Focused Right Pane */}
        <div className="min-w-0 flex flex-col gap-7 animate-in fade-in-0 duration-150">
          {/* Profile & Identity */}
          {showSection("profile") ? (
            <details open className="group space-y-3">
              <summary className="flex cursor-pointer list-none items-center justify-between rounded-xl border border-border bg-muted/35 px-4 py-2.5 text-xs font-semibold text-foreground transition-colors hover:bg-muted/60 [&::-webkit-details-marker]:hidden">
                <span className="inline-flex items-center gap-2">
                  <User
                    aria-hidden="true"
                    className="size-3.5 text-emerald-600 dark:text-emerald-400"
                  />
                  {st.profile.heading}
                  {settings?.username ? (
                    <span className="rounded-full bg-background px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                      {settings.username}
                    </span>
                  ) : null}
                </span>
                <ChevronDown
                  aria-hidden="true"
                  className="size-4 text-muted-foreground transition-transform duration-200 group-open:rotate-180"
                />
              </summary>
              <section
                aria-label={st.profile.heading}
                className="rounded-2xl border border-border bg-card p-6 text-base"
              >
                <div className="mb-5 border-b border-border/70 pb-4">
                  <h2 className="text-[1.1875rem] font-semibold leading-tight tracking-[-0.025em] text-balance text-foreground">
                    {st.profile.heading}
                  </h2>
                  <p className="mt-1 text-[0.8125rem] leading-normal text-pretty text-muted-foreground">
                    {st.profile.description}
                  </p>
                </div>
                <div className="grid gap-5 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="settings-display-name" className="text-[0.8125rem] font-medium">
                      {st.profile.displayName}
                    </Label>
                    <Input
                      id="settings-display-name"
                      placeholder={st.profile.displayNamePlaceholder}
                      value={displayName}
                      onChange={(event) => setDisplayName(event.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="settings-phone" className="text-[0.8125rem] font-medium">
                      {st.profile.phone}
                    </Label>
                    <Input
                      id="settings-phone"
                      className="tabular-nums"
                      placeholder={st.profile.phonePlaceholder}
                      value={phone}
                      onChange={(event) => setPhone(event.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="settings-email" className="text-[0.8125rem] font-medium">
                      {st.profile.emailManaged}
                    </Label>
                    <Input id="settings-email" value={settings?.email ?? ""} disabled />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="settings-username" className="text-[0.8125rem] font-medium">
                      {st.profile.usernameProvider}
                    </Label>
                    <Input
                      id="settings-username"
                      value={
                        settings
                          ? `${settings.username} · ${settings.provider_type} (${settings.auth_provider})`
                          : ""
                      }
                      disabled
                    />
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 sm:col-span-2">
                    <div className="flex flex-wrap items-center gap-2.5">
                      <Mail aria-hidden="true" className="size-4 text-primary" />
                      <span className="text-sm font-medium">{st.profile.gmailIngestion}</span>
                      <span
                        className={
                          emailConn?.gmail_access_enabled
                            ? "inline-flex rounded-full border border-emerald-500/30 bg-emerald-500/12 px-2.5 py-0.5 text-xs font-medium text-emerald-800 dark:text-emerald-300"
                            : "inline-flex rounded-full border border-amber-500/30 bg-amber-500/12 px-2.5 py-0.5 text-xs font-medium text-amber-800 dark:text-amber-300"
                        }
                      >
                        {emailConn?.gmail_access_enabled ? st.profile.enabled : st.profile.disabled}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {emailConn?.gmail_access_enabled
                          ? emailConn.gmail_connected_email
                            ? `${st.profile.pollingPrefix} ${emailConn.gmail_connected_email}`
                            : st.profile.activeForAccount
                          : st.profile.failClosedHint}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => selectTab("integrations")}
                      className="text-xs font-semibold text-primary hover:underline"
                    >
                      {st.profile.manageInEmailGmail}
                    </button>
                  </div>
                </div>
              </section>
            </details>
          ) : null}

          {/* Currency, Locale & Display */}
          {showSection("display") ? (
            <details open className="group space-y-3">
              <summary className="flex cursor-pointer list-none items-center justify-between rounded-xl border border-border bg-muted/35 px-4 py-2.5 text-xs font-semibold text-foreground transition-colors hover:bg-muted/60 [&::-webkit-details-marker]:hidden">
                <span className="inline-flex items-center gap-2">
                  <Globe aria-hidden="true" className="size-3.5 text-sky-600 dark:text-sky-400" />
                  {st.display.heading}
                  <span className="rounded-full bg-background px-2 py-0.5 text-[11px] font-medium tabular-nums text-muted-foreground">
                    {prefs.base_currency} · {prefs.locale}
                  </span>
                </span>
                <ChevronDown
                  aria-hidden="true"
                  className="size-4 text-muted-foreground transition-transform duration-200 group-open:rotate-180"
                />
              </summary>
              <section
                aria-label={st.display.heading}
                className="rounded-2xl border border-border bg-card p-5"
              >
                <div className="mb-4 border-b border-border pb-3.5">
                  <h2 className="text-base font-semibold tracking-tight">{st.display.heading}</h2>
                  <p className="mt-0.5 text-xs text-muted-foreground">{st.display.description}</p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <div className="space-y-1.5">
                    <Label htmlFor="settings-base-currency">{st.display.baseCurrency}</Label>
                    <NativeSelect
                      id="settings-base-currency"
                      value={prefs.base_currency}
                      onChange={(event) =>
                        setPrefs((prev) => ({
                          ...prev,
                          base_currency: event.target.value as SupportedCurrency,
                        }))
                      }
                    >
                      {CURRENCY_OPTIONS.map((cur) => (
                        <option key={cur} value={cur}>
                          {cur}
                        </option>
                      ))}
                    </NativeSelect>
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="settings-locale">{st.display.locale}</Label>
                    <NativeSelect
                      id="settings-locale"
                      value={prefs.locale}
                      onChange={(event) => {
                        const nextLocale = event.target.value as SupportedLocale;
                        setPrefs((prev) => ({ ...prev, locale: nextLocale }));
                        if (isLocale(nextLocale)) {
                          setLocale(nextLocale);
                        }
                      }}
                    >
                      {LOCALE_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </NativeSelect>
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="settings-timezone">{st.display.timezone}</Label>
                    <NativeSelect
                      id="settings-timezone"
                      value={prefs.timezone}
                      onChange={(event) =>
                        setPrefs((prev) => ({ ...prev, timezone: event.target.value }))
                      }
                    >
                      {TIMEZONE_OPTIONS.map((tz) => (
                        <option key={tz} value={tz}>
                          {tz}
                        </option>
                      ))}
                    </NativeSelect>
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="settings-date-format">{st.display.dateFormat}</Label>
                    <NativeSelect
                      id="settings-date-format"
                      value={prefs.date_format}
                      onChange={(event) =>
                        setPrefs((prev) => ({
                          ...prev,
                          date_format: event.target.value as SupportedDateFormat,
                        }))
                      }
                    >
                      {DATE_FORMAT_OPTIONS.map((fmt) => (
                        <option key={fmt} value={fmt}>
                          {fmt}
                        </option>
                      ))}
                    </NativeSelect>
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="settings-page-size">{st.display.pageSize}</Label>
                    <NativeSelect
                      id="settings-page-size"
                      value={String(prefs.default_page_size)}
                      onChange={(event) =>
                        setPrefs((prev) => ({
                          ...prev,
                          default_page_size: Number(event.target.value) as SupportedPageSize,
                        }))
                      }
                    >
                      {PAGE_SIZE_OPTIONS.map((sz) => (
                        <option key={sz} value={sz}>
                          {sz} {st.display.rowsPerPage}
                        </option>
                      ))}
                    </NativeSelect>
                  </div>
                  <label
                    className={cn(
                      "flex cursor-pointer items-center justify-between gap-3 self-end rounded-xl border px-3.5 py-2.5 text-sm transition-colors",
                      prefs.hide_balances_by_default
                        ? "border-emerald-500/35 bg-emerald-500/8"
                        : "border-border bg-muted/25 hover:bg-muted/40",
                    )}
                  >
                    <span className="text-xs font-semibold">{st.display.hideBalances}</span>
                    <input
                      type="checkbox"
                      checked={prefs.hide_balances_by_default}
                      onChange={(event) =>
                        setPrefs((prev) => ({
                          ...prev,
                          hide_balances_by_default: event.target.checked,
                        }))
                      }
                      className="size-4 accent-emerald-600"
                    />
                  </label>
                </div>
              </section>
            </details>
          ) : null}

          {/* Ledger & Reconciliation Defaults */}
          {showSection("ledger") ? (
            <details open className="group space-y-3">
              <summary className="flex cursor-pointer list-none items-center justify-between rounded-xl border border-border bg-muted/35 px-4 py-2.5 text-xs font-semibold text-foreground transition-colors hover:bg-muted/60 [&::-webkit-details-marker]:hidden">
                <span className="inline-flex items-center gap-2">
                  <Landmark
                    aria-hidden="true"
                    className="size-3.5 text-violet-600 dark:text-violet-400"
                  />
                  {st.ledger.heading}
                  <span className="rounded-full bg-background px-2 py-0.5 text-[11px] font-medium tabular-nums text-muted-foreground">
                    {st.ledger.dayPrefix} {prefs.fiscal_month_start_day}
                  </span>
                </span>
                <ChevronDown
                  aria-hidden="true"
                  className="size-4 text-muted-foreground transition-transform duration-200 group-open:rotate-180"
                />
              </summary>
              <section
                aria-label={st.ledger.heading}
                className="rounded-2xl border border-border bg-card p-5"
              >
                <div className="mb-4 border-b border-border pb-3.5">
                  <h2 className="text-base font-semibold tracking-tight">{st.ledger.heading}</h2>
                  <p className="mt-0.5 text-xs text-muted-foreground">{st.ledger.description}</p>
                </div>
                <div className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-1.5">
                      <Label htmlFor="settings-default-account">{st.ledger.defaultAccount}</Label>
                      <NativeSelect
                        id="settings-default-account"
                        value={prefs.default_account_id ?? ""}
                        onChange={(event) =>
                          setPrefs((prev) => ({
                            ...prev,
                            default_account_id: event.target.value || null,
                          }))
                        }
                      >
                        <option value="">{st.ledger.noneSelected}</option>
                        {accounts.map((acc) => (
                          <option key={acc.id} value={acc.id}>
                            {acc.name} ({acc.currency})
                          </option>
                        ))}
                      </NativeSelect>
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="settings-fiscal-day">{st.ledger.fiscalDay}</Label>
                      <Input
                        id="settings-fiscal-day"
                        type="number"
                        min={1}
                        max={28}
                        value={prefs.fiscal_month_start_day}
                        onChange={(event) =>
                          setPrefs((prev) => ({
                            ...prev,
                            fiscal_month_start_day: Number(event.target.value) || 1,
                          }))
                        }
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="settings-default-income-cat">
                        {st.ledger.defaultIncomeCategory}
                      </Label>
                      <NativeSelect
                        id="settings-default-income-cat"
                        value={prefs.default_income_category_id ?? ""}
                        onChange={(event) =>
                          setPrefs((prev) => ({
                            ...prev,
                            default_income_category_id: event.target.value || null,
                          }))
                        }
                      >
                        <option value="">{st.ledger.noneSelected}</option>
                        {categories.map((cat) => (
                          <option key={cat.id} value={cat.id}>
                            {cat.name}
                          </option>
                        ))}
                      </NativeSelect>
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="settings-default-expense-cat">
                        {st.ledger.defaultExpenseCategory}
                      </Label>
                      <NativeSelect
                        id="settings-default-expense-cat"
                        value={prefs.default_expense_category_id ?? ""}
                        onChange={(event) =>
                          setPrefs((prev) => ({
                            ...prev,
                            default_expense_category_id: event.target.value || null,
                          }))
                        }
                      >
                        <option value="">{st.ledger.noneSelected}</option>
                        {categories.map((cat) => (
                          <option key={cat.id} value={cat.id}>
                            {cat.name}
                          </option>
                        ))}
                      </NativeSelect>
                    </div>
                  </div>

                  <div className="grid gap-2.5 sm:grid-cols-2">
                    <label
                      className={cn(
                        "flex cursor-pointer items-center justify-between gap-3 rounded-xl border px-3.5 py-3 text-sm transition-colors",
                        prefs.credit_card_cashflow_only
                          ? "border-emerald-500/35 bg-emerald-500/8"
                          : "border-border bg-muted/25 hover:bg-muted/40",
                      )}
                    >
                      <div>
                        <p className="text-xs font-semibold">{st.ledger.ccCashflowTitle}</p>
                        <p className="text-[11px] text-muted-foreground">
                          {st.ledger.ccCashflowHint}
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        aria-label={st.ledger.ccCashflowTitle}
                        checked={prefs.credit_card_cashflow_only}
                        onChange={(event) =>
                          setPrefs((prev) => ({
                            ...prev,
                            credit_card_cashflow_only: event.target.checked,
                          }))
                        }
                        className="size-4 shrink-0 accent-emerald-600"
                      />
                    </label>
                    <label
                      className={cn(
                        "flex cursor-pointer items-center justify-between gap-3 rounded-xl border px-3.5 py-3 text-sm transition-colors",
                        prefs.auto_refresh_balances
                          ? "border-emerald-500/35 bg-emerald-500/8"
                          : "border-border bg-muted/25 hover:bg-muted/40",
                      )}
                    >
                      <div>
                        <p className="text-xs font-semibold">{st.ledger.autoRefreshTitle}</p>
                        <p className="text-[11px] text-muted-foreground">
                          {st.ledger.autoRefreshHint}
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        aria-label={st.ledger.autoRefreshTitle}
                        checked={prefs.auto_refresh_balances}
                        onChange={(event) =>
                          setPrefs((prev) => ({
                            ...prev,
                            auto_refresh_balances: event.target.checked,
                          }))
                        }
                        className="size-4 shrink-0 accent-emerald-600"
                      />
                    </label>
                  </div>
                </div>
              </section>
            </details>
          ) : null}

          {/* Alerts & Thresholds */}
          {showSection("alerts") ? (
            <details open className="group space-y-3">
              <summary className="flex cursor-pointer list-none items-center justify-between rounded-xl border border-border bg-muted/35 px-4 py-2.5 text-xs font-semibold text-foreground transition-colors hover:bg-muted/60 [&::-webkit-details-marker]:hidden">
                <span className="inline-flex items-center gap-2">
                  <Bell
                    aria-hidden="true"
                    className="size-3.5 text-amber-600 dark:text-amber-400"
                  />
                  {st.alerts.heading}
                  <span className="rounded-full bg-background px-2 py-0.5 text-[11px] font-medium tabular-nums text-muted-foreground">
                    {prefs.payment_due_reminder_days}d · {prefs.high_utilization_pct_threshold}%
                  </span>
                </span>
                <ChevronDown
                  aria-hidden="true"
                  className="size-4 text-muted-foreground transition-transform duration-200 group-open:rotate-180"
                />
              </summary>
              <section
                aria-label={st.alerts.heading}
                className="rounded-2xl border border-border bg-card p-5"
              >
                <div className="mb-4 border-b border-border pb-3.5">
                  <h2 className="text-base font-semibold tracking-tight">{st.alerts.heading}</h2>
                  <p className="mt-0.5 text-xs text-muted-foreground">{st.alerts.description}</p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label htmlFor="settings-due-days">{st.alerts.dueDays}</Label>
                    <Input
                      id="settings-due-days"
                      type="number"
                      min={1}
                      max={30}
                      value={prefs.payment_due_reminder_days}
                      onChange={(event) =>
                        setPrefs((prev) => ({
                          ...prev,
                          payment_due_reminder_days: Number(event.target.value) || 5,
                        }))
                      }
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="settings-runway-months">{st.alerts.runwayMonths}</Label>
                    <Input
                      id="settings-runway-months"
                      type="number"
                      min={1}
                      max={24}
                      value={prefs.low_runway_months_threshold}
                      onChange={(event) =>
                        setPrefs((prev) => ({
                          ...prev,
                          low_runway_months_threshold: Number(event.target.value) || 3,
                        }))
                      }
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="settings-util-pct">{st.alerts.highUtilPct}</Label>
                    <Input
                      id="settings-util-pct"
                      type="number"
                      min={10}
                      max={100}
                      value={prefs.high_utilization_pct_threshold}
                      onChange={(event) =>
                        setPrefs((prev) => ({
                          ...prev,
                          high_utilization_pct_threshold: Number(event.target.value) || 30,
                        }))
                      }
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="settings-large-txn">
                      {st.alerts.largeTxn} ({prefs.base_currency})
                    </Label>
                    <Input
                      id="settings-large-txn"
                      type="number"
                      min={0}
                      placeholder={st.alerts.largeTxnPlaceholder}
                      value={largeTxnInput}
                      onChange={(event) => setLargeTxnInput(event.target.value)}
                    />
                  </div>
                </div>
              </section>
            </details>
          ) : null}

          {/* Privacy & Security */}
          {showSection("security") ? (
            <details open className="group space-y-3">
              <summary className="flex cursor-pointer list-none items-center justify-between rounded-xl border border-border bg-muted/35 px-4 py-2.5 text-xs font-semibold text-foreground transition-colors hover:bg-muted/60 [&::-webkit-details-marker]:hidden">
                <span className="inline-flex items-center gap-2">
                  <ShieldCheck
                    aria-hidden="true"
                    className="size-3.5 text-emerald-600 dark:text-emerald-400"
                  />
                  {st.security.heading}
                  <span className="rounded-full bg-background px-2 py-0.5 text-[11px] font-medium tabular-nums text-muted-foreground">
                    {prefs.session_idle_timeout_minutes}
                    {st.security.idleSuffix}
                  </span>
                </span>
                <ChevronDown
                  aria-hidden="true"
                  className="size-4 text-muted-foreground transition-transform duration-200 group-open:rotate-180"
                />
              </summary>
              <section
                aria-label={st.security.heading}
                className="rounded-2xl border border-border bg-card p-5"
              >
                <div className="mb-4 border-b border-border pb-3.5">
                  <h2 className="text-base font-semibold tracking-tight">{st.security.heading}</h2>
                  <p className="mt-0.5 text-xs text-muted-foreground">{st.security.description}</p>
                </div>
                <div className="space-y-4">
                  <div className="grid gap-2.5 sm:grid-cols-2">
                    <label
                      className={cn(
                        "flex cursor-pointer items-center justify-between gap-3 rounded-xl border px-3.5 py-3 text-sm transition-colors",
                        prefs.redact_card_numbers
                          ? "border-emerald-500/35 bg-emerald-500/8"
                          : "border-border bg-muted/25 hover:bg-muted/40",
                      )}
                    >
                      <div>
                        <p className="text-xs font-semibold">{st.security.redactCardTitle}</p>
                        <p className="text-[11px] text-muted-foreground">
                          {st.security.redactCardHint}
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        aria-label={st.security.redactCardTitle}
                        checked={prefs.redact_card_numbers}
                        onChange={(event) =>
                          setPrefs((prev) => ({
                            ...prev,
                            redact_card_numbers: event.target.checked,
                          }))
                        }
                        className="size-4 shrink-0 accent-emerald-600"
                      />
                    </label>
                    <label
                      className={cn(
                        "flex cursor-pointer items-center justify-between gap-3 rounded-xl border px-3.5 py-3 text-sm transition-colors",
                        prefs.require_dkim_spf_for_email_ingestion
                          ? "border-emerald-500/35 bg-emerald-500/8"
                          : "border-border bg-muted/25 hover:bg-muted/40",
                      )}
                    >
                      <div>
                        <p className="text-xs font-semibold">{st.security.dkimSpfTitle}</p>
                        <p className="text-[11px] text-muted-foreground">
                          {st.security.dkimSpfHint}
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        aria-label={st.security.dkimSpfTitle}
                        checked={prefs.require_dkim_spf_for_email_ingestion}
                        onChange={(event) =>
                          setPrefs((prev) => ({
                            ...prev,
                            require_dkim_spf_for_email_ingestion: event.target.checked,
                          }))
                        }
                        className="size-4 shrink-0 accent-emerald-600"
                      />
                    </label>
                  </div>

                  <div className="max-w-xs space-y-1.5">
                    <Label htmlFor="settings-idle-timeout">{st.security.idleTimeout}</Label>
                    <Input
                      id="settings-idle-timeout"
                      type="number"
                      min={15}
                      max={1440}
                      value={prefs.session_idle_timeout_minutes}
                      onChange={(event) =>
                        setPrefs((prev) => ({
                          ...prev,
                          session_idle_timeout_minutes: Number(event.target.value) || 120,
                        }))
                      }
                    />
                  </div>
                </div>
              </section>
            </details>
          ) : null}

          {/* Email & Gmail Integrations */}
          {showSection("integrations") ? (
            <div aria-label="Integrations settings" className="space-y-4">
              <EmailIngestionPage
                embedded
                externalAutoSave={autoSave}
                saveSignal={emailSaveSignal}
              />
            </div>
          ) : null}

          {/* AI & LLM */}
          {showSection("ai") ? (
            <div aria-label="AI and LLM settings" className="space-y-4">
              <AISettingsPanel embedded saveSignal={aiSaveSignal} variantLayout={variantLayout} />
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );

  return renderSettingsShell("unified-1", "papita-settings-shell");
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  KeyRound,
  Loader2,
  Plug,
  RefreshCw,
  Save,
  Server,
  ShieldCheck,
  Sparkles,
  Terminal,
  Trash2,
  XCircle,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import {
  fetchAIModels,
  getAIConfig,
  getAIStatus,
  sendAIChat,
  updateAIConfig,
  type AIMode,
  type AIModelOption,
} from "@/api/ai";
import {
  bridgeChat,
  bridgeListModels,
  detectCliBridge,
  requestCliBridgePermission,
  revokeCliBridgePermission,
} from "@/api/cliBridge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { useLocale } from "@/i18n/LocaleProvider";
import { LOCALE_TO_LANGUAGE } from "@/i18n/locales";
import { formatApiError } from "@/lib/formatApiError";
import { cn } from "@/lib/utils";

const AI_COPY = {
  en: {
    headlessTitle: "Local AI CLI",
    headlessDesc: "Pinned local CLIs (agy, claude, codex, cursor) via the single-owner sidecar.",
    lanTitle: "Built-in Model",
    lanDesc:
      "Built-in financial model, local Ollama, or OpenAI-compatible local server (zero cloud egress).",
    apiTitle: "Direct Cloud API",
    apiDesc:
      "OpenAI (GPT), Anthropic (Claude), or Google Gemini with Fernet-encrypted keys at rest.",
    grantCliBanner: "Grant Local AI CLI permission to inspect and select local machine CLIs.",
    grantLanBanner: "Grant Built-in Model permission to discover and connect local endpoints.",
    grantApiBanner: "Grant Direct Cloud API permission to configure provider keys and models.",
    localClisBadge: "Local CLIs",
    lanEndpointBadge: "Built-in Endpoint",
    apiClientBadge: "API Client",
    grantBtnPrefix: "Grant",
    testConnection: "Test connection",
    summaryTitle: "Provider Mode, Permissions & Model ID",
    permCliTitle: "Local AI CLI Integration Permissions & Guardrails",
    permLanTitle: "Built-in Model Permissions & Guardrails",
    permApiTitle: "Direct Cloud API Integration Permissions & Guardrails",
    permGranted: "Permission granted",
    grantPerm: "Grant permission",
    cliConnLabel: "Local AI CLI Connection",
    lanConnLabel: "Built-in / Local Model Provider",
    apiConnLabel: "Cloud API Provider",
    lanUrlLabel: "LAN Inference Base URL",
    apiKeyLabel: "API Key",
    baseUrlOptLabel: "Base URL (optional)",
    exactModelLabel: "Exact Model ID",
    refreshModels: "Refresh models",
    connectLoad: "Connect & load models",
    providerDefault: "Provider default",
    customModelOpt: "Custom model ID…",
    customModelPlaceholder: "Enter exact custom model ID…",
    grantToConnectHint:
      "Grant the integration permission above to connect and load selectable model IDs.",
    enterKeyHint:
      "Enter your API key and click Connect & load models to populate the model ID dropdown.",
    clickConnectHint: "Click Connect & load models to fetch exact model IDs from this provider.",
    attachContextTitle: "Attach redacted financial-health summary by default",
    attachContextDesc:
      "Net worth, runway, and debt ratio only — never raw account numbers or emails.",
    attachContextDetail:
      "Includes aggregated balances, cash runway months, and debt-to-asset ratio. Strips IBANs, card numbers, emails, and transaction descriptions.",
    attachContextTags: ["Redacted", "Read-only", "No PII"],
    reportsAiTitle: "Enable AI in Reports",
    reportsAiDesc:
      "Allow contextual AI analysis inside Reports views and cards (Cashflow, Spending, Debt, Investments).",
    reportsAiDetail:
      "Adds inline AI triggers to Cashflow Waterfall, Planned vs Actual, Spending Breakdown, and Debt Paydown views using only visible summary totals.",
    reportsAiTags: ["Cashflow", "Spending", "Debt", "Read-only"],
    duesAiTitle: "Enable AI in Payment Dues",
    duesAiDesc:
      "Allow contextual AI assistance for recurring bills, due-date prioritization, and reminders.",
    duesAiDetail:
      "Surfaces due-date prioritization, overdue risk checks, and missing-payment detection on the Payment Dues table without mutating schedules.",
    duesAiTags: ["Bills", "Due dates", "Read-only"],
    enablementsHeading: "AI Module Enablements & Context",
    activeLabel: "Enabled",
    pausedLabel: "Disabled",
    saveBtn: "Save LLM settings",
    savingBtn: "Saving…",
    testOkTitle: "Connection verified",
    testFailTitle: "Connection failed",
    testReplyLabel: "Model reply",
    cliBullets: [
      "Execute pinned local CLI binary (shell=False) with scrubbed database & OAuth secrets.",
      "Run model discovery (e.g. agy models) and single-turn prompts with all shell/file tools disabled.",
      "Read-only boundary: cannot mutate PostgreSQL, post transactions, or trigger transfers.",
    ],
    cliRiskModalTitle: "Security Warning: Enable Local AI CLI Access?",
    cliRiskModalDesc:
      "Allowing this web app to invoke local AI CLIs (agy, claude, codex, cursor) bridges your browser to executables on your machine. Review what can happen before accepting:",
    cliRiskItems: [
      "OS user-level execution: The CLI binary runs under your OS user account using your active local CLI login, credentials, and configuration.",
      "External data egress & usage: Prompts, visible UI context, and any attached financial summary leave your browser and are sent to the CLI's upstream AI provider (Google, Anthropic, OpenAI, Cursor), counting against your quota or billing.",
      "Prompt-injection & local plugin risks: Even though Papita enforces shell=False, a binary allowlist, and scrubbed DB/OAuth env vars, CLI bugs or locally enabled MCP/CLI plugins could expose local state or behave unexpectedly.",
      "Origin-wide trust while enabled: Any script running on this origin can invoke the local CLI bridge while permission is active. Only enable on trusted local/self-hosted origins — you can revoke access at any time.",
    ],
    cliRiskAckLabel:
      "I understand what might happen and accept the security and privacy risks of allowing this page to run local AI CLIs.",
    cliRiskCancel: "Cancel",
    cliRiskConfirm: "I understand — Allow CLI Access",
    lanBullets: [
      "Connect to your configured private LAN inference server (OpenAI-compatible /v1 or Ollama /api) with zero public cloud egress.",
      "SSRF guardrails block cloud metadata IPs (169.254.169.254), link-local addresses, and embedded URL credentials.",
      "Read-only boundary: receives only aggregated non-PII financial metrics and sanitized UI context; cannot modify ledger state.",
    ],
    apiBullets: [
      "Store your provider API key Fernet-encrypted at rest and query the provider's public /models catalog.",
      "SSRF guardrails restrict cloud API endpoints to public HTTPS hosts (private/LAN IPs rejected).",
      "Read-only boundary: sends only your prompt and optional redacted financial summary (never raw account numbers or emails).",
    ],
  },
  es: {
    headlessTitle: "CLI de IA local",
    headlessDesc:
      "CLIs locales fijados (agy, claude, codex, cursor) mediante el sidecar de propietario único.",
    lanTitle: "Modelo integrado",
    lanDesc:
      "Modelo financiero integrado, Ollama local o servidor compatible con OpenAI (sin salida a la nube).",
    apiTitle: "API directa en la nube",
    apiDesc:
      "OpenAI (GPT), Anthropic (Claude) o Google Gemini con llaves cifradas Fernet en reposo.",
    grantCliBanner:
      "Otorga el permiso de CLI de IA local para inspeccionar y elegir los CLIs locales.",
    grantLanBanner:
      "Otorga el permiso de Modelo integrado para descubrir y conectar endpoints locales.",
    grantApiBanner:
      "Otorga el permiso de API directa para configurar llaves y modelos del proveedor.",
    localClisBadge: "CLIs locales",
    lanEndpointBadge: "Endpoint integrado",
    apiClientBadge: "Cliente API",
    grantBtnPrefix: "Autorizar",
    testConnection: "Probar conexión",
    summaryTitle: "Modo de proveedor, permisos e ID de modelo",
    permCliTitle: "Permisos y barreras de CLI de IA local",
    permLanTitle: "Permisos y barreras de Modelo integrado",
    permApiTitle: "Permisos y barreras de API directa en la nube",
    permGranted: "Permiso otorgado",
    grantPerm: "Otorgar permiso",
    cliConnLabel: "Conexión de CLI de IA local",
    lanConnLabel: "Proveedor de Modelo integrado / Local",
    apiConnLabel: "Proveedor API en la nube",
    lanUrlLabel: "URL base de inferencia LAN",
    apiKeyLabel: "Llave API",
    baseUrlOptLabel: "URL base (opcional)",
    exactModelLabel: "ID exacto de modelo",
    refreshModels: "Actualizar modelos",
    connectLoad: "Conectar y cargar modelos",
    providerDefault: "Predeterminado del proveedor",
    customModelOpt: "ID de modelo personalizado…",
    customModelPlaceholder: "Ingresa el ID exacto del modelo…",
    grantToConnectHint: "Otorga el permiso arriba para conectar y cargar los IDs de modelo.",
    enterKeyHint:
      "Ingresa tu llave API y haz clic en Conectar y cargar modelos para poblar la lista.",
    clickConnectHint:
      "Haz clic en Conectar y cargar modelos para obtener los IDs exactos de este proveedor.",
    attachContextTitle: "Adjuntar resumen financiero anonimizado por defecto",
    attachContextDesc:
      "Solo patrimonio neto, runway y razón de deuda — nunca números de cuenta ni correos.",
    attachContextDetail:
      "Incluye balances agregados, meses de runway y razón deuda/activos. Excluye números de cuenta, tarjetas, correos y descripciones crudas.",
    attachContextTags: ["Anonimizado", "Solo lectura", "Sin PII"],
    reportsAiTitle: "Habilitar IA en Reportes",
    reportsAiDesc:
      "Permitir análisis contextual con IA en las vistas y tarjetas de Reportes (Flujo de caja, Gastos, Deuda, Inversiones).",
    reportsAiDetail:
      "Agrega disparadores contextuales en Flujo de caja, Planificado vs Real, Gastos y Pago de deuda usando únicamente los totales visibles.",
    reportsAiTags: ["Flujo de caja", "Gastos", "Deuda", "Solo lectura"],
    duesAiTitle: "Habilitar IA en Pagos pendientes",
    duesAiDesc:
      "Permitir asistencia contextual con IA para pagos recurrentes, priorización de fechas y recordatorios.",
    duesAiDetail:
      "Permite priorizar vencimientos, detectar riesgos de mora y ubicar compromisos sin pago vinculado en Pagos pendientes sin modificar registros.",
    duesAiTags: ["Compromisos", "Vencimientos", "Solo lectura"],
    enablementsHeading: "Habilitaciones de módulos y contexto IA",
    activeLabel: "Activo",
    pausedLabel: "Desactivado",
    saveBtn: "Guardar configuración LLM",
    savingBtn: "Guardando…",
    testOkTitle: "Conexión verificada",
    testFailTitle: "Falló la conexión",
    testReplyLabel: "Respuesta del modelo",
    cliBullets: [
      "Ejecuta el binario CLI local fijado (shell=False) sin secretos de base de datos ni OAuth.",
      "Ejecuta descubrimiento de modelos (ej. agy models) y prompts de un solo turno sin herramientas de archivos o shell.",
      "Límite de solo lectura: no puede modificar PostgreSQL, registrar transacciones ni ejecutar transferencias.",
    ],
    cliRiskModalTitle: "Advertencia de seguridad: ¿Habilitar acceso a CLI de IA local?",
    cliRiskModalDesc:
      "Permitir que esta aplicación web ejecute CLIs de IA locales (agy, claude, codex, cursor) conecta tu navegador con ejecutables en tu equipo. Revisa lo que puede ocurrir antes de aceptar:",
    cliRiskItems: [
      "Ejecución bajo tu usuario del sistema: El binario CLI se ejecuta con los permisos de tu cuenta de usuario y tu sesión/credenciales locales activas.",
      "Salida de datos y consumo: Tus prompts, el contexto visible de la interfaz y cualquier resumen financiero adjunto salen del navegador hacia el proveedor de IA del CLI (Google, Anthropic, OpenAI, Cursor) y consumen tu cuota o facturación.",
      "Riesgo de inyección de prompts y plugins locales: Aunque Papita usa shell=False, lista blanca de binarios y oculta secretos de BD/OAuth, errores o plugins MCP/CLI habilitados en tu máquina podrían exponer estado local.",
      "Confianza a nivel de origen mientras esté activo: Cualquier script en este origen podrá invocar el puente CLI mientras el permiso esté otorgado. Habilítalo solo en orígenes locales/autoalojados de confianza; puedes revocarlo en cualquier momento.",
    ],
    cliRiskAckLabel:
      "Entiendo lo que puede ocurrir y acepto los riesgos de seguridad y privacidad de permitir que esta página ejecute CLIs de IA locales.",
    cliRiskCancel: "Cancelar",
    cliRiskConfirm: "Entiendo — Permitir acceso CLI",
    lanBullets: [
      "Conecta a tu servidor de inferencia privado en LAN (OpenAI /v1 u Ollama /api) sin salida a la nube pública.",
      "Las barreras SSRF bloquean IPs de metadatos en la nube (169.254.169.254), enlaces locales y credenciales en la URL.",
      "Límite de solo lectura: recibe solo métricas financieras agregadas sin PII; no puede alterar el libro contable.",
    ],
    apiBullets: [
      "Almacena tu llave API cifrada con Fernet en reposo y consulta el catálogo público /models del proveedor.",
      "Las barreras SSRF restringen los endpoints API a hosts HTTPS públicos (IPs privadas/LAN rechazadas).",
      "Límite de solo lectura: envía solo tu prompt y el resumen financiero anonimizado opcional (nunca números de cuenta ni correos).",
    ],
  },
} as const;

type AICopy = (typeof AI_COPY)[keyof typeof AI_COPY];

const CUSTOM_MODEL_VALUE = "__custom__";

const CLI_PROVIDERS = [
  { id: "cli:agy", label: "Antigravity CLI (agy)", hint: "Headless local agy chat via sidecar" },
  {
    id: "cli:claude",
    label: "Claude Code CLI (claude)",
    hint: "Headless Claude Code (-p, tools off)",
  },
  {
    id: "cli:codex",
    label: "OpenAI Codex / GPT CLI (codex)",
    hint: "Headless Codex exec via sidecar",
  },
  { id: "cli:cursor", label: "Cursor Agent CLI (cursor)", hint: "Headless Cursor agent --print" },
] as const;

const LAN_PROVIDERS = [
  {
    id: "qwen_finance",
    label: "Built-in Financial Model",
    defaultModel: "qwen-finance-lora",
    defaultUrl: "",
  },
  {
    id: "ollama",
    label: "Local / LAN Ollama",
    defaultModel: "llama3.2",
    defaultUrl: "http://host.docker.internal:11434",
  },
  {
    id: "openai_compat",
    label: "LAN OpenAI-Compatible (vLLM / LM Studio / llama.cpp)",
    defaultModel: "local-model",
    defaultUrl: "http://host.docker.internal:1234/v1",
  },
] as const;

const API_PROVIDERS = [
  {
    id: "openai",
    label: "OpenAI (GPT-4o / o3)",
    defaultModel: "gpt-4o-mini",
    defaultUrl: "https://api.openai.com/v1",
  },
  {
    id: "anthropic",
    label: "Anthropic (Claude)",
    defaultModel: "claude-sonnet-4-20250514",
    defaultUrl: "https://api.anthropic.com",
  },
  {
    id: "gemini",
    label: "Google Gemini",
    defaultModel: "gemini-2.5-flash",
    defaultUrl: "https://generativelanguage.googleapis.com",
  },
] as const;

export type AISettingsPanelProps = {
  /** When true, hides the duplicate obsidian hero header and delegates Save to the parent Settings header. */
  embedded?: boolean;
  /** Incremented by the parent Settings header Save button to trigger saving LLM settings. */
  saveSignal?: number;
  /** Layout variant for Impeccable Live Mode comparison. */
  variantLayout?: "original" | "unified-1" | "unified-2";
};

export function AISettingsPanel({
  embedded = false,
  saveSignal = 0,
  variantLayout = "original",
}: AISettingsPanelProps) {
  const { locale } = useLocale();
  const lang = LOCALE_TO_LANGUAGE[locale];
  const queryClient = useQueryClient();
  const statusQuery = useQuery({
    queryKey: ["ai-status"],
    queryFn: ({ signal }) => getAIStatus(signal),
  });
  const configQuery = useQuery({
    queryKey: ["ai-config"],
    queryFn: ({ signal }) => getAIConfig(signal),
  });
  const bridgeQuery = useQuery({
    queryKey: ["cli-bridge-status"],
    queryFn: () => detectCliBridge(),
    staleTime: 10_000,
  });

  const [modeOverride, setModeOverride] = useState<AIMode | null>(null);
  const [connOverride, setConnOverride] = useState<string | null>(null);
  const [modelOverride, setModelOverride] = useState<string | null>(null);
  const [baseUrlOverride, setBaseUrlOverride] = useState<string | null>(null);
  const [includeContextOverride, setIncludeContextOverride] = useState<boolean | null>(null);
  const [reportsAiOverride, setReportsAiOverride] = useState<boolean | null>(null);
  const [paymentDuesAiOverride, setPaymentDuesAiOverride] = useState<boolean | null>(null);
  const [cliPermOverride, setCliPermOverride] = useState<boolean | null>(null);
  const [lanPermOverride, setLanPermOverride] = useState<boolean | null>(null);
  const [apiPermOverride, setApiPermOverride] = useState<boolean | null>(null);
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [useCustomModel, setUseCustomModel] = useState(false);
  const [testReply, setTestReply] = useState<{
    ok: boolean;
    provider: string;
    model: string | null;
    reply: string;
  } | null>(null);

  const [connectedForKey, setConnectedForKey] = useState<string | null>(null);
  const [discoveredModels, setDiscoveredModels] = useState<AIModelOption[]>([]);
  const [modelSource, setModelSource] = useState<"live" | "curated" | null>(null);
  const [connectError, setConnectError] = useState<string | null>(null);
  const [cliRiskModalOpen, setCliRiskModalOpen] = useState(false);
  const [cliRiskAccepted, setCliRiskAccepted] = useState(false);
  const [cliRiskConfirming, setCliRiskConfirming] = useState(false);
  const lastSaveSignalRef = useRef(saveSignal);
  const autoLoadedKeyRef = useRef<string | null>(null);

  const cfg = configQuery.data;
  const status = statusQuery.data;
  const bridge = bridgeQuery.data;

  const mode: AIMode = modeOverride ?? cfg?.mode ?? "sidecar";
  const defaultConnection = connOverride ?? cfg?.default_connection ?? "cli:agy";
  const model = modelOverride ?? cfg?.model ?? "";
  const baseUrl = baseUrlOverride ?? cfg?.base_url ?? "";
  const includeContext =
    includeContextOverride ?? cfg?.include_financial_context_by_default ?? true;
  const reportsAiEnabled = reportsAiOverride ?? cfg?.reports_ai_enabled ?? true;
  const paymentDuesAiEnabled = paymentDuesAiOverride ?? cfg?.payment_dues_ai_enabled ?? true;
  const useBrowserCliBridge =
    mode === "sidecar" && Boolean(bridge?.installed && bridge.nativeHostReady);
  const cliPermissionGranted =
    cliPermOverride ??
    (bridge?.installed ? Boolean(bridge.originGranted) : (cfg?.cli_permission_granted ?? false));
  const lanPermissionGranted = lanPermOverride ?? cfg?.lan_permission_granted ?? false;
  const apiPermissionGranted = apiPermOverride ?? cfg?.api_permission_granted ?? false;
  const cliConnections =
    useBrowserCliBridge && bridge && bridge.clis.length > 0
      ? bridge.clis
      : (status?.connections ?? []).filter((conn) => conn.kind === "cli");

  const activePermissionGranted =
    mode === "sidecar"
      ? cliPermissionGranted
      : mode === "lan_local"
        ? lanPermissionGranted
        : apiPermissionGranted;
  const connectionKey = `${mode}:${defaultConnection}`;
  const isConnected = connectedForKey === connectionKey;

  const connectMutation = useMutation({
    retry: 1,
    retryDelay: 800,
    mutationFn: async () => {
      if (useBrowserCliBridge) {
        if (!bridge?.originGranted) {
          const decision = await requestCliBridgePermission(defaultConnection);
          void queryClient.invalidateQueries({ queryKey: ["cli-bridge-status"] });
          if (!decision.granted) {
            throw new Error(decision.error || "Browser CLI permission was denied.");
          }
          setCliPermOverride(true);
        }
        return bridgeListModels(defaultConnection);
      }
      return fetchAIModels({
        mode,
        connection: defaultConnection,
        base_url: mode === "sidecar" ? null : baseUrl.trim() || null,
        api_key: mode === "sidecar" ? null : apiKeyInput.trim() || null,
      });
    },
    onSuccess: (res) => {
      if (!res.ready) {
        setConnectedForKey(null);
        setDiscoveredModels([]);
        setModelSource(null);
        setConnectError(
          mode === "sidecar"
            ? `${res.connection} is not ready in the local sidecar. Verify the binary or Ollama service is running.`
            : `Could not verify ${res.connection} connection.`,
        );
        return;
      }
      setConnectError(null);
      setConnectedForKey(`${res.mode}:${res.connection}`);
      setDiscoveredModels(res.models);
      setModelSource(res.source);
      setUseCustomModel(false);
      if (res.models.length > 0 && !res.models.some((m) => m.id === model)) {
        setModelOverride(res.default_model ?? res.models[0]?.id ?? "");
      }
      toast.success(
        `Connected to ${res.connection} (${String(res.models.length)} model${res.models.length === 1 ? "" : "s"} available).`,
      );
    },
    onError: (err) => {
      const msg = formatApiError(err, "Could not connect and fetch model IDs.");
      setConnectError(msg);
      setConnectedForKey(null);
      toast.error(msg);
    },
  });

  const { mutate: triggerConnect } = connectMutation;
  const savedPermissionGranted =
    mode === "sidecar"
      ? Boolean(cfg?.cli_permission_granted)
      : mode === "lan_local"
        ? Boolean(cfg?.lan_permission_granted)
        : Boolean(cfg?.api_permission_granted);

  // Automatically load model IDs once when a previously saved & permitted configuration hydrates.
  useEffect(() => {
    if (!cfg || !savedPermissionGranted || !activePermissionGranted) return;
    if (mode === "api_key" && !cfg.has_api_key) return;
    if (autoLoadedKeyRef.current === connectionKey) return;
    autoLoadedKeyRef.current = connectionKey;
    triggerConnect();
  }, [activePermissionGranted, cfg, connectionKey, mode, savedPermissionGranted, triggerConnect]);

  const saveMutation = useMutation({
    mutationFn: (opts?: { clearKey?: boolean }) =>
      updateAIConfig({
        enabled: true,
        mode,
        default_connection: defaultConnection,
        model: model.trim() || null,
        base_url: baseUrl.trim() || null,
        include_financial_context_by_default: includeContext,
        reports_ai_enabled: reportsAiEnabled,
        payment_dues_ai_enabled: paymentDuesAiEnabled,
        cli_permission_granted: cliPermissionGranted,
        lan_permission_granted: lanPermissionGranted,
        api_permission_granted: apiPermissionGranted,
        api_key: opts?.clearKey ? null : apiKeyInput.trim() || null,
        clear_api_key: Boolean(opts?.clearKey),
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["ai-config"], updated);
      void queryClient.invalidateQueries({ queryKey: ["ai-status"] });
      setApiKeyInput("");
      toast.success("AI & LLM configuration saved.");
    },
    onError: (err) => {
      toast.error(formatApiError(err, "Could not save AI configuration."));
    },
  });

  const testMutation = useMutation({
    mutationFn: async () => {
      const prompt = "Reply with OK and your provider/model name in one short sentence.";
      if (useBrowserCliBridge) {
        if (!bridge?.originGranted) {
          const decision = await requestCliBridgePermission(defaultConnection);
          void queryClient.invalidateQueries({ queryKey: ["cli-bridge-status"] });
          if (!decision.granted) {
            throw new Error(decision.error || "Browser CLI permission was denied.");
          }
          setCliPermOverride(true);
        }
        return bridgeChat({
          connection: defaultConnection,
          model: model.trim() || null,
          userPrompt: prompt,
        });
      }
      return sendAIChat({
        prompt,
        connection: defaultConnection,
        include_financial_context: false,
      });
    },
    onSuccess: (res) => {
      setTestReply({
        ok: true,
        provider: res.provider,
        model: res.model ?? null,
        reply: res.reply,
      });
      toast.success("LLM connection responded cleanly.");
    },
    onError: (err) => {
      const msg = formatApiError(err, "LLM connection test failed.");
      setTestReply({ ok: false, provider: defaultConnection, model: null, reply: msg });
      toast.error(msg);
    },
  });

  const { mutate: triggerSave, isPending: isSaving } = saveMutation;

  useEffect(() => {
    if (saveSignal === lastSaveSignalRef.current) {
      return;
    }
    lastSaveSignalRef.current = saveSignal;
    if (!isSaving) {
      triggerSave({});
    }
  }, [isSaving, saveSignal, triggerSave]);

  const canConnect =
    activePermissionGranted &&
    !connectMutation.isPending &&
    (mode === "sidecar" ||
      mode === "lan_local" ||
      Boolean(apiKeyInput.trim()) ||
      Boolean(cfg?.has_api_key));

  const modelDropdownValue =
    useCustomModel ||
    (model && discoveredModels.length > 0 && !discoveredModels.some((m) => m.id === model))
      ? CUSTOM_MODEL_VALUE
      : model;

  const isUnified = variantLayout === "unified-1" || variantLayout === "unified-2";

  const renderModeCards = (t: AICopy) => (
    <div className="papita-ai-modes grid gap-3 md:grid-cols-3">
      <button
        type="button"
        onClick={() => {
          setModeOverride("sidecar");
          setConnectError(null);
          if (!CLI_PROVIDERS.some((p) => p.id === defaultConnection)) {
            setConnOverride("cli:agy");
            setModelOverride("");
          }
        }}
        className={cn(
          "papita-ai-mode-card flex items-start gap-3 rounded-xl border p-3.5 text-left transition-colors",
          mode === "sidecar"
            ? "papita-ai-mode-active border-primary bg-primary/[0.06]"
            : "border-border hover:bg-muted/40",
        )}
      >
        <Terminal className="mt-0.5 size-4 shrink-0 text-primary" />
        <div>
          <p className="text-sm font-semibold">{t.headlessTitle}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">{t.headlessDesc}</p>
        </div>
      </button>

      <button
        type="button"
        onClick={() => {
          setModeOverride("lan_local");
          setConnectError(null);
          if (!LAN_PROVIDERS.some((p) => p.id === defaultConnection)) {
            setConnOverride("qwen_finance");
            setModelOverride("qwen-finance-lora");
            if (!baseUrl) {
              setBaseUrlOverride("");
            }
          }
        }}
        className={cn(
          "papita-ai-mode-card flex items-start gap-3 rounded-xl border p-3.5 text-left transition-colors",
          mode === "lan_local"
            ? "papita-ai-mode-active border-primary bg-primary/[0.06]"
            : "border-border hover:bg-muted/40",
        )}
      >
        <Server className="mt-0.5 size-4 shrink-0 text-primary" />
        <div>
          <p className="text-sm font-semibold">{t.lanTitle}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">{t.lanDesc}</p>
        </div>
      </button>

      <button
        type="button"
        onClick={() => {
          setModeOverride("api_key");
          setConnectError(null);
          if (!API_PROVIDERS.some((p) => p.id === defaultConnection)) {
            setConnOverride("openai");
            setModelOverride("gpt-4o-mini");
            setBaseUrlOverride("https://api.openai.com/v1");
          }
        }}
        className={cn(
          "papita-ai-mode-card flex items-start gap-3 rounded-xl border p-3.5 text-left transition-colors",
          mode === "api_key"
            ? "papita-ai-mode-active border-primary bg-primary/[0.06]"
            : "border-border hover:bg-muted/40",
        )}
      >
        <KeyRound className="mt-0.5 size-4 shrink-0 text-primary" />
        <div>
          <p className="text-sm font-semibold">{t.apiTitle}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">{t.apiDesc}</p>
        </div>
      </button>
    </div>
  );

  const renderPermissionsAndGuardrails = (t: AICopy, includeEndpoints: boolean) => {
    const bullets =
      mode === "sidecar" ? t.cliBullets : mode === "lan_local" ? t.lanBullets : t.apiBullets;

    return (
      <div
        className={cn(
          "papita-ai-perm space-y-3 rounded-xl border p-4",
          activePermissionGranted
            ? "border-emerald-500/35 bg-emerald-500/[0.05]"
            : "border-amber-500/40 bg-amber-500/[0.06]",
        )}
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-2.5">
            <ShieldCheck
              className={cn(
                "mt-0.5 size-4 shrink-0",
                activePermissionGranted
                  ? "text-emerald-600 dark:text-emerald-400"
                  : "text-amber-600 dark:text-amber-400",
              )}
            />
            <div className="space-y-1">
              <p className="text-xs font-semibold text-foreground">
                {mode === "sidecar"
                  ? t.permCliTitle
                  : mode === "lan_local"
                    ? t.permLanTitle
                    : t.permApiTitle}
              </p>
              <ul className="list-disc space-y-0.5 pl-4 text-[11px] leading-relaxed text-muted-foreground">
                {bullets.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              {mode === "sidecar" ? (
                <p className="pt-1 text-[11px] text-muted-foreground">
                  {bridge?.installed ? (
                    bridge.nativeHostReady ? (
                      <span className="font-medium text-emerald-700 dark:text-emerald-300">
                        Browser CLI Bridge active — permission prompt runs in the extension &amp;
                        executes CLIs directly on your machine.
                      </span>
                    ) : (
                      <span className="font-medium text-amber-700 dark:text-amber-300">
                        Browser CLI Bridge extension detected, but native host is not registered.
                        Run{" "}
                        <code>
                          modules/browser-cli-bridge/native-host/install_native_host.sh
                          &lt;EXT_ID&gt;
                        </code>
                        .
                      </span>
                    )
                  ) : (
                    <span>
                      For direct browser-to-CLI execution, load{" "}
                      <code>modules/browser-cli-bridge/extension/</code> in your browser (otherwise
                      falls back to the local sidecar).
                    </span>
                  )}
                </p>
              ) : null}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-medium">
              <input
                type="checkbox"
                checked={activePermissionGranted}
                onChange={(event) => {
                  const granted = event.target.checked;
                  if (mode === "sidecar") {
                    if (granted) {
                      setCliRiskAccepted(false);
                      setCliRiskModalOpen(true);
                      return;
                    }
                    if (bridge?.installed) {
                      void revokeCliBridgePermission().then(() => {
                        void queryClient.invalidateQueries({ queryKey: ["cli-bridge-status"] });
                      });
                    }
                    setCliPermOverride(false);
                  } else if (mode === "lan_local") {
                    setLanPermOverride(granted);
                  } else {
                    setApiPermOverride(granted);
                  }
                  if (!granted) {
                    setConnectedForKey(null);
                    setDiscoveredModels([]);
                  }
                }}
                className="size-4 accent-emerald-600"
              />
              <span>{activePermissionGranted ? t.permGranted : t.grantPerm}</span>
            </label>
          </div>
        </div>

        {includeEndpoints && activePermissionGranted ? (
          <div className="flex flex-wrap items-center gap-2 border-t border-border/60 pt-2.5">
            {mode === "sidecar" ? (
              <>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-2.5 py-1 font-medium text-emerald-700 dark:text-emerald-300">
                  <CheckCircle2 className="size-3.5" />
                  {useBrowserCliBridge ? "Browser CLI Bridge" : t.localClisBadge}
                </span>
                {cliConnections.map((conn) => (
                  <button
                    key={conn.id}
                    type="button"
                    onClick={() => setConnOverride(conn.id)}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-medium transition-colors",
                      defaultConnection === conn.id
                        ? "bg-primary/15 text-foreground ring-1 ring-primary/40"
                        : "bg-muted/80 text-muted-foreground hover:text-foreground",
                    )}
                  >
                    <Terminal className="size-3" />
                    <span>{conn.id}</span>
                    <span
                      className={cn(
                        "size-1.5 rounded-full",
                        conn.ready ? "bg-emerald-500" : "bg-muted-foreground/50",
                      )}
                    />
                  </button>
                ))}
              </>
            ) : (
              <>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-2.5 py-1 font-medium text-emerald-700 dark:text-emerald-300">
                  <CheckCircle2 className="size-3.5" />
                  {mode === "lan_local" ? t.lanEndpointBadge : t.apiClientBadge}
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-1 font-medium text-foreground">
                  {mode === "lan_local" ? (
                    <Server className="size-3" />
                  ) : (
                    <KeyRound className="size-3" />
                  )}
                  <span>
                    {defaultConnection}
                    {baseUrl && mode === "lan_local" ? ` · ${baseUrl}` : ""}
                    {model ? ` · ${model}` : ""}
                  </span>
                </span>
              </>
            )}
          </div>
        ) : null}
      </div>
    );
  };

  const renderCfgBody = (
    t: AICopy,
    enablementsStyle: "original" | "rows-cards" | "rows-divided" | "rows-detailed" = "original",
  ) => (
    <>
      {/* 1. Integration Mode (omitted inside details when unified header owns it) */}
      {isUnified ? null : renderModeCards(t)}

      {/* 2. Required Integration Permissions & Guardrails (omitted inside details when unified header owns it) */}
      {isUnified ? null : renderPermissionsAndGuardrails(t, false)}

      {/* 3. Provider + Credentials / LAN Endpoint + Connect */}
      <div className="papita-ai-fields grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="ai-provider-select">
            {mode === "sidecar"
              ? t.cliConnLabel
              : mode === "lan_local"
                ? t.lanConnLabel
                : t.apiConnLabel}
          </Label>
          <div className="flex items-center gap-2">
            <NativeSelect
              id="ai-provider-select"
              value={defaultConnection}
              className="flex-1"
              onChange={(event) => {
                const next = event.target.value;
                setConnOverride(next);
                setConnectedForKey(null);
                setDiscoveredModels([]);
                setConnectError(null);
                setUseCustomModel(false);
                const lanPreset = LAN_PROVIDERS.find((p) => p.id === next);
                const apiPreset = API_PROVIDERS.find((p) => p.id === next);
                if (lanPreset) {
                  setModelOverride(lanPreset.defaultModel);
                  setBaseUrlOverride(lanPreset.defaultUrl);
                } else if (apiPreset) {
                  setModelOverride(apiPreset.defaultModel);
                  setBaseUrlOverride(apiPreset.defaultUrl);
                } else {
                  setModelOverride("");
                }
              }}
            >
              {(mode === "sidecar"
                ? CLI_PROVIDERS
                : mode === "lan_local"
                  ? LAN_PROVIDERS
                  : API_PROVIDERS
              ).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </NativeSelect>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="shrink-0"
              disabled={testMutation.isPending || !activePermissionGranted}
              onClick={() => testMutation.mutate()}
            >
              {testMutation.isPending ? (
                <Loader2 className="mr-1.5 size-3.5 animate-spin" />
              ) : (
                <Sparkles className="mr-1.5 size-3.5 text-emerald-600 dark:text-emerald-400" />
              )}
              {t.testConnection}
            </Button>
          </div>
        </div>

        {mode === "lan_local" ? (
          <div className="space-y-1.5">
            <Label htmlFor="ai-lan-url-input">{t.lanUrlLabel}</Label>
            <Input
              id="ai-lan-url-input"
              placeholder="http://localhost:11434 (optional if configured on server)"
              value={baseUrl}
              onChange={(event) => setBaseUrlOverride(event.target.value)}
            />
          </div>
        ) : null}

        {mode === "api_key" ? (
          <>
            <div className="space-y-1.5">
              <Label htmlFor="ai-apikey-input">
                {t.apiKeyLabel}{" "}
                {cfg?.has_api_key ? `(stored: ${cfg.api_key_hint ?? "encrypted"})` : ""}
              </Label>
              <div className="flex gap-2">
                <Input
                  id="ai-apikey-input"
                  type="password"
                  autoComplete="off"
                  placeholder={
                    cfg?.has_api_key ? "Leave blank to keep stored key" : "Paste provider API key…"
                  }
                  value={apiKeyInput}
                  onChange={(event) => setApiKeyInput(event.target.value)}
                />
                {cfg?.has_api_key ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={saveMutation.isPending}
                    onClick={() => saveMutation.mutate({ clearKey: true })}
                    title="Revoke stored API key"
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                ) : null}
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="ai-baseurl-input">{t.baseUrlOptLabel}</Label>
              <Input
                id="ai-baseurl-input"
                placeholder="https://api.openai.com/v1"
                value={baseUrl}
                onChange={(event) => setBaseUrlOverride(event.target.value)}
              />
            </div>
          </>
        ) : null}

        {/* Connect button + Exact Model ID dropdown */}
        <div className={cn("space-y-1.5", mode === "sidecar" ? "" : "sm:col-span-2")}>
          <div className="flex items-center justify-between gap-2">
            <Label htmlFor="ai-model-select">{t.exactModelLabel}</Label>
            <div className="flex items-center gap-1.5">
              {isConnected ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/12 px-2 py-0.5 text-[11px] font-medium text-emerald-700 dark:text-emerald-300">
                  <CheckCircle2 className="size-3" />
                  Connected · {String(discoveredModels.length)}{" "}
                  {modelSource === "live" ? "live" : "available"}
                </span>
              ) : null}
              <Button
                type="button"
                size="sm"
                variant={isConnected ? "outline" : "default"}
                disabled={!canConnect}
                onClick={() => connectMutation.mutate()}
                className="h-7 gap-1.5 px-2.5 text-xs"
              >
                {connectMutation.isPending ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : isConnected ? (
                  <RefreshCw className="size-3.5" />
                ) : (
                  <Plug className="size-3.5" />
                )}
                {isConnected ? t.refreshModels : t.connectLoad}
              </Button>
            </div>
          </div>

          {isConnected && discoveredModels.length > 0 ? (
            <div className="space-y-2">
              <NativeSelect
                id="ai-model-select"
                aria-label="Exact Model ID"
                value={modelDropdownValue}
                onChange={(event) => {
                  const nextVal = event.target.value;
                  if (nextVal === CUSTOM_MODEL_VALUE) {
                    setUseCustomModel(true);
                  } else {
                    setUseCustomModel(false);
                    setModelOverride(nextVal);
                  }
                }}
              >
                <option value="">{t.providerDefault}</option>
                {discoveredModels.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label !== item.id ? `${item.label} — ${item.id}` : item.id}
                  </option>
                ))}
                <option value={CUSTOM_MODEL_VALUE}>{t.customModelOpt}</option>
              </NativeSelect>

              {modelDropdownValue === CUSTOM_MODEL_VALUE ? (
                <Input
                  id="ai-model-custom-input"
                  placeholder={t.customModelPlaceholder}
                  value={model}
                  onChange={(event) => setModelOverride(event.target.value)}
                />
              ) : null}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-border bg-muted/25 px-3 py-2 text-xs text-muted-foreground">
              {!activePermissionGranted
                ? t.grantToConnectHint
                : mode === "api_key" && !apiKeyInput.trim() && !cfg?.has_api_key
                  ? t.enterKeyHint
                  : t.clickConnectHint}
            </div>
          )}

          {connectError ? (
            <p role="alert" className="text-xs text-destructive">
              {connectError}
            </p>
          ) : null}
        </div>
      </div>

      {enablementsStyle === "original" ? (
        <>
          <div
            className={cn(
              "flex items-center justify-between gap-3 rounded-xl border px-3.5 py-3 text-sm transition-colors",
              includeContext
                ? "border-emerald-500/35 bg-emerald-500/8"
                : "border-border bg-muted/25 hover:bg-muted/40",
            )}
          >
            <label htmlFor="ai-include-context-checkbox" className="cursor-pointer">
              <span className="block text-xs font-semibold">{t.attachContextTitle}</span>
              <span className="block text-[11px] text-muted-foreground">{t.attachContextDesc}</span>
            </label>
            <input
              id="ai-include-context-checkbox"
              type="checkbox"
              checked={includeContext}
              onChange={(event) => setIncludeContextOverride(event.target.checked)}
              className="size-4 shrink-0 cursor-pointer accent-emerald-600"
            />
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div
              className={cn(
                "flex items-center justify-between gap-3 rounded-xl border px-3.5 py-3 text-sm transition-colors",
                reportsAiEnabled
                  ? "border-emerald-500/35 bg-emerald-500/8"
                  : "border-border bg-muted/25 hover:bg-muted/40",
              )}
            >
              <label htmlFor="ai-reports-enabled-checkbox" className="cursor-pointer">
                <span className="block text-xs font-semibold">{t.reportsAiTitle}</span>
                <span className="block text-[11px] text-muted-foreground">{t.reportsAiDesc}</span>
              </label>
              <input
                id="ai-reports-enabled-checkbox"
                type="checkbox"
                checked={reportsAiEnabled}
                onChange={(event) => setReportsAiOverride(event.target.checked)}
                className="size-4 shrink-0 cursor-pointer accent-emerald-600"
              />
            </div>

            <div
              className={cn(
                "flex items-center justify-between gap-3 rounded-xl border px-3.5 py-3 text-sm transition-colors",
                paymentDuesAiEnabled
                  ? "border-emerald-500/35 bg-emerald-500/8"
                  : "border-border bg-muted/25 hover:bg-muted/40",
              )}
            >
              <label htmlFor="ai-dues-enabled-checkbox" className="cursor-pointer">
                <span className="block text-xs font-semibold">{t.duesAiTitle}</span>
                <span className="block text-[11px] text-muted-foreground">{t.duesAiDesc}</span>
              </label>
              <input
                id="ai-dues-enabled-checkbox"
                type="checkbox"
                checked={paymentDuesAiEnabled}
                onChange={(event) => setPaymentDuesAiOverride(event.target.checked)}
                className="size-4 shrink-0 cursor-pointer accent-emerald-600"
              />
            </div>
          </div>
        </>
      ) : (
        (() => {
          const rows = [
            {
              id: "ai-include-context-toggle",
              title: t.attachContextTitle,
              desc: t.attachContextDesc,
              detail: t.attachContextDetail,
              tags: t.attachContextTags,
              checked: includeContext,
              onToggle: () => setIncludeContextOverride(!includeContext),
            },
            {
              id: "ai-reports-enabled-toggle",
              title: t.reportsAiTitle,
              desc: t.reportsAiDesc,
              detail: t.reportsAiDetail,
              tags: t.reportsAiTags,
              checked: reportsAiEnabled,
              onToggle: () => setReportsAiOverride(!reportsAiEnabled),
            },
            {
              id: "ai-dues-enabled-toggle",
              title: t.duesAiTitle,
              desc: t.duesAiDesc,
              detail: t.duesAiDetail,
              tags: t.duesAiTags,
              checked: paymentDuesAiEnabled,
              onToggle: () => setPaymentDuesAiOverride(!paymentDuesAiEnabled),
            },
          ];

          const renderSwitch = (row: (typeof rows)[number]) => (
            <button
              id={row.id}
              type="button"
              role="switch"
              aria-checked={row.checked}
              aria-label={row.title}
              onClick={row.onToggle}
              className={cn(
                "relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                row.checked ? "bg-emerald-600 dark:bg-emerald-500" : "bg-muted-foreground/30",
              )}
            >
              <span
                aria-hidden="true"
                className={cn(
                  "pointer-events-none block size-5 rounded-full bg-white shadow-sm transition-transform",
                  row.checked ? "translate-x-5" : "translate-x-0",
                )}
              />
            </button>
          );

          if (enablementsStyle === "rows-divided") {
            return (
              <div className="papita-ai-enab-list overflow-hidden rounded-xl border border-border bg-background/60">
                <div className="border-b border-border bg-muted/35 px-4 py-2 text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">
                  {t.enablementsHeading}
                </div>
                <div className="divide-y divide-border">
                  {rows.map((row) => (
                    <div
                      key={row.id}
                      className="papita-ai-enab-row flex items-start justify-between gap-4 px-4 py-3.5 transition-colors hover:bg-muted/25"
                    >
                      <div className="min-w-0 space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-xs font-semibold text-foreground">{row.title}</span>
                          <span
                            className={cn(
                              "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium",
                              row.checked
                                ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                                : "bg-muted text-muted-foreground",
                            )}
                          >
                            {row.checked ? t.activeLabel : t.pausedLabel}
                          </span>
                        </div>
                        <p className="text-[11px] font-medium text-foreground/80">{row.desc}</p>
                        <p className="text-[11px] leading-relaxed text-muted-foreground">
                          {row.detail}
                        </p>
                      </div>
                      <div className="pt-0.5">{renderSwitch(row)}</div>
                    </div>
                  ))}
                </div>
              </div>
            );
          }

          if (enablementsStyle === "rows-detailed") {
            return (
              <div className="space-y-2.5">
                {rows.map((row) => (
                  <div
                    key={row.id}
                    className={cn(
                      "papita-ai-enab-accent flex items-start justify-between gap-4 rounded-xl border border-l-4 px-4 py-3.5 transition-colors",
                      row.checked
                        ? "border-border border-l-emerald-500 bg-emerald-500/[0.04]"
                        : "border-border border-l-muted-foreground/30 bg-muted/20",
                    )}
                  >
                    <div className="min-w-0 space-y-1.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-semibold text-foreground">{row.title}</span>
                        {row.tags.map((tag) => (
                          <span
                            key={tag}
                            className="rounded-md bg-background/80 px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground ring-1 ring-border/70"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                      <p className="text-[11px] leading-relaxed text-muted-foreground">
                        {row.detail}
                      </p>
                    </div>
                    <div className="pt-0.5">{renderSwitch(row)}</div>
                  </div>
                ))}
              </div>
            );
          }

          return (
            <div className="space-y-2.5">
              {rows.map((row) => (
                <div
                  key={row.id}
                  className={cn(
                    "papita-ai-enab-card flex items-start justify-between gap-4 rounded-xl border px-4 py-3.5 transition-colors",
                    row.checked
                      ? "border-emerald-500/35 bg-emerald-500/[0.06]"
                      : "border-border bg-muted/20 hover:bg-muted/35",
                  )}
                >
                  <div className="min-w-0 space-y-1.5">
                    <span className="block text-xs font-semibold text-foreground">{row.title}</span>
                    <p className="text-[11px] leading-relaxed text-muted-foreground">
                      {row.detail}
                    </p>
                    <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                      {row.tags.map((tag) => (
                        <span
                          key={tag}
                          className="rounded-full bg-background/90 px-2 py-0.5 text-[10px] font-medium text-muted-foreground border border-border/70"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="pt-0.5">{renderSwitch(row)}</div>
                </div>
              ))}
            </div>
          );
        })()
      )}

      {testReply ? (
        <div
          className={cn(
            "flex items-start gap-2.5 rounded-xl border px-3.5 py-2.5 text-xs leading-relaxed",
            testReply.ok
              ? "border-emerald-500/35 bg-emerald-500/[0.06] text-foreground"
              : "border-destructive/40 bg-destructive/[0.06] text-destructive",
          )}
        >
          {testReply.ok ? (
            <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
          ) : (
            <XCircle className="mt-0.5 size-4 shrink-0 text-destructive" />
          )}
          <div className="min-w-0 space-y-0.5">
            <p className="font-semibold">
              {testReply.ok ? t.testOkTitle : t.testFailTitle} · {testReply.provider}
              {testReply.model ? ` (${testReply.model})` : ""}
            </p>
            <p className="text-muted-foreground">
              {t.testReplyLabel}: {testReply.reply}
            </p>
          </div>
        </div>
      ) : null}
    </>
  );

  const renderPanel = (t: AICopy, extraClass?: string) => (
    <div className={cn("flex flex-col gap-7", extraClass)}>
      {embedded ? (
        isUnified ? (
          <div
            className={cn(
              "space-y-4 rounded-2xl border border-border bg-card text-xs",
              variantLayout === "unified-1" ? "p-5" : "p-4",
            )}
          >
            {renderModeCards(t)}

            {renderPermissionsAndGuardrails(t, true)}
          </div>
        ) : (
          <div className="papita-ai-bar rounded-2xl border border-border bg-card text-xs">
            <div className="flex flex-wrap items-center gap-2.5">
              <div className="papita-ai-seg" role="group" aria-label="AI transport mode">
                {(
                  [
                    { id: "sidecar", label: "CLI" },
                    { id: "lan_local", label: "LAN" },
                    { id: "api_key", label: "API" },
                  ] as const
                ).map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => {
                      setModeOverride(item.id);
                      setConnectError(null);
                      if (
                        item.id === "sidecar" &&
                        !CLI_PROVIDERS.some((p) => p.id === defaultConnection)
                      ) {
                        setConnOverride("cli:agy");
                        setModelOverride("");
                      } else if (
                        item.id === "lan_local" &&
                        !LAN_PROVIDERS.some((p) => p.id === defaultConnection)
                      ) {
                        setConnOverride("qwen_finance");
                        setBaseUrlOverride(LAN_PROVIDERS[0].defaultUrl);
                        setModelOverride(LAN_PROVIDERS[0].defaultModel);
                      } else if (
                        item.id === "api_key" &&
                        !API_PROVIDERS.some((p) => p.id === defaultConnection)
                      ) {
                        setConnOverride("openai");
                        setBaseUrlOverride(API_PROVIDERS[0].defaultUrl);
                        setModelOverride(API_PROVIDERS[0].defaultModel);
                      }
                    }}
                    className={cn(
                      "rounded-md px-2.5 py-1 font-medium transition-colors",
                      mode === item.id
                        ? "bg-background text-foreground shadow-xs"
                        : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {item.label}
                  </button>
                ))}
              </div>

              {mode === "sidecar" ? (
                (status?.connections ?? [])
                  .filter((conn) => conn.kind === "cli")
                  .map((conn) => (
                    <button
                      key={conn.id}
                      type="button"
                      onClick={() => setConnOverride(conn.id)}
                      className={cn(
                        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-medium transition-colors",
                        defaultConnection === conn.id
                          ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                          : "bg-muted/70 text-muted-foreground hover:text-foreground",
                      )}
                    >
                      <Terminal className="size-3" />
                      <span>{conn.id}</span>
                      <span
                        className={cn(
                          "size-1.5 rounded-full",
                          conn.ready ? "bg-emerald-500" : "bg-muted-foreground/50",
                        )}
                      />
                    </button>
                  ))
              ) : (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-1 font-medium text-foreground">
                  {mode === "lan_local" ? (
                    <Server className="size-3" />
                  ) : (
                    <KeyRound className="size-3" />
                  )}
                  <span>
                    {defaultConnection}
                    {model ? ` · ${model}` : ""}
                  </span>
                </span>
              )}
            </div>

            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={testMutation.isPending || !activePermissionGranted}
              onClick={() => testMutation.mutate()}
            >
              {testMutation.isPending ? (
                <Loader2 className="mr-1.5 size-3.5 animate-spin" />
              ) : (
                <Sparkles className="mr-1.5 size-3.5 text-emerald-600 dark:text-emerald-400" />
              )}
              {t.testConnection}
            </Button>
          </div>
        )
      ) : (
        <header className="relative overflow-hidden rounded-2xl bg-[#04090c] p-6 text-white">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -top-24 -right-20 size-72 rounded-full bg-emerald-500/18 blur-3xl"
          />
          <div className="relative grid gap-5 lg:grid-cols-[1fr_272px] lg:items-center">
            <div className="space-y-4">
              <div className="max-w-2xl space-y-2">
                <h2 className="text-2xl font-semibold tracking-tight text-white">
                  AI &amp; LLM Integration
                </h2>
                <p className="text-sm leading-relaxed text-slate-300">
                  Authorize local headless CLIs (agy, claude, codex, cursor), local Ollama, or
                  encrypted API keys (GPT, Claude, Gemini) and select exact model IDs.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-full px-3 py-1 font-medium",
                    status?.available
                      ? "bg-emerald-500/20 text-emerald-300"
                      : "bg-amber-500/20 text-amber-200",
                  )}
                >
                  {status?.available ? (
                    <CheckCircle2 className="size-3.5" />
                  ) : (
                    <XCircle className="size-3.5" />
                  )}
                  {status?.available
                    ? `Ready · ${status.default_connection ?? status.provider ?? "connected"}`
                    : status?.enabled
                      ? "Configured (no ready adapter)"
                      : "Sidecar disabled in env"}
                </span>
                {(status?.connections ?? []).map((conn) => (
                  <span
                    key={conn.id}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full px-3 py-1 font-medium",
                      conn.ready ? "bg-white/10 text-slate-100" : "bg-white/[0.05] text-slate-400",
                    )}
                  >
                    {conn.kind === "cli" ? (
                      <Terminal className="size-3" />
                    ) : (
                      <KeyRound className="size-3" />
                    )}
                    <span>{conn.id}</span>
                    <span
                      className={cn(
                        "size-1.5 rounded-full",
                        conn.ready ? "bg-emerald-400" : "bg-slate-500",
                      )}
                    />
                  </span>
                ))}
              </div>
            </div>

            <div className="flex flex-col gap-2.5 rounded-xl border border-white/10 bg-white/[0.05] p-4">
              <Button
                type="button"
                disabled={saveMutation.isPending}
                onClick={() => saveMutation.mutate({})}
                className="w-full bg-emerald-500 text-slate-950 hover:bg-emerald-400"
              >
                <Save className="mr-1.5 size-4" />
                {saveMutation.isPending ? t.savingBtn : t.saveBtn}
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={testMutation.isPending || !activePermissionGranted}
                onClick={() => testMutation.mutate()}
                className="w-full border-white/15 bg-white/[0.06] text-white hover:bg-white/12 hover:text-white"
              >
                {testMutation.isPending ? (
                  <Loader2 className="mr-1.5 size-4 animate-spin" />
                ) : (
                  <Sparkles className="mr-1.5 size-4 text-emerald-400" />
                )}
                {t.testConnection}
              </Button>
            </div>
          </div>
        </header>
      )}

      <details open className="group space-y-3">
        <summary className="flex cursor-pointer list-none items-center justify-between rounded-xl border border-border bg-muted/35 px-4 py-2.5 text-xs font-semibold text-foreground transition-colors hover:bg-muted/60 [&::-webkit-details-marker]:hidden">
          <span className="inline-flex items-center gap-2">
            <Sparkles
              aria-hidden="true"
              className="size-3.5 text-emerald-600 dark:text-emerald-400"
            />
            {t.summaryTitle}
            <span className="rounded-full bg-background px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
              {defaultConnection}
              {model ? ` · ${model}` : ""}
            </span>
          </span>
          <ChevronDown
            aria-hidden="true"
            className="size-4 text-muted-foreground transition-transform duration-200 group-open:rotate-180"
          />
        </summary>

        <div className="papita-ai-cfg rounded-2xl border border-border bg-card">
          {renderCfgBody(t, "rows-divided")}
        </div>
      </details>

      <Dialog
        open={cliRiskModalOpen}
        onOpenChange={(open) => {
          if (!cliRiskConfirming) {
            setCliRiskModalOpen(open);
            if (!open) setCliRiskAccepted(false);
          }
        }}
      >
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="size-5 shrink-0 text-amber-500" />
              <span>{t.cliRiskModalTitle}</span>
            </DialogTitle>
            <DialogDescription className="pt-1 text-xs leading-relaxed">
              {t.cliRiskModalDesc}
            </DialogDescription>
          </DialogHeader>

          <div className="rounded-xl border border-amber-500/40 bg-amber-500/[0.08] p-3.5 text-xs leading-relaxed text-foreground">
            <ul className="list-disc space-y-2 pl-4">
              {t.cliRiskItems.map((risk) => (
                <li key={risk}>{risk}</li>
              ))}
            </ul>
          </div>

          <label className="flex cursor-pointer items-start gap-2.5 rounded-lg border border-border bg-muted/30 p-3 text-xs leading-relaxed">
            <input
              type="checkbox"
              checked={cliRiskAccepted}
              onChange={(event) => setCliRiskAccepted(event.target.checked)}
              className="mt-0.5 size-4 shrink-0 accent-amber-600"
            />
            <span>{t.cliRiskAckLabel}</span>
          </label>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={cliRiskConfirming}
              onClick={() => {
                setCliRiskModalOpen(false);
                setCliRiskAccepted(false);
              }}
            >
              {t.cliRiskCancel}
            </Button>
            <Button
              type="button"
              disabled={!cliRiskAccepted || cliRiskConfirming}
              onClick={() => {
                if (!cliRiskAccepted) return;
                if (bridge?.installed) {
                  setCliRiskConfirming(true);
                  void requestCliBridgePermission(defaultConnection, true)
                    .then((decision) => {
                      void queryClient.invalidateQueries({ queryKey: ["cli-bridge-status"] });
                      if (decision.granted) {
                        setCliPermOverride(true);
                        setCliRiskModalOpen(false);
                        setCliRiskAccepted(false);
                        toast.success("Browser CLI Bridge permission granted for this origin.");
                      } else {
                        setCliPermOverride(false);
                        toast.error(decision.error || "Browser CLI permission was denied.");
                      }
                    })
                    .finally(() => {
                      setCliRiskConfirming(false);
                    });
                  return;
                }
                setCliPermOverride(true);
                setCliRiskModalOpen(false);
                setCliRiskAccepted(false);
                toast.success("Local AI CLI permission granted.");
              }}
            >
              {cliRiskConfirming ? <Loader2 className="mr-1.5 size-3.5 animate-spin" /> : null}
              {t.cliRiskConfirm}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );

  return renderPanel(AI_COPY[lang], "papita-ai-panel");
}

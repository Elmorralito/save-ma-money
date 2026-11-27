import type { AIChatResponse, AIConnectionStatus, AIModelsResponse } from "@/api/ai";

const BRIDGE_CHANNEL = "papita-cli-bridge:v1";

export type CliBridgeStatus = {
  installed: boolean;
  version?: string;
  originGranted: boolean;
  nativeHostReady: boolean;
  nativeError?: string | null;
  clis: AIConnectionStatus[];
};

type BridgeResponse = {
  ok?: boolean;
  error?: string;
  code?: string;
  [key: string]: unknown;
};

function sendBridgeRequest(
  action: string,
  payload: Record<string, unknown> = {},
  timeoutMs = 15_000,
): Promise<BridgeResponse> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Browser CLI bridge is only available in a browser window."));
  }

  return new Promise((resolve, reject) => {
    const requestId = `pcb-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    let settled = false;

    const timer = window.setTimeout(() => {
      if (settled) return;
      settled = true;
      window.removeEventListener("message", onMessage);
      reject(new Error("Timed out waiting for Papita Local CLI Bridge extension."));
    }, timeoutMs);

    function onMessage(event: MessageEvent) {
      if (event.source !== window || event.origin !== window.location.origin) return;
      const data = event.data as Record<string, unknown> | null;
      if (!data || typeof data !== "object") return;
      if (data.channel !== BRIDGE_CHANNEL || data.direction !== "from-extension") return;
      if (data.requestId !== requestId) return;

      settled = true;
      window.clearTimeout(timer);
      window.removeEventListener("message", onMessage);
      resolve(data as BridgeResponse);
    }

    window.addEventListener("message", onMessage);
    window.postMessage(
      {
        channel: BRIDGE_CHANNEL,
        direction: "from-page",
        requestId,
        action,
        payload,
      },
      window.location.origin,
    );
  });
}

/** Detect whether the Papita Local CLI Bridge browser extension + native host are active. */
export async function detectCliBridge(timeoutMs = 1200): Promise<CliBridgeStatus> {
  try {
    const res = await sendBridgeRequest("ping", {}, timeoutMs);
    if (!res.ok) {
      return { installed: false, originGranted: false, nativeHostReady: false, clis: [] };
    }
    return {
      installed: Boolean(res.installed),
      version: typeof res.version === "string" ? res.version : undefined,
      originGranted: Boolean(res.originGranted),
      nativeHostReady: Boolean(res.nativeHostReady),
      nativeError: typeof res.nativeError === "string" ? res.nativeError : null,
      clis: Array.isArray(res.clis) ? (res.clis as AIConnectionStatus[]) : [],
    };
  } catch {
    return { installed: false, originGranted: false, nativeHostReady: false, clis: [] };
  }
}

/** Open the browser extension's explicit risk-consent window for this origin. */
export async function requestCliBridgePermission(
  connection: string,
  forcePrompt = false,
): Promise<{ granted: boolean; error?: string | null }> {
  const res = await sendBridgeRequest("request_permission", { connection, forcePrompt }, 120_000);
  return {
    granted: Boolean(res.granted),
    error: typeof res.error === "string" ? res.error : null,
  };
}

/** Revoke this origin's local CLI execution permission inside the browser extension. */
export async function revokeCliBridgePermission(): Promise<void> {
  try {
    await sendBridgeRequest("revoke_permission", {}, 5_000);
  } catch {
    // Ignore if extension is unavailable.
  }
}

/** Discover exact model IDs directly via the browser extension + native messaging host. */
export async function bridgeListModels(connection: string): Promise<AIModelsResponse> {
  const res = await sendBridgeRequest("list_models", { connection }, 20_000);
  if (!res.ok) {
    throw new Error(
      typeof res.error === "string" ? res.error : "Browser CLI model discovery failed.",
    );
  }
  const models = Array.isArray(res.models)
    ? (res.models as Array<{ id: string; label: string }>)
    : [];
  return {
    connection: typeof res.connection === "string" ? res.connection : connection,
    mode: "sidecar",
    ready: Boolean(res.ready),
    source: res.source === "live" ? "live" : "curated",
    models,
    default_model:
      typeof res.default_model === "string" ? res.default_model : (models[0]?.id ?? null),
  };
}

/** Execute a pinned local AI CLI directly on the user's machine via the browser extension. */
export async function bridgeChat(input: {
  connection: string;
  model?: string | null;
  systemPrompt?: string;
  userPrompt: string;
}): Promise<AIChatResponse> {
  const res = await sendBridgeRequest(
    "chat",
    {
      connection: input.connection,
      model: input.model ?? null,
      system_prompt: input.systemPrompt ?? "",
      user_prompt: input.userPrompt,
    },
    95_000,
  );
  if (!res.ok) {
    throw new Error(typeof res.error === "string" ? res.error : "Browser CLI execution failed.");
  }
  return {
    reply: typeof res.reply === "string" ? res.reply : "",
    connection: typeof res.connection === "string" ? res.connection : input.connection,
    kind: "cli",
    provider: typeof res.provider === "string" ? res.provider : input.connection,
    model: typeof res.model === "string" ? res.model : (input.model ?? null),
    context_included: Boolean(input.systemPrompt),
  };
}

import { apiFetch } from "@/api/http";

export type AIConnectionKind = "api" | "cli";

export type AIConnectionStatus = {
  id: string;
  kind: AIConnectionKind;
  provider: string;
  model: string | null;
  ready: boolean;
};

export type AIStatusResponse = {
  enabled: boolean;
  available: boolean;
  provider: string | null;
  model: string | null;
  default_connection: string | null;
  connections: AIConnectionStatus[];
  single_owner_enforced: boolean;
};

export type AIMode = "sidecar" | "lan_local" | "api_key";

export type AIConfigResponse = {
  enabled: boolean;
  mode: AIMode;
  default_connection: string;
  model: string | null;
  base_url: string | null;
  include_financial_context_by_default: boolean;
  reports_ai_enabled: boolean;
  payment_dues_ai_enabled: boolean;
  cli_permission_granted: boolean;
  lan_permission_granted: boolean;
  api_permission_granted: boolean;
  has_api_key: boolean;
  api_key_hint: string | null;
};

export type AIConfigUpdateRequest = {
  enabled?: boolean;
  mode?: AIMode;
  default_connection?: string;
  model?: string | null;
  base_url?: string | null;
  include_financial_context_by_default?: boolean;
  reports_ai_enabled?: boolean;
  payment_dues_ai_enabled?: boolean;
  cli_permission_granted?: boolean;
  lan_permission_granted?: boolean;
  api_permission_granted?: boolean;
  api_key?: string | null;
  clear_api_key?: boolean;
};

export type AIModelOption = {
  id: string;
  label: string;
};

export type AIModelsRequest = {
  mode: AIMode;
  connection: string;
  base_url?: string | null;
  api_key?: string | null;
};

export type AIModelsResponse = {
  connection: string;
  mode: AIMode;
  ready: boolean;
  source: "live" | "curated";
  models: AIModelOption[];
  default_model: string | null;
};

export type AIChatRequest = {
  prompt: string;
  connection?: string | null;
  include_financial_context?: boolean;
  currency?: string | null;
  module?: string | null;
  view?: string | null;
  control?: string | null;
  locale?: string | null;
  surface_context?: Record<string, unknown> | null;
};

export type AIChatResponse = {
  reply: string;
  connection: string | null;
  kind: AIConnectionKind | null;
  provider: string;
  model: string | null;
  context_included: boolean;
};

export async function getAIStatus(signal?: AbortSignal): Promise<AIStatusResponse> {
  const { data } = await apiFetch<AIStatusResponse>("/api/v1/ai/status", { method: "GET", signal });
  return data;
}

export async function getAIConfig(signal?: AbortSignal): Promise<AIConfigResponse> {
  const { data } = await apiFetch<AIConfigResponse>("/api/v1/ai/config", { method: "GET", signal });
  return data;
}

export async function updateAIConfig(payload: AIConfigUpdateRequest): Promise<AIConfigResponse> {
  const { data } = await apiFetch<AIConfigResponse>("/api/v1/ai/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return data;
}

export async function fetchAIModels(payload: AIModelsRequest): Promise<AIModelsResponse> {
  const { data } = await apiFetch<AIModelsResponse>("/api/v1/ai/models", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return data;
}

export async function sendAIChat(payload: AIChatRequest): Promise<AIChatResponse> {
  const { data } = await apiFetch<AIChatResponse>("/api/v1/ai/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return data;
}

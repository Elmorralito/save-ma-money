import { PapitaApiError } from "@/api/errors";
import { apiFetch } from "@/api/http";
import type {
  IngestionRunResponse,
  PaginatedIngestionConnections,
  PaginatedIngestionRuns,
} from "@/types/domain";

const INGESTION_PATH = "/api/v1/ingestion";

export type LatestIngestionRunParams = {
  connection_id?: string | null;
  signal?: AbortSignal;
};

export type ListIngestionRunsParams = {
  connection_id?: string | null;
  skip?: number;
  limit?: number;
  signal?: AbortSignal;
};

export type ListIngestionConnectionsParams = {
  skip?: number;
  limit?: number;
  signal?: AbortSignal;
};

function buildQuery(params: Record<string, string | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, value);
    }
  }
  const qs = search.toString();
  return qs === "" ? "" : `?${qs}`;
}

/**
 * ``GET /api/v1/ingestion/runs/latest`` — latest ingestion run for the owner.
 *
 * Returns ``null`` when the API replies 404 (no runs recorded yet).
 */
export async function getLatestIngestionRun(
  params: LatestIngestionRunParams = {},
): Promise<IngestionRunResponse | null> {
  const { signal, connection_id } = params;
  const path = `${INGESTION_PATH}/runs/latest${buildQuery({
    connection_id: connection_id ?? undefined,
  })}`;
  try {
    const result = await apiFetch<IngestionRunResponse>(path, { signal });
    return result.data;
  } catch (err) {
    if (err instanceof PapitaApiError && err.status === 404) {
      return null;
    }
    throw err;
  }
}

/** ``GET /api/v1/ingestion/runs`` — paginated recent ingestion runs. */
export async function listIngestionRuns(
  params: ListIngestionRunsParams = {},
): Promise<PaginatedIngestionRuns> {
  const { signal, connection_id, skip, limit } = params;
  const path = `${INGESTION_PATH}/runs${buildQuery({
    connection_id: connection_id ?? undefined,
    skip: skip !== undefined ? String(skip) : undefined,
    limit: limit !== undefined ? String(limit) : undefined,
  })}`;
  const result = await apiFetch<PaginatedIngestionRuns>(path, { signal });
  return result.data;
}

/** ``GET /api/v1/ingestion/connections`` — paginated ingestion connections. */
export async function listIngestionConnections(
  params: ListIngestionConnectionsParams = {},
): Promise<PaginatedIngestionConnections> {
  const { signal, skip, limit } = params;
  const path = `${INGESTION_PATH}/connections${buildQuery({
    skip: skip !== undefined ? String(skip) : undefined,
    limit: limit !== undefined ? String(limit) : undefined,
  })}`;
  const result = await apiFetch<PaginatedIngestionConnections>(path, { signal });
  return result.data;
}

export type EmailParserMode =
  "auto" | "bancolombia-email" | "global66-email" | "nequi-email" | "nu-email" | "custom_regex";

export type EmailRuleTransactionType = "auto" | "income" | "expense" | "transfer";

export type EmailParsingRule = {
  id?: string | null;
  name: string;
  enabled: boolean;
  parser_mode: EmailParserMode;
  sender_match: string;
  subject_match: string;
  amount_regex: string;
  transaction_type: EmailRuleTransactionType;
  currency: string;
  default_account_id?: string | null;
  default_category_id?: string | null;
  description_template: string;
};

export type EmailIngestionConnection = {
  id: string;
  provider: string;
  flow_name: string;
  deployment_name?: string | null;
  enabled: boolean;
  lookback_hours: number;
  email_senders: string[];
  email_subjects: string[];
  email_source_label?: string | null;
  email_query?: string | null;
  gmail_access_enabled: boolean;
  gmail_connected: boolean;
  gmail_connected_email?: string | null;
  parsing_rules: EmailParsingRule[];
  created_at?: string | null;
  updated_at?: string | null;
};

export type UpsertEmailIngestionConfigPayload = {
  provider?: "email";
  flow_name?: "papita-email-ingestion";
  enabled: boolean;
  lookback_hours: number;
  email_senders: string[];
  email_subjects: string[];
  email_source_label?: string | null;
  gmail_access_enabled: boolean;
  parsing_rules: EmailParsingRule[];
};

export type EmailParseTestPayload = {
  sender: string;
  subject: string;
  body: string;
  rules?: EmailParsingRule[];
};

export type EmailParseTestResult = {
  matched: boolean;
  matched_rule_name?: string | null;
  parser_used?: string | null;
  transaction_type?: string | null;
  amount?: number | null;
  currency?: string | null;
  description?: string | null;
  default_account_id?: string | null;
  default_category_id?: string | null;
  error?: string | null;
};

/** Same-origin URL to start per-user Gmail OAuth (`gmail.modify`). */
export function gmailOAuthStartUrl(): string {
  return `${INGESTION_PATH}/gmail/oauth/start`;
}

/** ``PUT /api/v1/ingestion/connections`` — save per-user Gmail access, filters, and parsing rules. */
export async function upsertEmailIngestionConnection(
  payload: UpsertEmailIngestionConfigPayload,
): Promise<EmailIngestionConnection> {
  const result = await apiFetch<EmailIngestionConnection>(`${INGESTION_PATH}/connections`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      provider: "email",
      flow_name: "papita-email-ingestion",
      ...payload,
    }),
  });
  return result.data;
}

/** ``POST /api/v1/ingestion/gmail/disconnect`` — clear stored per-user Gmail refresh token. */
export async function disconnectGmailConnection(): Promise<EmailIngestionConnection> {
  const result = await apiFetch<EmailIngestionConnection>(`${INGESTION_PATH}/gmail/disconnect`, {
    method: "POST",
  });
  return result.data;
}

/** ``POST /api/v1/ingestion/email/test-parse`` — dry-run sample email against parsing rules. */
export async function testEmailParse(
  payload: EmailParseTestPayload,
): Promise<EmailParseTestResult> {
  const result = await apiFetch<EmailParseTestResult>(`${INGESTION_PATH}/email/test-parse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return result.data;
}

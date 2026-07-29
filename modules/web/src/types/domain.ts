/**
 * Thin re-exports of OpenAPI schema component types.
 *
 * Domain business rules stay in ``papita_txnsmodel`` / ``papita_txnsapi``.
 * Prefer these aliases over hand-rolled DTO shapes (PPT-048 / #114).
 */
import type { components } from "./api";

/** OpenAPI ``components.schemas`` map from the committed artifact. */
export type ApiSchemas = components["schemas"];

export type HealthResponse = ApiSchemas["HealthResponse"];
export type AuthHealthResponse = ApiSchemas["AuthHealthResponse"];
export type DatabaseHealthResponse = ApiSchemas["DatabaseHealthResponse"];
export type RedisHealthResponse = ApiSchemas["RedisHealthResponse"];

/**
 * Shape of ``GET /api/v1/meta/client-contract``.
 *
 * OpenAPI types the 200 body as a free-form object; this interface mirrors the
 * JSON from ``papita_txnsapi.core.client_contract.build_client_contract`` without
 * reimplementing limit enforcement in TypeScript.
 */
export type ClientContract = {
  breaking_changes: string;
  api_version: string;
  secure_defaults: {
    reports_foreign_account_status: number;
    cash_flow_refresh_balances_default: boolean;
    bulk_max_transactions: number;
    report_window_max_days: number;
    docs_require_debug_or_docs_enabled: boolean;
    cors_wildcard_forbidden_when_not_debug: boolean;
  };
  effective: {
    reports_foreign_account_status: number;
    cash_flow_refresh_balances_default: boolean;
    bulk_max_transactions: number;
    report_window_max_days: number;
    docs_enabled: boolean;
  };
  compat: {
    active: string[];
    sunset: string | null;
    flags: Record<string, { enabled: boolean; effect: string }>;
  };
  error_codes: Record<string, string>;
  migration: {
    probe: string;
    prefer_headers: string[];
    client_checklist: string[];
  };
};

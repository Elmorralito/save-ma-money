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

export type AccountCreate = ApiSchemas["AccountCreate"];
export type AccountUpdate = ApiSchemas["AccountUpdate"];
export type AccountResponse = ApiSchemas["AccountResponse"];
export type PaginatedAccounts = ApiSchemas["PaginatedResponse_AccountResponse_"];
export type BankingDetailsSchema = ApiSchemas["BankingDetailsSchema"];
export type TradingDetailsSchema = ApiSchemas["TradingDetailsSchema"];
export type RealEstateDetailsSchema = ApiSchemas["RealEstateDetailsSchema"];
export type CreditCardDetailsSchema = ApiSchemas["CreditCardDetailsSchema"];
export type LoanDetailsSchema = ApiSchemas["LoanDetailsSchema"];

export type CategoryCreate = ApiSchemas["CategoryCreate"];
export type CategoryUpdate = ApiSchemas["CategoryUpdate"];
export type CategoryResponse = ApiSchemas["CategoryResponse"];
export type PaginatedCategories = ApiSchemas["PaginatedResponse_CategoryResponse_"];
export type CategorySubcategoryResponse = ApiSchemas["CategorySubcategoryResponse"];

export type TransactionCreate = ApiSchemas["TransactionCreate"];
export type TransactionUpdate = ApiSchemas["TransactionUpdate"];
export type TransactionResponse = ApiSchemas["TransactionResponse"];
export type TransactionBulkCreate = ApiSchemas["TransactionBulkCreate"];
export type TransactionBulkResponse = ApiSchemas["TransactionBulkResponse"];
export type PaginatedTransactions = ApiSchemas["PaginatedResponse_TransactionResponse_"];

export type TransactionTemplateCreate = ApiSchemas["TransactionTemplateCreate"];
export type TransactionTemplateUpdate = ApiSchemas["TransactionTemplateUpdate"];
export type TransactionTemplateResponse = ApiSchemas["TransactionTemplateResponse"];
export type PaginatedTransactionTemplates =
  ApiSchemas["PaginatedResponse_TransactionTemplateResponse_"];
export type UpcomingDueResponse = ApiSchemas["UpcomingDueResponse"];
export type UpcomingDuesResponse = ApiSchemas["UpcomingDuesResponse"];
export type MarkPaidRequest = ApiSchemas["MarkPaidRequest"];
export type ClearPaidRequest = ApiSchemas["ClearPaidRequest"];

export type MovementCreate = ApiSchemas["MovementCreate"];
export type MovementUpdate = ApiSchemas["MovementUpdate"];
export type MovementResponse = ApiSchemas["MovementResponse"];
export type MovementExecuteResponse = ApiSchemas["MovementExecuteResponse"];
export type PaginatedMovements = ApiSchemas["PaginatedResponse_MovementResponse_"];

export type ReportPeriod = ApiSchemas["ReportPeriod"];
export type SpendingBreakdownItem = ApiSchemas["SpendingBreakdownItem"];
export type SpendingReportResponse = ApiSchemas["SpendingReportResponse"];
export type CashFlowReportResponse = ApiSchemas["CashFlowReportResponse"];
export type TrendsReportResponse = ApiSchemas["TrendsReportResponse"];

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

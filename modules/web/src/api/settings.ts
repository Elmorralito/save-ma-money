import { apiFetch } from "@/api/http";

export type SupportedCurrency = "COP" | "USD" | "EUR" | "GBP" | "MXN" | "CLP" | "PEN" | "BRL";
export type SupportedLocale = "es-CO" | "en-US" | "es-ES" | "en-GB";
export type SupportedDateFormat = "YYYY-MM-DD" | "DD/MM/YYYY" | "MM/DD/YYYY";
export type SupportedPageSize = 10 | 25 | 50 | 100;

export type UserPreferences = {
  base_currency: SupportedCurrency;
  locale: SupportedLocale;
  timezone: string;
  date_format: SupportedDateFormat;
  default_page_size: SupportedPageSize;
  hide_balances_by_default: boolean;
  default_account_id: string | null;
  default_income_category_id: string | null;
  default_expense_category_id: string | null;
  credit_card_cashflow_only: boolean;
  auto_refresh_balances: boolean;
  fiscal_month_start_day: number;
  payment_due_reminder_days: number;
  low_runway_months_threshold: number;
  high_utilization_pct_threshold: number;
  large_transaction_alert_amount: number | null;
  redact_card_numbers: boolean;
  require_dkim_spf_for_email_ingestion: boolean;
  session_idle_timeout_minutes: number;
};

export type UserSettings = {
  id: string;
  username: string;
  email: string;
  display_name: string | null;
  phone: string | null;
  auth_provider: string;
  provider_type: string;
  preferences: UserPreferences;
  updated_at: string | null;
};

export type UpdateUserSettingsPayload = {
  display_name?: string | null;
  phone?: string | null;
  preferences?: UserPreferences;
};

const SETTINGS_PATH = "/api/v1/settings";

export async function getUserSettings(signal?: AbortSignal): Promise<UserSettings> {
  const result = await apiFetch<UserSettings>(SETTINGS_PATH, { signal });
  return result.data;
}

export async function updateUserSettings(
  payload: UpdateUserSettingsPayload,
): Promise<UserSettings> {
  const result = await apiFetch<UserSettings>(SETTINGS_PATH, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return result.data;
}

export async function resetUserSettings(): Promise<UserSettings> {
  const result = await apiFetch<UserSettings>(`${SETTINGS_PATH}/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  return result.data;
}

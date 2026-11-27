/** Supported UI locales matching backend ``UserPreferences.locale``. */
export const LOCALES = ["en-US", "es-CO", "es-ES", "en-GB"] as const;

export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "en-US";

export const LOCALE_STORAGE_KEY = "papita_locale";

export const LOCALE_TO_LANGUAGE: Record<Locale, "en" | "es"> = {
  "en-US": "en",
  "en-GB": "en",
  "es-CO": "es",
  "es-ES": "es",
};

export const LOCALE_LABELS: Record<Locale, string> = {
  "en-US": "English (US)",
  "es-CO": "Español (Colombia)",
  "es-ES": "Español (España)",
  "en-GB": "English (UK)",
};

export const LOCALE_SHORT_CODES: Record<Locale, string> = {
  "en-US": "EN",
  "en-GB": "EN",
  "es-CO": "ES",
  "es-ES": "ES",
};

export function isLocale(value: string): value is Locale {
  return (LOCALES as readonly string[]).includes(value);
}

export function resolveLocale(raw: string | null | undefined): Locale {
  if (raw && isLocale(raw)) return raw;
  return DEFAULT_LOCALE;
}

/**
 * Map browser / Accept-Language tags to a supported app locale.
 * Prefers the first matching language in navigator.languages order.
 */
export function localeFromUserAgent(
  languages: readonly string[] | null | undefined,
): Locale | null {
  if (!languages?.length) return null;
  for (const raw of languages) {
    const tag = raw.trim().toLowerCase();
    if (!tag) continue;
    if (tag === "es-co") return "es-CO";
    if (tag === "es-es") return "es-ES";
    if (tag === "en-gb") return "en-GB";
    const primary = tag.split("-")[0] ?? "";
    if (primary === "es") return "es-CO";
    if (primary === "en") return "en-US";
  }
  return null;
}

/**
 * Initial UI locale before user settings load.
 * Explicit storage wins; otherwise follow the user agent; else default.
 */
export function resolveInitialLocale(stored: string | null | undefined): Locale {
  if (stored && isLocale(stored)) return stored;
  if (typeof navigator !== "undefined") {
    const fromUa = localeFromUserAgent(navigator.languages ?? [navigator.language]);
    if (fromUa) return fromUa;
  }
  return DEFAULT_LOCALE;
}

let userDefaultLocale: Locale = DEFAULT_LOCALE;

export function getUserDefaultLocale(): Locale {
  return userDefaultLocale;
}

export function setUserDefaultLocale(locale: Locale): void {
  userDefaultLocale = locale;
}

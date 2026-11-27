import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  DEFAULT_LOCALE,
  LOCALE_STORAGE_KEY,
  LOCALE_TO_LANGUAGE,
  type Locale,
  getUserDefaultLocale,
  isLocale,
  resolveInitialLocale,
  setUserDefaultLocale,
} from "@/i18n/locales";
import { en_US, type MessageCatalog } from "@/i18n/messages/en_US";
import { es_CO } from "@/i18n/messages/es_CO";

const catalogs: Record<Locale, MessageCatalog> = {
  "en-US": en_US,
  "en-GB": en_US,
  "es-CO": es_CO,
  "es-ES": es_CO,
};

let activeMessages: MessageCatalog = en_US;
let activeLocale: Locale = DEFAULT_LOCALE;

export function getActiveMessages(): MessageCatalog {
  return activeMessages;
}

export function getActiveLocale(): Locale {
  return activeLocale;
}

export { getUserDefaultLocale };

type LocaleContextValue = {
  locale: Locale;
  userDefaultLocale: Locale;
  messages: MessageCatalog;
  setLocale: (locale: Locale) => void;
  /**
   * Apply saved user preference when the browser has no explicit localStorage override.
   */
  applyUserDefaultLocale: (locale: Locale) => void;
};

const LocaleContext = createContext<LocaleContextValue>({
  locale: DEFAULT_LOCALE,
  userDefaultLocale: DEFAULT_LOCALE,
  messages: en_US,
  setLocale: () => undefined,
  applyUserDefaultLocale: () => undefined,
});

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    if (typeof window === "undefined") return DEFAULT_LOCALE;
    try {
      return resolveInitialLocale(window.localStorage.getItem(LOCALE_STORAGE_KEY));
    } catch {
      return DEFAULT_LOCALE;
    }
  });
  const [userDefault, setUserDefault] = useState<Locale>(DEFAULT_LOCALE);

  useEffect(() => {
    document.documentElement.lang = LOCALE_TO_LANGUAGE[locale];
    activeLocale = locale;
    activeMessages = catalogs[locale];
  }, [locale]);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    try {
      window.localStorage.setItem(LOCALE_STORAGE_KEY, next);
    } catch {
      // Ignore storage failures in restricted contexts.
    }
  }, []);

  const applyUserDefaultLocale = useCallback((next: Locale) => {
    setUserDefault(next);
    setUserDefaultLocale(next);
    try {
      const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);
      if (stored && isLocale(stored)) return;
    } catch {
      // ignore
    }
    setLocaleState(next);
  }, []);

  const value = useMemo(
    () => ({
      locale,
      userDefaultLocale: userDefault,
      messages: catalogs[locale],
      setLocale,
      applyUserDefaultLocale,
    }),
    [locale, userDefault, setLocale, applyUserDefaultLocale],
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  return useContext(LocaleContext);
}

export function useMessages(): MessageCatalog {
  return useContext(LocaleContext).messages;
}

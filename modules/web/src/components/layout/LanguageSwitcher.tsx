import { LOCALE_LABELS, LOCALE_SHORT_CODES, LOCALES, type Locale } from "@/i18n/locales";
import { useLocale } from "@/i18n/LocaleProvider";
import { cn } from "@/lib/utils";

type Props = {
  className?: string;
  /** Short-code control (closed face shows EN or ES, mirroring Piggies-VetPharma-Track). */
  compact?: boolean;
};

export function LanguageSwitcher({ className, compact = true }: Props) {
  const { locale, setLocale, messages } = useLocale();
  const shortCode = LOCALE_SHORT_CODES[locale];
  const fullName = LOCALE_LABELS[locale];
  const title = `${messages.language}: ${shortCode} → ${fullName}`;

  if (compact) {
    return (
      <label
        className={cn(
          "group relative inline-flex h-8 w-9 shrink-0 cursor-pointer items-center justify-center rounded-xl border border-border bg-muted/40 text-xs font-semibold text-foreground transition-colors hover:border-primary/40 hover:bg-muted",
          className,
        )}
      >
        <span className="pointer-events-none select-none" aria-hidden="true">
          {shortCode}
        </span>
        <span
          role="tooltip"
          className="pointer-events-none absolute right-0 top-full z-30 mt-1.5 whitespace-nowrap rounded-md bg-[#04090c] px-2 py-1 text-[11px] font-medium text-white opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100"
        >
          {title}
        </span>
        <select
          value={locale}
          onChange={(event) => setLocale(event.target.value as Locale)}
          className="absolute inset-0 cursor-pointer opacity-0"
          aria-label={title}
        >
          {LOCALES.map((code) => (
            <option key={code} value={code}>
              {LOCALE_SHORT_CODES[code]} · {LOCALE_LABELS[code]}
            </option>
          ))}
        </select>
      </label>
    );
  }

  return (
    <label className={cn("flex flex-col gap-1.5 text-xs text-muted-foreground", className)}>
      <span>{messages.language}</span>
      <select
        value={locale}
        onChange={(event) => setLocale(event.target.value as Locale)}
        aria-label={title}
        className="h-9 rounded-lg border border-border bg-card px-2.5 text-sm text-foreground"
      >
        {LOCALES.map((code) => (
          <option key={code} value={code}>
            {LOCALE_SHORT_CODES[code]} · {LOCALE_LABELS[code]}
          </option>
        ))}
      </select>
    </label>
  );
}

import type { LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";

import { cn } from "@/lib/utils";

export type ActionIconTone = "emerald" | "amber" | "sky" | "violet" | "rose" | "neutral";

const ACTION_TONE_CLASSES: Record<ActionIconTone, string> = {
  emerald:
    "border-emerald-500/25 bg-emerald-500/10 text-emerald-700 hover:border-emerald-500/45 hover:bg-emerald-500/20 focus-visible:ring-emerald-500/40 dark:text-emerald-300",
  amber:
    "border-amber-500/25 bg-amber-500/10 text-amber-700 hover:border-amber-500/45 hover:bg-amber-500/20 focus-visible:ring-amber-500/40 dark:text-amber-300",
  sky: "border-sky-500/25 bg-sky-500/10 text-sky-700 hover:border-sky-500/45 hover:bg-sky-500/20 focus-visible:ring-sky-500/40 dark:text-sky-300",
  violet:
    "border-violet-500/25 bg-violet-500/10 text-violet-700 hover:border-violet-500/45 hover:bg-violet-500/20 focus-visible:ring-violet-500/40 dark:text-violet-300",
  rose: "border-rose-500/25 bg-rose-500/10 text-rose-700 hover:border-rose-500/45 hover:bg-rose-500/20 focus-visible:ring-rose-500/40 dark:text-rose-300",
  neutral:
    "border-border bg-muted/40 text-muted-foreground hover:border-foreground/30 hover:bg-muted hover:text-foreground focus-visible:ring-primary/40",
};

export type ActionIconButtonProps = {
  icon: LucideIcon;
  label: string;
  tone: ActionIconTone;
  disabled?: boolean;
  onClick?: () => void;
  to?: string;
  ariaExpanded?: boolean;
  className?: string;
};

/**
 * Standardized compact colorized icon action button with accessible obsidian tooltip.
 * Shared across Payment Dues, Transactions, Categories, Accounts, and Integrations tables.
 */
export function ActionIconButton({
  icon: Icon,
  label,
  tone,
  disabled = false,
  onClick,
  to,
  ariaExpanded,
  className,
}: ActionIconButtonProps) {
  const controlClasses = cn(
    "inline-flex size-8 items-center justify-center rounded-lg border transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 disabled:pointer-events-none disabled:opacity-45",
    ACTION_TONE_CLASSES[tone],
    className,
  );

  return (
    <span className="group/tip relative inline-flex">
      {to && !disabled ? (
        <Link to={to} aria-label={label} className={controlClasses}>
          <Icon aria-hidden="true" className="size-4" />
        </Link>
      ) : (
        <button
          type="button"
          aria-label={label}
          aria-expanded={ariaExpanded}
          disabled={disabled}
          onClick={onClick}
          className={controlClasses}
        >
          <Icon aria-hidden="true" className="size-4" />
        </button>
      )}
      <span
        role="tooltip"
        className="pointer-events-none absolute right-0 bottom-full z-30 mb-1.5 whitespace-nowrap rounded-md bg-[#04090c] px-2 py-1 text-[11px] font-medium text-white opacity-0 transition-opacity duration-150 group-hover/tip:opacity-100 group-focus-within/tip:opacity-100"
      >
        {label}
      </span>
    </span>
  );
}

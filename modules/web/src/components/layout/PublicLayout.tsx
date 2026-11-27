import { Activity, Landmark, ShieldCheck } from "lucide-react";
import { Outlet } from "react-router-dom";

const PILLARS = [
  { icon: Landmark, label: "All accounts", hint: "No pretending that card isn't yours" },
  { icon: Activity, label: "Real runway", hint: "Months left before ramen season" },
  { icon: ShieldCheck, label: "Owner-only", hint: "Nobody else sees 2 a.m. receipts" },
] as const;

/** Split brand + elevated auth card layout for unauthenticated routes (login / register). */
export function PublicLayout() {
  const title = import.meta.env.VITE_APP_TITLE ?? "Papita";

  return (
    <div className="grid min-h-svh bg-background lg:grid-cols-[1.15fr_1fr]">
      <aside
        className="relative hidden flex-col justify-between overflow-hidden bg-[#04090c] p-10 text-white lg:flex xl:p-12"
        style={{ contain: "layout style paint" }}
      >
        <div
          aria-hidden="true"
          className="animate-papita-ambient pointer-events-none absolute -inset-12 opacity-75"
          style={{
            backgroundImage:
              "radial-gradient(circle at 50% 42%, oklch(0.30 0.09 200 / 0.42), transparent 60%), radial-gradient(circle at 20% 88%, oklch(0.28 0.08 165 / 0.30), transparent 52%)",
          }}
        />

        <div className="relative z-10 flex items-center justify-between gap-4">
          <span className="text-base font-semibold tracking-tight text-white">{title}</span>
          <span className="rounded-full border border-emerald-400/25 bg-emerald-400/10 px-3 py-1 text-[11px] font-medium tracking-wide text-emerald-300">
            Financial Freedom (Soon™)
          </span>
        </div>

        <div className="relative z-10 mx-auto flex w-full max-w-lg flex-col items-center text-center">
          <div className="w-full max-w-md">
            <img
              src="/save-ma-money-brand.png"
              alt="Save Ma Money — Broke but planning"
              width={644}
              height={501}
              decoding="async"
              className="mx-auto block h-auto w-full object-contain drop-shadow-[0_18px_36px_rgba(0,0,0,0.75)]"
            />
          </div>

          <div className="mt-4 max-w-md space-y-2.5">
            <h2 className="text-2xl font-semibold leading-snug tracking-tight text-balance text-white xl:text-[28px]">
              Broke is temporary. Your spreadsheet denial doesn&apos;t have to be.
            </h2>
            <p className="text-sm leading-relaxed text-white/70">
              Reconcile every account, check how long your cash actually lasts, and catch every
              questionable bank alert in one place.
            </p>
          </div>
        </div>

        <div className="relative z-10 space-y-4">
          <ul className="grid grid-cols-3 gap-5 border-t border-white/12 pt-5">
            {PILLARS.map(({ icon: Icon, label, hint }) => (
              <li key={label} className="space-y-1">
                <div className="flex items-center gap-2 text-emerald-300">
                  <Icon aria-hidden="true" className="size-3.5 shrink-0" />
                  <span className="text-xs font-semibold text-white">{label}</span>
                </div>
                <p className="text-xs leading-snug text-white/75">{hint}</p>
              </li>
            ))}
          </ul>
          <p className="text-center text-xs text-white/65">
            {title} · Broke and still better than your budget :)
          </p>
        </div>
      </aside>

      <div
        className="relative flex flex-col bg-background"
        style={{
          backgroundImage:
            "radial-gradient(circle at 82% 14%, oklch(0.88 0.045 205 / 0.35), transparent 46%)",
        }}
      >
        <header className="flex items-center justify-between border-b border-border bg-card px-5 py-3.5 lg:hidden">
          <span className="text-sm font-semibold tracking-tight text-foreground">{title}</span>
          <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-[11px] font-medium text-primary">
            Soon™
          </span>
        </header>

        <main className="flex flex-1 items-start justify-center px-4 py-10 sm:items-center sm:px-8">
          <div
            className="animate-papita-card-enter w-full max-w-md rounded-2xl border border-border bg-card p-6 text-card-foreground sm:p-8"
            style={{ contain: "layout style" }}
          >
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

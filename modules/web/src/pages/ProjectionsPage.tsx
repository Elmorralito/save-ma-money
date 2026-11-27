import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Calculator, CreditCard, Landmark, Save, TrendingUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import {
  computeCreditCardProjection,
  computeInvestmentProjection,
  computeLoanProjection,
  computeRealEstateProjection,
  getProjectionPortfolio,
  saveAccountProjectionConfig,
  type AmortizationMethod,
  type CreditCardProjectionResponse,
  type InvestmentProjectionResponse,
  type InvestmentType,
  type LoanAmortizationResponse,
  type PortfolioAccountProjectionItem,
  type RateConvention,
  type RealEstateProjectionResponse,
} from "@/api/projections";
import { ScopedAIPanel, ScopedAITrigger, useScopedAIToggle } from "@/components/ai/ScopedAICopilot";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatApiError } from "@/lib/formatApiError";
import { useLocale } from "@/i18n/LocaleProvider";
import { formatMoney } from "@/lib/formatMoney";
import { cn } from "@/lib/utils";

type ProjectionTab = "debts" | "credit_cards" | "real_estate" | "investments";

const RATE_CONVENTIONS: ReadonlyArray<{ value: RateConvention; label: string }> = [
  { value: "CO_EA", label: "Colombia — Efectivo Anual (EA)" },
  { value: "US_APR", label: "USA — Nominal APR (÷12)" },
  { value: "US_APY", label: "USA — Compound APY" },
  { value: "MONTHLY_MV", label: "Monthly Effective (MV %)" },
];

const INVESTMENT_TYPES: ReadonlyArray<{ value: InvestmentType; label: string }> = [
  { value: "hysa_co", label: "High-Yield Savings (Colombia EA)" },
  { value: "fiduciary_co", label: "Fiduciary / FIC (Colombia)" },
  { value: "cdt_co", label: "CDT (Colombia)" },
  { value: "voluntary_pension", label: "Voluntary Pension (Protección)" },
  { value: "us_equity_etf", label: "US Stocks / ETFs (IBKR)" },
  { value: "crypto", label: "Crypto Assets" },
  { value: "private_equity", label: "Private / Lending Investment" },
  { value: "real_estate_fund", label: "Real Estate Fund / REIT" },
];

const num = (v: unknown, fallback: number): number =>
  typeof v === "number" && Number.isFinite(v) ? v : fallback;

export function ProjectionsPage() {
  const { locale } = useLocale();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<ProjectionTab>("debts");
  const [selectedId, setSelectedId] = useState<string>("");

  const portfolioQuery = useQuery({
    queryKey: ["projections-portfolio"],
    queryFn: ({ signal }) => getProjectionPortfolio(signal),
  });

  const activeItems = useMemo<PortfolioAccountProjectionItem[]>(() => {
    const p = portfolioQuery.data;
    if (!p) return [];
    if (activeTab === "debts") return p.debts;
    if (activeTab === "credit_cards") return p.credit_cards;
    if (activeTab === "real_estate") return p.real_estate;
    return p.investments;
  }, [activeTab, portfolioQuery.data]);

  const selectedAccount = useMemo(
    () => activeItems.find((a) => a.id === selectedId) ?? activeItems[0] ?? null,
    [activeItems, selectedId],
  );

  // Loan state
  const [loanPrincipal, setLoanPrincipal] = useState(100_000_000);
  const [loanRate, setLoanRate] = useState(11.9);
  const [loanConv, setLoanConv] = useState<RateConvention>("CO_EA");
  const [loanMonths, setLoanMonths] = useState(61);
  const [loanInsurance, setLoanInsurance] = useState(20_833);
  const [loanExtraMonthly, setLoanExtraMonthly] = useState(0);
  const [loanLumpSum, setLoanLumpSum] = useState(0);
  const [loanMethod, setLoanMethod] = useState<AmortizationMethod>("french_fixed");
  const [loanResult, setLoanResult] = useState<LoanAmortizationResponse | null>(null);

  // Credit card state
  const [ccBalance, setCcBalance] = useState(2_455_880);
  const [ccRate, setCcRate] = useState(25.0);
  const [ccConv, setCcConv] = useState<RateConvention>("CO_EA");
  const [ccPayment, setCcPayment] = useState(600_000);
  const [ccNewSpend, setCcNewSpend] = useState(0);
  const [ccFee, setCcFee] = useState(0);
  const [ccOneCuota, setCcOneCuota] = useState(false);
  const [ccResult, setCcResult] = useState<CreditCardProjectionResponse | null>(null);

  // Real estate state
  const [reValue, setReValue] = useState(431_000_000);
  const [reAppr, setReAppr] = useState(8.0);
  const [reYears, setReYears] = useState(10);
  const [reRent, setReRent] = useState(3_500_000);
  const [reOcc, setReOcc] = useState(75);
  const [reHoa, setReHoa] = useState(258_000);
  const [reTax, setReTax] = useState(0.6);
  const [reMortBal, setReMortBal] = useState(159_000_000);
  const [reMortRate, setReMortRate] = useState(17.1);
  const [reMortConv, setReMortConv] = useState<RateConvention>("CO_EA");
  const [reMortMonths, setReMortMonths] = useState(226);
  const [reMortIns, setReMortIns] = useState(64_344);
  const [reResult, setReResult] = useState<RealEstateProjectionResponse | null>(null);

  // Investment state
  const [invInitial, setInvInitial] = useState(31_322_865);
  const [invType, setInvType] = useState<InvestmentType>("hysa_co");
  const [invReturn, setInvReturn] = useState(9.5);
  const [invConv, setInvConv] = useState<RateConvention>("CO_EA");
  const [invYears, setInvYears] = useState(10);
  const [invMonthly, setInvMonthly] = useState(0);
  const [invFee, setInvFee] = useState(0.0);
  const [invInflation, setInvInflation] = useState(5.0);
  const [invTax, setInvTax] = useState(7.0);
  const [invFxDrift, setInvFxDrift] = useState(0.0);
  const [invResult, setInvResult] = useState<InvestmentProjectionResponse | null>(null);

  // Hydrate inputs whenever selectedAccount changes
  useEffect(() => {
    if (!selectedAccount) return;
    const cfg = selectedAccount.config ?? {};
    queueMicrotask(() => {
      if (selectedAccount.group === "debt") {
        setLoanPrincipal(selectedAccount.balance > 0 ? selectedAccount.balance : 10_000_000);
        setLoanRate(num(cfg.annual_rate_pct, 15.0));
        setLoanConv((cfg.rate_convention as RateConvention) || "CO_EA");
        setLoanMonths(num(cfg.remaining_months, 60));
        setLoanInsurance(num(cfg.monthly_insurance, 0));
        setLoanExtraMonthly(num(cfg.extra_monthly_payment, 0));
        setLoanLumpSum(0);
        setLoanResult(null);
      } else if (selectedAccount.group === "credit_card") {
        setCcBalance(selectedAccount.balance);
        setCcRate(num(cfg.annual_rate_pct, 25.0));
        setCcConv((cfg.rate_convention as RateConvention) || "CO_EA");
        setCcPayment(num(cfg.monthly_payment, Math.max(selectedAccount.balance, 200_000)));
        setCcOneCuota(Boolean(cfg.pay_in_one_installment));
        setCcNewSpend(0);
        setCcFee(0);
        setCcResult(null);
      } else if (selectedAccount.group === "real_estate") {
        setReValue(selectedAccount.balance > 0 ? selectedAccount.balance : 431_000_000);
        setReAppr(num(cfg.annual_appreciation_pct, 8.0));
        setReYears(num(cfg.horizon_years, 10));
        setReRent(num(cfg.monthly_rent_income, 3_500_000));
        setReOcc(num(cfg.occupancy_pct, 75));
        setReHoa(num(cfg.monthly_hoa_and_maintenance, 258_000));
        setReTax(num(cfg.annual_property_tax_pct, 0.6));
        const linkedMortId =
          typeof cfg.linked_mortgage_id === "string" ? cfg.linked_mortgage_id : null;
        const linkedMort = portfolioQuery.data?.debts.find((d) => d.id === linkedMortId);
        if (linkedMort) {
          setReMortBal(linkedMort.balance);
          setReMortRate(num(linkedMort.config?.annual_rate_pct, 17.1));
          setReMortConv((linkedMort.config?.rate_convention as RateConvention) || "CO_EA");
          setReMortMonths(num(linkedMort.config?.remaining_months, 226));
          setReMortIns(num(linkedMort.config?.monthly_insurance, 64_344));
        }
        setReResult(null);
      } else {
        setInvInitial(selectedAccount.balance);
        setInvType((cfg.investment_type as InvestmentType) || "us_equity_etf");
        setInvReturn(num(cfg.annual_rate_pct, 9.0));
        setInvConv((cfg.rate_convention as RateConvention) || "CO_EA");
        setInvYears(num(cfg.horizon_years, 10));
        setInvMonthly(num(cfg.monthly_contribution, 0));
        setInvFee(num(cfg.annual_fee_pct, 0.1));
        setInvInflation(num(cfg.annual_inflation_pct, 5.0));
        setInvTax(num(cfg.tax_on_gains_pct, 15.0));
        setInvFxDrift(num(cfg.annual_fx_drift_pct, 0.0));
        setInvResult(null);
      }
    });
  }, [selectedAccount, portfolioQuery.data]);

  const currency = selectedAccount?.currency ?? "COP";

  const calcMutation = useMutation({
    mutationFn: async () => {
      if (activeTab === "debts") {
        const res = await computeLoanProjection({
          principal: loanPrincipal,
          annual_rate_pct: loanRate,
          rate_convention: loanConv,
          remaining_months: loanMonths,
          monthly_insurance: loanInsurance,
          extra_monthly_payment: loanExtraMonthly,
          extra_lump_sum: loanLumpSum,
          method: loanMethod,
          currency,
        });
        setLoanResult(res);
      } else if (activeTab === "credit_cards") {
        const res = await computeCreditCardProjection({
          balance: ccBalance,
          annual_rate_pct: ccRate,
          rate_convention: ccConv,
          monthly_payment: ccPayment,
          monthly_new_spend: ccNewSpend,
          handling_fee: ccFee,
          pay_in_one_installment: ccOneCuota,
          currency,
        });
        setCcResult(res);
      } else if (activeTab === "real_estate") {
        const res = await computeRealEstateProjection({
          current_value: reValue,
          annual_appreciation_pct: reAppr,
          horizon_years: reYears,
          monthly_rent_income: reRent,
          occupancy_pct: reOcc,
          annual_rent_growth_pct: 5.0,
          monthly_hoa_and_maintenance: reHoa,
          annual_property_tax_pct: reTax,
          mortgage_balance: reMortBal,
          mortgage_annual_rate_pct: reMortRate,
          mortgage_rate_convention: reMortConv,
          mortgage_remaining_months: reMortMonths,
          mortgage_monthly_insurance: reMortIns,
          currency,
        });
        setReResult(res);
      } else {
        const res = await computeInvestmentProjection({
          initial_amount: invInitial,
          investment_type: invType,
          expected_annual_return_pct: invReturn,
          rate_convention: invConv,
          horizon_years: invYears,
          monthly_contribution: invMonthly,
          annual_fee_pct: invFee,
          annual_inflation_pct: invInflation,
          tax_on_gains_pct: invTax,
          annual_fx_drift_pct: invFxDrift,
          currency,
        });
        setInvResult(res);
      }
    },
    onError: (err) => {
      toast.error(formatApiError(err, "Projection calculation failed."));
    },
  });

  const saveConfigMutation = useMutation({
    mutationFn: async () => {
      if (!selectedAccount) return;
      const cfg =
        activeTab === "debts"
          ? {
              rate_convention: loanConv,
              annual_rate_pct: loanRate,
              remaining_months: loanMonths,
              monthly_insurance: loanInsurance,
              extra_monthly_payment: loanExtraMonthly,
            }
          : activeTab === "credit_cards"
            ? {
                rate_convention: ccConv,
                annual_rate_pct: ccRate,
                monthly_payment: ccPayment,
                pay_in_one_installment: ccOneCuota,
              }
            : activeTab === "real_estate"
              ? {
                  annual_appreciation_pct: reAppr,
                  horizon_years: reYears,
                  monthly_rent_income: reRent,
                  occupancy_pct: reOcc,
                  monthly_hoa_and_maintenance: reHoa,
                  annual_property_tax_pct: reTax,
                }
              : {
                  investment_type: invType,
                  rate_convention: invConv,
                  annual_rate_pct: invReturn,
                  horizon_years: invYears,
                  monthly_contribution: invMonthly,
                  annual_fee_pct: invFee,
                  annual_inflation_pct: invInflation,
                  tax_on_gains_pct: invTax,
                  annual_fx_drift_pct: invFxDrift,
                };
      await saveAccountProjectionConfig(selectedAccount.id, cfg);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["projections-portfolio"] });
      toast.success("Rates & assumptions saved for this account.");
    },
    onError: (err) => {
      toast.error(formatApiError(err, "Could not save configuration."));
    },
  });

  const projectionAi = useScopedAIToggle();

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6 pb-10">
      {/* Obsidian hero header */}
      <header className="relative overflow-hidden rounded-2xl bg-[#04090c] p-6 text-white">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -top-24 -right-20 size-72 rounded-full bg-emerald-500/20 blur-3xl"
        />
        <div className="relative flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-2xl space-y-1.5">
            <h1 className="text-2xl font-semibold tracking-tight text-white">
              Projections &amp; Amortization
            </h1>
            <p className="text-sm text-slate-300">
              Model Colombian EA and USA APR/APY schedules across your real loans, credit cards,
              real estate equity, and investments — with configurable rates, insurance, extra
              payments, inflation, FX drift, and taxes.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <ScopedAITrigger
              open={projectionAi.open}
              panelId={projectionAi.panelId}
              onToggle={projectionAi.toggle}
              compact={false}
              tone="dark"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={!selectedAccount || saveConfigMutation.isPending}
              onClick={() => {
                saveConfigMutation.mutate();
              }}
              className="border-white/20 bg-white/5 text-white hover:bg-white/15"
            >
              <Save aria-hidden="true" className="mr-1.5 size-4" />
              Save assumptions
            </Button>
            <Button
              type="button"
              size="sm"
              disabled={calcMutation.isPending}
              onClick={() => {
                calcMutation.mutate();
              }}
              className="bg-emerald-500 text-slate-950 hover:bg-emerald-400"
            >
              <Calculator aria-hidden="true" className="mr-1.5 size-4" />
              {calcMutation.isPending ? "Calculating…" : "Run projection"}
            </Button>
          </div>
        </div>

        {/* Domain tabs */}
        <div
          role="tablist"
          aria-label="Projection domains"
          className="relative mt-5 flex flex-wrap gap-2"
        >
          {(
            [
              { id: "debts", label: "Debts & Loans", icon: Landmark },
              { id: "credit_cards", label: "Credit Cards", icon: CreditCard },
              { id: "real_estate", label: "Real Estate", icon: Building2 },
              { id: "investments", label: "Investments", icon: TrendingUp },
            ] as const
          ).map((t) => {
            const Icon = t.icon;
            const active = activeTab === t.id;
            return (
              <button
                key={t.id}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => {
                  setActiveTab(t.id);
                  setSelectedId("");
                }}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-medium transition-colors",
                  active
                    ? "bg-emerald-500 text-slate-950"
                    : "bg-white/10 text-slate-200 hover:bg-white/15",
                )}
              >
                <Icon aria-hidden="true" className="size-3.5" />
                {t.label}
              </button>
            );
          })}
        </div>
      </header>

      <ScopedAIPanel
        id={projectionAi.panelId}
        open={projectionAi.open}
        onClose={projectionAi.close}
        module="projections"
        view={activeTab}
        control="projection-workspace"
        title={`Projections · ${activeTab}`}
        currency={selectedAccount?.currency}
        surfaceContext={{
          active_tab: activeTab,
          selected_account: selectedAccount
            ? {
                name: selectedAccount.name,
                kind: selectedAccount.account_kind,
                balance: selectedAccount.balance,
                currency: selectedAccount.currency,
              }
            : null,
          loan_inputs:
            activeTab === "debts"
              ? {
                  principal: loanPrincipal,
                  rate: loanRate,
                  convention: loanConv,
                  months: loanMonths,
                  extra_monthly: loanExtraMonthly,
                }
              : undefined,
          credit_card_inputs:
            activeTab === "credit_cards"
              ? { balance: ccBalance, rate: ccRate, payment: ccPayment }
              : undefined,
          real_estate_inputs:
            activeTab === "real_estate"
              ? { value: reValue, appr_pct: reAppr, years: reYears, mortgage_balance: reMortBal }
              : undefined,
          investment_inputs:
            activeTab === "investments"
              ? { initial: invInitial, type: invType, return_pct: invReturn, years: invYears }
              : undefined,
        }}
        suggestedPrompts={
          locale === "es-CO"
            ? [
                "Analiza esta proyección e identifica sus principales riesgos u oportunidades.",
                "¿Qué pasa si aumento el aporte mensual o cambio el plazo aquí?",
              ]
            : [
                "Analyze this projection scenario and highlight key risks and levers.",
                "How should I weigh extra payments vs. inflation or liquidity here?",
              ]
        }
      />

      {/* Account selector + Parameter workbench */}
      <section className="space-y-4 rounded-2xl border border-border bg-card p-5">
        <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-4">
          <div className="w-full max-w-md space-y-1.5">
            <Label htmlFor="projection-account-select" className="text-xs">
              Select account from your ledger
            </Label>
            <NativeSelect
              id="projection-account-select"
              value={selectedAccount?.id ?? ""}
              onChange={(e) => {
                setSelectedId(e.target.value);
              }}
            >
              {activeItems.map((acc) => (
                <option key={acc.id} value={acc.id}>
                  {acc.name} — {formatMoney(acc.balance, acc.currency)}
                </option>
              ))}
            </NativeSelect>
          </div>
          {selectedAccount ? (
            <p className="text-xs text-muted-foreground tabular-nums">
              Current ledger balance:{" "}
              <span className="font-semibold text-foreground">
                {formatMoney(selectedAccount.balance, selectedAccount.currency)}
              </span>
            </p>
          ) : null}
        </div>

        {/* DEBTS INPUTS */}
        {activeTab === "debts" ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-1">
              <Label className="text-xs">Principal ({currency})</Label>
              <Input
                type="number"
                value={loanPrincipal}
                onChange={(e) => setLoanPrincipal(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Interest convention</Label>
              <NativeSelect
                value={loanConv}
                onChange={(e) => setLoanConv(e.target.value as RateConvention)}
              >
                {RATE_CONVENTIONS.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </NativeSelect>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Annual / MV rate (%)</Label>
              <Input
                type="number"
                step="0.01"
                value={loanRate}
                onChange={(e) => setLoanRate(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Remaining months</Label>
              <Input
                type="number"
                min={1}
                max={480}
                value={loanMonths}
                onChange={(e) => setLoanMonths(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Monthly insurance ({currency})</Label>
              <Input
                type="number"
                value={loanInsurance}
                onChange={(e) => setLoanInsurance(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Extra monthly payment (abono)</Label>
              <Input
                type="number"
                value={loanExtraMonthly}
                onChange={(e) => setLoanExtraMonthly(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">One-time lump sum (month 1)</Label>
              <Input
                type="number"
                value={loanLumpSum}
                onChange={(e) => setLoanLumpSum(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Amortization method</Label>
              <NativeSelect
                value={loanMethod}
                onChange={(e) => setLoanMethod(e.target.value as AmortizationMethod)}
              >
                <option value="french_fixed">French (Fixed cuota)</option>
                <option value="german_constant_principal">German (Fixed capital)</option>
              </NativeSelect>
            </div>
          </div>
        ) : null}

        {/* CREDIT CARD INPUTS */}
        {activeTab === "credit_cards" ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-1">
              <Label className="text-xs">Current balance ({currency})</Label>
              <Input
                type="number"
                value={ccBalance}
                onChange={(e) => setCcBalance(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Rate convention</Label>
              <NativeSelect
                value={ccConv}
                onChange={(e) => setCcConv(e.target.value as RateConvention)}
              >
                {RATE_CONVENTIONS.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </NativeSelect>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Interest rate (%)</Label>
              <Input
                type="number"
                step="0.01"
                value={ccRate}
                onChange={(e) => setCcRate(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Monthly payment ({currency})</Label>
              <Input
                type="number"
                value={ccPayment}
                onChange={(e) => setCcPayment(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Monthly new spend</Label>
              <Input
                type="number"
                value={ccNewSpend}
                onChange={(e) => setCcNewSpend(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Handling fee (cuota de manejo)</Label>
              <Input
                type="number"
                value={ccFee}
                onChange={(e) => setCcFee(Number(e.target.value))}
              />
            </div>
            <label className="flex items-center gap-2 self-end rounded-lg border border-border bg-muted/20 px-3 py-2 text-xs sm:col-span-2">
              <input
                type="checkbox"
                className="size-4 accent-emerald-600"
                checked={ccOneCuota}
                onChange={(e) => setCcOneCuota(e.target.checked)}
              />
              <span>Paid in 1 cuota (0% interest — Colombia cashflow mode)</span>
            </label>
          </div>
        ) : null}

        {/* REAL ESTATE INPUTS */}
        {activeTab === "real_estate" ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-1">
              <Label className="text-xs">Property value ({currency})</Label>
              <Input
                type="number"
                value={reValue}
                onChange={(e) => setReValue(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Annual appreciation (%)</Label>
              <Input
                type="number"
                step="0.1"
                value={reAppr}
                onChange={(e) => setReAppr(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Horizon (years)</Label>
              <Input
                type="number"
                min={1}
                max={30}
                value={reYears}
                onChange={(e) => setReYears(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Monthly gross rent</Label>
              <Input
                type="number"
                value={reRent}
                onChange={(e) => setReRent(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Occupancy (%)</Label>
              <Input
                type="number"
                min={0}
                max={100}
                value={reOcc}
                onChange={(e) => setReOcc(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Monthly HOA &amp; maintenance</Label>
              <Input
                type="number"
                value={reHoa}
                onChange={(e) => setReHoa(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Property tax (predial %/yr)</Label>
              <Input
                type="number"
                step="0.1"
                value={reTax}
                onChange={(e) => setReTax(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Linked mortgage balance</Label>
              <Input
                type="number"
                value={reMortBal}
                onChange={(e) => setReMortBal(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Mortgage rate (%)</Label>
              <Input
                type="number"
                step="0.01"
                value={reMortRate}
                onChange={(e) => setReMortRate(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Mortgage convention</Label>
              <NativeSelect
                value={reMortConv}
                onChange={(e) => setReMortConv(e.target.value as RateConvention)}
              >
                {RATE_CONVENTIONS.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </NativeSelect>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Mortgage months left</Label>
              <Input
                type="number"
                value={reMortMonths}
                onChange={(e) => setReMortMonths(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Mortgage monthly insurance</Label>
              <Input
                type="number"
                value={reMortIns}
                onChange={(e) => setReMortIns(Number(e.target.value))}
              />
            </div>
          </div>
        ) : null}

        {/* INVESTMENTS INPUTS */}
        {activeTab === "investments" ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <div className="space-y-1 lg:col-span-2">
              <Label className="text-xs">Investment type</Label>
              <NativeSelect
                value={invType}
                onChange={(e) => setInvType(e.target.value as InvestmentType)}
              >
                {INVESTMENT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </NativeSelect>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Initial capital ({currency})</Label>
              <Input
                type="number"
                value={invInitial}
                onChange={(e) => setInvInitial(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Rate convention</Label>
              <NativeSelect
                value={invConv}
                onChange={(e) => setInvConv(e.target.value as RateConvention)}
              >
                {RATE_CONVENTIONS.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </NativeSelect>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Expected return (%)</Label>
              <Input
                type="number"
                step="0.1"
                value={invReturn}
                onChange={(e) => setInvReturn(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Horizon (years)</Label>
              <Input
                type="number"
                min={1}
                max={40}
                value={invYears}
                onChange={(e) => setInvYears(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Monthly contribution</Label>
              <Input
                type="number"
                value={invMonthly}
                onChange={(e) => setInvMonthly(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Annual fee / TER (%)</Label>
              <Input
                type="number"
                step="0.05"
                value={invFee}
                onChange={(e) => setInvFee(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Inflation (% / yr)</Label>
              <Input
                type="number"
                step="0.1"
                value={invInflation}
                onChange={(e) => setInvInflation(Number(e.target.value))}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Tax on gains (%) &amp; FX drift (%)</Label>
              <div className="flex gap-1.5">
                <Input
                  type="number"
                  step="0.5"
                  value={invTax}
                  onChange={(e) => setInvTax(Number(e.target.value))}
                  aria-label="Tax on gains %"
                />
                <Input
                  type="number"
                  step="0.5"
                  value={invFxDrift}
                  onChange={(e) => setInvFxDrift(Number(e.target.value))}
                  aria-label="FX drift %"
                />
              </div>
            </div>
          </div>
        ) : null}
      </section>

      {/* LOAN RESULTS */}
      {activeTab === "debts" && loanResult ? (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-border bg-card p-4">
              <p className="text-xs text-muted-foreground">Monthly outflow (incl. insurance)</p>
              <p className="mt-1 text-lg font-bold tabular-nums">
                {formatMoney(loanResult.total_monthly_outflow, loanResult.currency)}
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                MV {loanResult.monthly_rate_pct}% · EA {loanResult.effective_annual_rate_pct}%
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              <p className="text-xs text-muted-foreground">Total interest</p>
              <p className="mt-1 text-lg font-bold tabular-nums text-rose-700 dark:text-rose-400">
                {formatMoney(loanResult.total_interest, loanResult.currency)}
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Insurance: {formatMoney(loanResult.total_insurance, loanResult.currency)}
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              <p className="text-xs text-muted-foreground">Payoff horizon</p>
              <p className="mt-1 text-lg font-bold tabular-nums">
                {loanResult.payoff_months} months
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Final: {loanResult.schedule[loanResult.schedule.length - 1]?.payment_date ?? "—"}
              </p>
            </div>
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4">
              <p className="text-xs text-emerald-900/75 dark:text-emerald-200/75">
                Savings from extra payments
              </p>
              <p className="mt-1 text-lg font-bold tabular-nums text-emerald-800 dark:text-emerald-300">
                {formatMoney(loanResult.interest_saved_vs_baseline, loanResult.currency)}
              </p>
              <p className="mt-0.5 text-xs text-emerald-900/75 dark:text-emerald-200/75">
                {loanResult.months_saved_vs_baseline} months faster
              </p>
            </div>
          </div>

          <div className="max-h-[28rem] overflow-auto rounded-xl border border-border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>#</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-right">Opening</TableHead>
                  <TableHead className="text-right">Principal</TableHead>
                  <TableHead className="text-right">Interest</TableHead>
                  <TableHead className="text-right">Insurance</TableHead>
                  <TableHead className="text-right">Total Outflow</TableHead>
                  <TableHead className="text-right">Closing</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loanResult.schedule.map((r) => (
                  <TableRow key={r.month}>
                    <TableCell className="tabular-nums text-muted-foreground">{r.month}</TableCell>
                    <TableCell className="tabular-nums">{r.payment_date}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatMoney(r.opening_balance, loanResult.currency)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-emerald-700 dark:text-emerald-400">
                      {formatMoney(r.principal_paid, loanResult.currency)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-rose-700 dark:text-rose-400">
                      {formatMoney(r.interest_paid, loanResult.currency)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">
                      {formatMoney(r.insurance_paid, loanResult.currency)}
                    </TableCell>
                    <TableCell className="text-right font-medium tabular-nums">
                      {formatMoney(r.total_outflow, loanResult.currency)}
                    </TableCell>
                    <TableCell className="text-right font-semibold tabular-nums">
                      {formatMoney(r.closing_balance, loanResult.currency)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      ) : null}

      {/* CREDIT CARD RESULTS */}
      {activeTab === "credit_cards" && ccResult ? (
        <div className="space-y-4">
          {ccResult.warning ? (
            <p
              role="alert"
              className="rounded-xl border border-amber-500/35 bg-amber-500/10 px-4 py-3 text-sm text-amber-900 dark:text-amber-200"
            >
              {ccResult.warning}
            </p>
          ) : null}
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-border bg-card p-4">
              <p className="text-xs text-muted-foreground">Months to payoff</p>
              <p className="mt-1 text-lg font-bold tabular-nums">
                {ccResult.months_to_payoff ?? "Never"}
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                MV {ccResult.monthly_rate_pct}% · EA {ccResult.effective_annual_rate_pct}%
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              <p className="text-xs text-muted-foreground">Total interest &amp; fees</p>
              <p className="mt-1 text-lg font-bold tabular-nums text-rose-700 dark:text-rose-400">
                {formatMoney(ccResult.total_interest + ccResult.total_fees, ccResult.currency)}
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              <p className="text-xs text-muted-foreground">Total paid</p>
              <p className="mt-1 text-lg font-bold tabular-nums">
                {formatMoney(ccResult.total_paid, ccResult.currency)}
              </p>
            </div>
          </div>

          <div className="max-h-96 overflow-auto rounded-xl border border-border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>#</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-right">Opening</TableHead>
                  <TableHead className="text-right">Interest</TableHead>
                  <TableHead className="text-right">Payment</TableHead>
                  <TableHead className="text-right">Closing</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {ccResult.schedule.map((r) => (
                  <TableRow key={r.month}>
                    <TableCell className="tabular-nums text-muted-foreground">{r.month}</TableCell>
                    <TableCell className="tabular-nums">{r.payment_date}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatMoney(r.opening_balance, ccResult.currency)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-rose-700 dark:text-rose-400">
                      {formatMoney(r.interest_charged, ccResult.currency)}
                    </TableCell>
                    <TableCell className="text-right font-medium tabular-nums">
                      {formatMoney(r.payment, ccResult.currency)}
                    </TableCell>
                    <TableCell className="text-right font-semibold tabular-nums">
                      {formatMoney(r.closing_balance, ccResult.currency)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      ) : null}

      {/* REAL ESTATE RESULTS */}
      {activeTab === "real_estate" && reResult ? (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-border bg-card p-4">
              <p className="text-xs text-muted-foreground">Projected property value</p>
              <p className="mt-1 text-lg font-bold tabular-nums">
                {formatMoney(reResult.projected_property_value, reResult.currency)}
              </p>
            </div>
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4">
              <p className="text-xs text-emerald-900/75 dark:text-emerald-200/75">
                Projected net equity
              </p>
              <p className="mt-1 text-lg font-bold tabular-nums text-emerald-800 dark:text-emerald-300">
                {formatMoney(reResult.projected_net_equity, reResult.currency)}
              </p>
              <p className="mt-0.5 text-xs text-emerald-900/75 dark:text-emerald-200/75">
                Current: {formatMoney(reResult.current_net_equity, reResult.currency)}
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              <p className="text-xs text-muted-foreground">Gross yield / Cap rate</p>
              <p className="mt-1 text-lg font-bold tabular-nums">
                {reResult.gross_rental_yield_pct}% / {reResult.cap_rate_pct}%
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              <p className="text-xs text-muted-foreground">Cumulative net cashflow</p>
              <p className="mt-1 text-lg font-bold tabular-nums">
                {formatMoney(reResult.cumulative_net_cashflow, reResult.currency)}
              </p>
            </div>
          </div>

          <div className="overflow-auto rounded-xl border border-border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Year</TableHead>
                  <TableHead className="text-right">Property Value</TableHead>
                  <TableHead className="text-right">Mortgage</TableHead>
                  <TableHead className="text-right">Net Equity</TableHead>
                  <TableHead className="text-right">Annual Rent</TableHead>
                  <TableHead className="text-right">Net Cashflow</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reResult.schedule.map((r) => (
                  <TableRow key={r.year}>
                    <TableCell className="font-medium tabular-nums">Year {r.year}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatMoney(r.property_value, reResult.currency)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-rose-700 dark:text-rose-400">
                      {formatMoney(r.mortgage_balance, reResult.currency)}
                    </TableCell>
                    <TableCell className="text-right font-semibold tabular-nums text-emerald-700 dark:text-emerald-400">
                      {formatMoney(r.net_equity, reResult.currency)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatMoney(r.annual_gross_rent, reResult.currency)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatMoney(r.annual_net_cashflow, reResult.currency)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      ) : null}

      {/* INVESTMENT RESULTS */}
      {activeTab === "investments" && invResult ? (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4">
              <p className="text-xs text-emerald-900/75 dark:text-emerald-200/75">
                After-tax future value
              </p>
              <p className="mt-1 text-lg font-bold tabular-nums text-emerald-800 dark:text-emerald-300">
                {formatMoney(invResult.final_after_tax_value, invResult.currency)}
              </p>
              <p className="mt-0.5 text-xs text-emerald-900/75 dark:text-emerald-200/75">
                Net CAGR: {invResult.effective_net_annual_pct}%
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              <p className="text-xs text-muted-foreground">Inflation-adjusted (real)</p>
              <p className="mt-1 text-lg font-bold tabular-nums">
                {formatMoney(invResult.final_real_value, invResult.currency)}
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              <p className="text-xs text-muted-foreground">Total contributed</p>
              <p className="mt-1 text-lg font-bold tabular-nums">
                {formatMoney(invResult.total_contributed, invResult.currency)}
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              <p className="text-xs text-muted-foreground">Estimated tax on gains</p>
              <p className="mt-1 text-lg font-bold tabular-nums text-amber-700 dark:text-amber-400">
                {formatMoney(invResult.estimated_tax, invResult.currency)}
              </p>
            </div>
          </div>

          <div className="overflow-auto rounded-xl border border-border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Year</TableHead>
                  <TableHead className="text-right">Contributed</TableHead>
                  <TableHead className="text-right">Gross Value</TableHead>
                  <TableHead className="text-right">Real Value</TableHead>
                  <TableHead className="text-right">After-Tax Value</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invResult.schedule.map((r) => (
                  <TableRow key={r.year}>
                    <TableCell className="font-medium tabular-nums">Year {r.year}</TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">
                      {formatMoney(r.contributed, invResult.currency)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatMoney(r.gross_value, invResult.currency)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatMoney(r.real_value, invResult.currency)}
                    </TableCell>
                    <TableCell className="text-right font-semibold tabular-nums text-emerald-700 dark:text-emerald-400">
                      {formatMoney(r.after_tax_value, invResult.currency)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      ) : null}
    </div>
  );
}

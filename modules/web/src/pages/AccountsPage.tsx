import { useQuery } from "@tanstack/react-query";
import { ArrowLeftRight, Eye } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { accountsListQueryOptions } from "@/api/queries";
import { ScopedAIPanel, ScopedAITrigger, useScopedAIToggle } from "@/components/ai/ScopedAICopilot";
import { AccountFormDialog } from "@/components/accounts/AccountFormDialog";
import { QueryState } from "@/components/QueryState";
import {
  SortableTableHead,
  sortItems,
  toggleSort,
  type SortState,
} from "@/components/table/SortableTableHead";
import { DEFAULT_PAGE_SIZE, TablePagination } from "@/components/table/TablePagination";
import { ActionIconButton } from "@/components/ui/action-icon-button";
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
import { useLocale } from "@/i18n/LocaleProvider";
import { formatMoney } from "@/lib/formatMoney";
import { formatSlugLabel } from "@/lib/formatSlugLabel";

type AccountSortKey = "name" | "kind" | "side" | "balance" | "status";

type AccountFilters = {
  search: string;
  account_kind: string;
  ledger_side: string;
  status: string;
};

const EMPTY_FILTERS: AccountFilters = {
  search: "",
  account_kind: "",
  ledger_side: "",
  status: "",
};

const ACCOUNT_KIND_OPTIONS = [
  "checking",
  "savings",
  "cash",
  "investment_brokerage",
  "real_estate",
  "credit_card",
  "loan_mortgage",
  "other_asset",
  "other_liability",
] as const;

export function AccountsPage() {
  const { locale, messages } = useLocale();
  const at = messages.accounts;
  const accountsAi = useScopedAIToggle();
  const [createOpen, setCreateOpen] = useState(false);
  const [filters, setFilters] = useState<AccountFilters>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(DEFAULT_PAGE_SIZE);
  const [sort, setSort] = useState<SortState<AccountSortKey>>({ key: "name", direction: "asc" });

  function updateFilters(updater: (prev: AccountFilters) => AccountFilters) {
    setFilters(updater);
    setPage(1);
  }

  const hasSearch = filters.search.trim() !== "";
  const listParams = useMemo(
    () => ({
      limit: hasSearch ? 100 : pageSize,
      skip: hasSearch ? 0 : (page - 1) * pageSize,
      ...(filters.account_kind ? { account_kind: filters.account_kind } : {}),
      ...(filters.ledger_side ? { ledger_side: filters.ledger_side } : {}),
      ...(filters.status === "active"
        ? { is_active: true }
        : filters.status === "inactive"
          ? { is_active: false }
          : {}),
    }),
    [filters.account_kind, filters.ledger_side, filters.status, hasSearch, page, pageSize],
  );

  const listQuery = useQuery(accountsListQueryOptions(listParams));
  const rawItems = listQuery.data?.items ?? [];

  const filteredItems = useMemo(() => {
    const query = filters.search.trim().toLowerCase();
    if (!query) return rawItems;
    return rawItems.filter(
      (account) =>
        account.name.toLowerCase().includes(query) ||
        account.currency.toLowerCase().includes(query) ||
        formatSlugLabel(account.account_kind).toLowerCase().includes(query),
    );
  }, [rawItems, filters.search]);

  const sortedItems = useMemo(
    () =>
      sortItems(filteredItems, sort, {
        name: (a) => a.name,
        kind: (a) => a.account_kind,
        side: (a) => a.ledger_side,
        balance: (a) => a.balance,
        status: (a) => (a.is_active ? 1 : 0),
      }),
    [filteredItems, sort],
  );

  const displayItems = useMemo(() => {
    if (!hasSearch) return sortedItems;
    const start = (page - 1) * pageSize;
    return sortedItems.slice(start, start + pageSize);
  }, [hasSearch, page, pageSize, sortedItems]);

  const total = hasSearch ? sortedItems.length : (listQuery.data?.total ?? sortedItems.length);
  const hasActiveFilters = Object.values(filters).some((value) => value.trim() !== "");

  const kindLabel = (kind: string) => at.kinds[kind] ?? formatSlugLabel(kind);
  const sideLabel = (side: string) =>
    side === "asset" ? at.asset : side === "liability" ? at.liability : formatSlugLabel(side);

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-balance">{at.title}</h1>
          <p className="text-sm text-muted-foreground text-pretty">{at.subtitle}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ScopedAITrigger
            open={accountsAi.open}
            panelId={accountsAi.panelId}
            onToggle={accountsAi.toggle}
            compact={false}
          />
          <Button
            type="button"
            onClick={() => {
              setCreateOpen(true);
            }}
          >
            {at.newAccount}
          </Button>
        </div>
      </header>

      <ScopedAIPanel
        id={accountsAi.panelId}
        open={accountsAi.open}
        onClose={accountsAi.close}
        module="accounts"
        view="list"
        control="accounts-table"
        title={at.title}
        surfaceContext={{
          total_matching: total,
          filters,
          sort,
          visible_accounts: displayItems.slice(0, 12).map((a) => ({
            name: a.name,
            kind: a.account_kind,
            side: a.ledger_side,
            currency: a.currency,
            balance: a.balance,
            is_active: a.is_active,
          })),
        }}
        suggestedPrompts={
          locale === "es-CO"
            ? [
                "Resume mis saldos y concentración por tipo de cuenta.",
                "¿Qué cuentas activas tienen mayor peso en pasivos o liquidez?",
              ]
            : [
                "Summarize balances and concentration across my visible accounts.",
                "Which accounts carry the highest liquidity or debt concentration?",
              ]
        }
      />

      <div className="grid gap-3 rounded-2xl border border-border bg-card p-4 shadow-xs sm:grid-cols-2 lg:grid-cols-5">
        <div className="space-y-1.5 lg:col-span-2">
          <Label htmlFor="accounts-filter-search">{at.searchLabel}</Label>
          <Input
            id="accounts-filter-search"
            placeholder={at.searchPlaceholder}
            value={filters.search}
            onChange={(event) => {
              updateFilters((prev) => ({ ...prev, search: event.target.value }));
            }}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="accounts-filter-kind">{at.kindLabel}</Label>
          <NativeSelect
            id="accounts-filter-kind"
            value={filters.account_kind}
            onChange={(event) => {
              updateFilters((prev) => ({ ...prev, account_kind: event.target.value }));
            }}
          >
            <option value="">{at.allKinds}</option>
            {ACCOUNT_KIND_OPTIONS.map((kind) => (
              <option key={kind} value={kind}>
                {kindLabel(kind)}
              </option>
            ))}
          </NativeSelect>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="accounts-filter-side">{at.sideLabel}</Label>
          <NativeSelect
            id="accounts-filter-side"
            value={filters.ledger_side}
            onChange={(event) => {
              updateFilters((prev) => ({ ...prev, ledger_side: event.target.value }));
            }}
          >
            <option value="">{at.allSides}</option>
            <option value="asset">{at.assets}</option>
            <option value="liability">{at.liabilities}</option>
          </NativeSelect>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="accounts-filter-status">{at.statusLabel}</Label>
          <div className="flex items-center gap-2">
            <NativeSelect
              id="accounts-filter-status"
              value={filters.status}
              onChange={(event) => {
                updateFilters((prev) => ({ ...prev, status: event.target.value }));
              }}
            >
              <option value="">{at.allStatuses}</option>
              <option value="active">{at.active}</option>
              <option value="inactive">{at.inactive}</option>
            </NativeSelect>
            {hasActiveFilters ? (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  updateFilters(() => EMPTY_FILTERS);
                }}
              >
                {at.clear}
              </Button>
            ) : null}
          </div>
        </div>
      </div>

      <QueryState
        isPending={listQuery.isPending}
        isError={listQuery.isError}
        error={listQuery.error}
        isEmpty={!listQuery.isPending && !listQuery.isError && displayItems.length === 0}
        emptyTitle={hasActiveFilters ? at.emptyFilteredTitle : at.emptyTitle}
        emptyDescription={hasActiveFilters ? at.emptyFilteredDescription : at.emptyDescription}
        emptyAction={
          hasActiveFilters ? (
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                updateFilters(() => EMPTY_FILTERS);
              }}
            >
              {at.clearFilters}
            </Button>
          ) : (
            <Button
              type="button"
              onClick={() => {
                setCreateOpen(true);
              }}
            >
              {at.createFirst}
            </Button>
          )
        }
        onRetry={() => {
          void listQuery.refetch();
        }}
      >
        <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-xs">
          <Table>
            <TableHeader>
              <TableRow>
                <SortableTableHead
                  label={at.colName}
                  sortKey="name"
                  sort={sort}
                  onSort={(key) => {
                    setSort((prev) => toggleSort(prev, key));
                  }}
                />
                <SortableTableHead
                  label={at.colKind}
                  sortKey="kind"
                  sort={sort}
                  onSort={(key) => {
                    setSort((prev) => toggleSort(prev, key));
                  }}
                />
                <SortableTableHead
                  label={at.colSide}
                  sortKey="side"
                  sort={sort}
                  onSort={(key) => {
                    setSort((prev) => toggleSort(prev, key));
                  }}
                />
                <SortableTableHead
                  label={at.colBalance}
                  sortKey="balance"
                  sort={sort}
                  align="right"
                  onSort={(key) => {
                    setSort((prev) => toggleSort(prev, key, "desc"));
                  }}
                />
                <SortableTableHead
                  label={at.colStatus}
                  sortKey="status"
                  sort={sort}
                  onSort={(key) => {
                    setSort((prev) => toggleSort(prev, key, "desc"));
                  }}
                />
                <TableHead className="text-right">{at.colActions}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {displayItems.map((account) => (
                <TableRow key={account.id}>
                  <TableCell>
                    <Link
                      to={`/accounts/${account.id}`}
                      className="font-medium text-primary underline-offset-4 hover:underline"
                    >
                      {account.name}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {kindLabel(account.account_kind)}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {sideLabel(account.ledger_side)}
                  </TableCell>
                  <TableCell className="text-right font-medium tabular-nums">
                    {formatMoney(account.balance, account.currency)}
                  </TableCell>
                  <TableCell>
                    <span
                      className={
                        account.is_active
                          ? "inline-flex rounded-full bg-success-soft px-2.5 py-0.5 text-xs font-medium text-success"
                          : "inline-flex rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground"
                      }
                    >
                      {account.is_active ? at.active : at.inactive}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1.5">
                      <ActionIconButton
                        icon={Eye}
                        label={at.viewDetails}
                        tone="sky"
                        to={`/accounts/${account.id}`}
                      />
                      <ActionIconButton
                        icon={ArrowLeftRight}
                        label={at.viewTransactions}
                        tone="emerald"
                        to={`/transactions?search=${encodeURIComponent(account.name)}`}
                      />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <TablePagination
            page={page}
            pageSize={pageSize}
            total={total}
            visibleCount={displayItems.length}
            onPageChange={setPage}
            onPageSizeChange={(nextSize) => {
              setPageSize(nextSize);
              setPage(1);
            }}
          />
        </div>
      </QueryState>

      <AccountFormDialog open={createOpen} onOpenChange={setCreateOpen} mode="create" />
    </div>
  );
}

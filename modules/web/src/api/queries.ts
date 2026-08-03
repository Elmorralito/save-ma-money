import { queryOptions } from "@tanstack/react-query";

import { getAccount, listAccounts, type ListAccountsParams } from "@/api/accounts";
import { getCategory, listCategories, type ListCategoriesParams } from "@/api/categories";
import { getHealth, getHealthLive } from "@/api/health";
import { getClientContract } from "@/api/meta";
import { queryKeys } from "@/api/queryKeys";

/** Shared query definition for PPT-044 client-contract discovery. */
export function clientContractQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.meta.clientContract(),
    queryFn: ({ signal }) => getClientContract(signal).then((result) => result.contract),
  });
}

/** Shared query definition for aggregate API health. */
export function healthQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.health.root(),
    queryFn: ({ signal }) => getHealth(signal),
  });
}

/** Shared query definition for liveness (no DB/Auth/Redis). */
export function healthLiveQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.health.live(),
    queryFn: ({ signal }) => getHealthLive(signal),
  });
}

function accountsListFilters(
  params: Omit<ListAccountsParams, "signal">,
): Record<string, string | number | boolean | undefined> {
  return {
    account_kind: params.account_kind,
    ledger_side: params.ledger_side,
    is_active: params.is_active,
    skip: params.skip,
    limit: params.limit,
  };
}

function categoriesListFilters(
  params: Omit<ListCategoriesParams, "signal">,
): Record<string, string | number | boolean | undefined> {
  return {
    parent_id: params.parent_id,
    category_type: params.category_type,
    skip: params.skip,
    limit: params.limit,
  };
}

/** Shared query definition for paginated accounts list. */
export function accountsListQueryOptions(params: Omit<ListAccountsParams, "signal"> = {}) {
  return queryOptions({
    queryKey: queryKeys.accounts.list(accountsListFilters(params)),
    queryFn: ({ signal }) => listAccounts({ ...params, signal }),
  });
}

/** Shared query definition for a single account. */
export function accountDetailQueryOptions(accountId: string) {
  return queryOptions({
    queryKey: queryKeys.accounts.detail(accountId),
    queryFn: ({ signal }) => getAccount(accountId, signal),
    enabled: accountId.length > 0,
  });
}

/** Shared query definition for paginated categories list. */
export function categoriesListQueryOptions(params: Omit<ListCategoriesParams, "signal"> = {}) {
  return queryOptions({
    queryKey: queryKeys.categories.list(categoriesListFilters(params)),
    queryFn: ({ signal }) => listCategories({ ...params, signal }),
  });
}

/** Shared query definition for a single category. */
export function categoryDetailQueryOptions(categoryId: string) {
  return queryOptions({
    queryKey: queryKeys.categories.detail(categoryId),
    queryFn: ({ signal }) => getCategory(categoryId, signal),
    enabled: categoryId.length > 0,
  });
}

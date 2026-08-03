/**
 * Hierarchical TanStack Query key factory (PPT-048).
 *
 * Keep keys stable and serializable. Feature screens (#117+) extend this factory —
 * do not invent ad-hoc string keys in components.
 */
export const queryKeys = {
  all: ["papita"] as const,
  auth: {
    all: ["papita", "auth"] as const,
    session: () => ["papita", "auth", "session"] as const,
  },
  meta: {
    all: ["papita", "meta"] as const,
    clientContract: () => ["papita", "meta", "client-contract"] as const,
  },
  health: {
    all: ["papita", "health"] as const,
    root: () => ["papita", "health", "root"] as const,
    live: () => ["papita", "health", "live"] as const,
  },
  accounts: {
    all: ["papita", "accounts"] as const,
    lists: () => ["papita", "accounts", "list"] as const,
    list: (filters: Record<string, string | number | boolean | undefined>) =>
      ["papita", "accounts", "list", filters] as const,
    details: () => ["papita", "accounts", "detail"] as const,
    detail: (accountId: string) => ["papita", "accounts", "detail", accountId] as const,
  },
  categories: {
    all: ["papita", "categories"] as const,
    lists: () => ["papita", "categories", "list"] as const,
    list: (filters: Record<string, string | number | boolean | undefined>) =>
      ["papita", "categories", "list", filters] as const,
    details: () => ["papita", "categories", "detail"] as const,
    detail: (categoryId: string) => ["papita", "categories", "detail", categoryId] as const,
  },
} as const;

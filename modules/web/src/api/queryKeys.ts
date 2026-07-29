/**
 * Hierarchical TanStack Query key factory (PPT-048).
 *
 * Keep keys stable and serializable. Feature screens (#117+) extend this factory —
 * do not invent ad-hoc string keys in components.
 */
export const queryKeys = {
  all: ["papita"] as const,
  meta: {
    all: ["papita", "meta"] as const,
    clientContract: () => ["papita", "meta", "client-contract"] as const,
  },
  health: {
    all: ["papita", "health"] as const,
    root: () => ["papita", "health", "root"] as const,
    live: () => ["papita", "health", "live"] as const,
  },
} as const;

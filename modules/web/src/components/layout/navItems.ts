export type AppNavItem = {
  to: string;
  label: string;
};

/** Primary authenticated navigation (accounts/categories: PPT-052; txns/movements: PPT-053). */
export const APP_NAV_ITEMS: readonly AppNavItem[] = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/accounts", label: "Accounts" },
  { to: "/categories", label: "Categories" },
  { to: "/transactions", label: "Transactions" },
  { to: "/movements", label: "Movements" },
  { to: "/reports", label: "Reports" },
] as const;

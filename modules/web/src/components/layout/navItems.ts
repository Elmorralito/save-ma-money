export type AppNavItem = {
  to: string;
  label: string;
};

/** Primary authenticated navigation (feature screens stubbed until PPT-052+). */
export const APP_NAV_ITEMS: readonly AppNavItem[] = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/accounts", label: "Accounts" },
  { to: "/categories", label: "Categories" },
  { to: "/transactions", label: "Transactions" },
  { to: "/movements", label: "Movements" },
  { to: "/reports", label: "Reports" },
] as const;

export type AppNavItem = {
  to: string;
  label: string;
};

/** Primary authenticated navigation (accounts/categories: PPT-052; unified ledger: PPT-099; dues: PPT-074). */
export const APP_NAV_ITEMS: readonly AppNavItem[] = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/accounts", label: "Accounts" },
  { to: "/categories", label: "Categories" },
  { to: "/transactions", label: "Transactions" },
  { to: "/payment-dues", label: "Payment dues" },
  { to: "/reports", label: "Reports" },
  { to: "/projections", label: "Projections" },
  { to: "/settings", label: "Settings" },
] as const;

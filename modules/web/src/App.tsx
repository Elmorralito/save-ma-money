import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthRedirectBridge } from "@/auth/AuthRedirectBridge";
import { RequireAuth } from "@/auth/RequireAuth";
import { BreakingChangesGuard } from "@/components/contract/BreakingChangesGuard";
import { AppLayout } from "@/components/layout/AppLayout";
import { PublicLayout } from "@/components/layout/PublicLayout";

const LoginPage = lazy(async () => {
  const mod = await import("@/pages/LoginPage");
  return { default: mod.LoginPage };
});
const RegisterPage = lazy(async () => {
  const mod = await import("@/pages/RegisterPage");
  return { default: mod.RegisterPage };
});
const CheckEmailPage = lazy(async () => {
  const mod = await import("@/pages/CheckEmailPage");
  return { default: mod.CheckEmailPage };
});
const ConfirmEmailPage = lazy(async () => {
  const mod = await import("@/pages/ConfirmEmailPage");
  return { default: mod.ConfirmEmailPage };
});
const DashboardPage = lazy(async () => {
  const mod = await import("@/pages/DashboardPage");
  return { default: mod.DashboardPage };
});
const AccountsPage = lazy(async () => {
  const mod = await import("@/pages/AccountsPage");
  return { default: mod.AccountsPage };
});
const AccountDetailPage = lazy(async () => {
  const mod = await import("@/pages/AccountDetailPage");
  return { default: mod.AccountDetailPage };
});
const CategoriesPage = lazy(async () => {
  const mod = await import("@/pages/CategoriesPage");
  return { default: mod.CategoriesPage };
});
const TransactionsPage = lazy(async () => {
  const mod = await import("@/pages/TransactionsPage");
  return { default: mod.TransactionsPage };
});
const MovementsPage = lazy(async () => {
  const mod = await import("@/pages/MovementsPage");
  return { default: mod.MovementsPage };
});
const ReportsPage = lazy(async () => {
  const mod = await import("@/pages/ReportsPage");
  return { default: mod.ReportsPage };
});

function RouteFallback() {
  return (
    <div className="flex min-h-40 items-center justify-center text-sm text-muted-foreground">
      Loading…
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <BreakingChangesGuard />
      <AuthRedirectBridge />
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route element={<PublicLayout />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/check-email" element={<CheckEmailPage />} />
            <Route path="/auth/confirm" element={<ConfirmEmailPage />} />
          </Route>

          <Route
            element={
              <RequireAuth>
                <AppLayout />
              </RequireAuth>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/accounts" element={<AccountsPage />} />
            <Route path="/accounts/:accountId" element={<AccountDetailPage />} />
            <Route path="/categories" element={<CategoriesPage />} />
            <Route path="/transactions" element={<TransactionsPage />} />
            <Route path="/movements" element={<MovementsPage />} />
            <Route path="/reports" element={<ReportsPage />} />
          </Route>

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;

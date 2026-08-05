import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as authApi from "@/api/auth";
import { PapitaApiError } from "@/api/errors";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { QueryTestProvider } from "@/test/queryWrapper";

vi.mock("@/api/auth", () => ({
  getBffSession: vi.fn(),
  bffLogin: vi.fn(),
  bffLogout: vi.fn(),
  bffRegister: vi.fn(),
  bffRefresh: vi.fn(),
  bffResendConfirmation: vi.fn(),
}));

const emptyDiscovery = {
  breakingChanges: null,
  bulkMax: null,
  reportWindowMaxDays: null,
  cashFlowRefreshDefault: null,
  reportsForeignAccountStatus: null,
  errorCode: null,
  compatActive: [] as string[],
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("RegisterPage", () => {
  beforeEach(() => {
    vi.mocked(authApi.getBffSession).mockResolvedValue({
      authenticated: false,
      user: null,
      csrf_token: null,
      session_backend: "memory",
      access_expires_at: null,
    });
  });

  it("requires matching passwords and toggles visibility", async () => {
    const user = userEvent.setup();
    render(
      <QueryTestProvider>
        <MemoryRouter>
          <RegisterPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await user.type(screen.getByLabelText("Email"), "a@example.com");
    await user.type(screen.getByLabelText("Password"), "SecurePass1!");
    await user.type(screen.getByLabelText("Confirm password"), "Different1!");
    await user.click(screen.getByRole("button", { name: "Register" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Passwords do not match");
    expect(authApi.bffRegister).not.toHaveBeenCalled();

    const showButtons = screen.getAllByRole("button", { name: "Show password" });
    expect(showButtons.length).toBe(2);
    await user.click(showButtons[0]!);
    expect(screen.getByLabelText("Password")).toHaveAttribute("type", "text");
  });

  it("registers then shows the login registered banner when confirmation is not required", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.bffRegister).mockResolvedValue({
      id: "11111111-1111-1111-1111-111111111111",
      username: "alice01",
      email: "a@example.com",
      display_name: null,
      phone: null,
      provider: "email",
      auth_provider: "supabase",
      created_at: "2026-07-30T00:00:00Z",
      email_confirmation_required: false,
    });

    render(
      <QueryTestProvider>
        <MemoryRouter initialEntries={["/register"]}>
          <Routes>
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/login" element={<LoginPage />} />
          </Routes>
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await user.type(screen.getByLabelText("Email"), "a@example.com");
    await user.type(screen.getByLabelText("Password"), "SecurePass1!");
    await user.type(screen.getByLabelText("Confirm password"), "SecurePass1!");
    await user.click(screen.getByRole("button", { name: "Register" }));

    await waitFor(() => {
      expect(authApi.bffRegister).toHaveBeenCalled();
    });
    expect(await screen.findByRole("status")).toHaveTextContent(/Account created/i);
  });

  it("registers then shows check-email when confirmation is required", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.bffRegister).mockResolvedValue({
      id: "11111111-1111-1111-1111-111111111111",
      username: "alice01",
      email: "a@example.com",
      display_name: null,
      phone: null,
      provider: "email",
      auth_provider: "supabase",
      created_at: "2026-07-30T00:00:00Z",
      email_confirmation_required: true,
    });

    const { CheckEmailPage } = await import("@/pages/CheckEmailPage");

    render(
      <QueryTestProvider>
        <MemoryRouter initialEntries={["/register"]}>
          <Routes>
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/check-email" element={<CheckEmailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await user.type(screen.getByLabelText("Email"), "a@example.com");
    await user.type(screen.getByLabelText("Password"), "SecurePass1!");
    await user.type(screen.getByLabelText("Confirm password"), "SecurePass1!");
    await user.click(screen.getByRole("button", { name: "Register" }));

    await waitFor(() => {
      expect(authApi.bffRegister).toHaveBeenCalled();
    });
    expect(await screen.findByRole("heading", { name: /Check your email/i })).toBeInTheDocument();
    expect(screen.getByText(/a@example.com/i)).toBeInTheDocument();
  });

  it("surfaces auth 429 with Retry-After in an alert (not silent)", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.bffRegister).mockRejectedValue(
      new PapitaApiError({
        message: "Email rate limit exceeded. Wait a few minutes, or use local Admin register.",
        status: 429,
        discovery: emptyDiscovery,
        retryAfter: 60,
      }),
    );

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <RegisterPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await user.type(screen.getByLabelText("Email"), "a@example.com");
    await user.type(screen.getByLabelText("Password"), "SecurePass1!");
    await user.type(screen.getByLabelText("Confirm password"), "SecurePass1!");
    await user.click(screen.getByRole("button", { name: "Register" }));

    await waitFor(() => {
      expect(authApi.bffRegister).toHaveBeenCalled();
    });
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/rate limit/i);
    expect(alert).toHaveTextContent(/Retry after 60s/);
  });
});

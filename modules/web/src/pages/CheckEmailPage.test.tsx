import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as authApi from "@/api/auth";
import { PapitaApiError } from "@/api/errors";
import { CheckEmailPage } from "@/pages/CheckEmailPage";
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

describe("CheckEmailPage", () => {
  it("shows pending confirmation copy with email from location state", () => {
    render(
      <QueryTestProvider>
        <MemoryRouter
          initialEntries={[{ pathname: "/check-email", state: { email: "a@example.com" } }]}
        >
          <Routes>
            <Route path="/check-email" element={<CheckEmailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryTestProvider>,
    );

    expect(screen.getByRole("heading", { name: /Check your email/i })).toBeInTheDocument();
    expect(screen.getByText(/No session is opened/i)).toBeInTheDocument();
    expect(screen.getByText(/a@example.com/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Sign in/i })).toHaveAttribute("href", "/login");
  });

  it("resends confirmation email for the pending address", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.bffResendConfirmation).mockResolvedValue(undefined);

    render(
      <QueryTestProvider>
        <MemoryRouter
          initialEntries={[{ pathname: "/check-email", state: { email: "a@example.com" } }]}
        >
          <Routes>
            <Route path="/check-email" element={<CheckEmailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await user.click(screen.getByRole("button", { name: /Resend confirmation email/i }));
    await waitFor(() => {
      expect(authApi.bffResendConfirmation).toHaveBeenCalled();
    });
    expect(vi.mocked(authApi.bffResendConfirmation).mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({
        email: "a@example.com",
      }),
    );
    expect(await screen.findByText(/sent another email/i)).toBeInTheDocument();
  });

  it("surfaces resend 429 in an alert", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.bffResendConfirmation).mockRejectedValue(
      new PapitaApiError({
        message: "Email rate limit exceeded. Wait a few minutes, or use local Admin register.",
        status: 429,
        discovery: emptyDiscovery,
        retryAfter: 60,
      }),
    );

    render(
      <QueryTestProvider>
        <MemoryRouter
          initialEntries={[{ pathname: "/check-email", state: { email: "a@example.com" } }]}
        >
          <Routes>
            <Route path="/check-email" element={<CheckEmailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await user.click(screen.getByRole("button", { name: /Resend confirmation email/i }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/rate limit/i);
  });
});

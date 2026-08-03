import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as authApi from "@/api/auth";
import { PapitaApiError } from "@/api/errors";
import { LoginPage } from "@/pages/LoginPage";
import { QueryTestProvider } from "@/test/queryWrapper";

vi.mock("@/api/auth", () => ({
  getBffSession: vi.fn(),
  bffLogin: vi.fn(),
  bffLogout: vi.fn(),
  bffRegister: vi.fn(),
  bffRefresh: vi.fn(),
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

describe("LoginPage", () => {
  beforeEach(() => {
    vi.mocked(authApi.getBffSession).mockResolvedValue({
      authenticated: false,
      user: null,
      csrf_token: null,
      session_backend: "memory",
    });
  });

  it("surfaces auth 429 with Retry-After in an alert (not silent)", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.bffLogin).mockRejectedValue(
      new PapitaApiError({
        message: "Too many authentication attempts. Try again later.",
        status: 429,
        discovery: emptyDiscovery,
        retryAfter: 30,
      }),
    );

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await user.type(screen.getByLabelText("Email"), "a@example.com");
    await user.type(screen.getByLabelText("Password"), "SecurePass1!");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(authApi.bffLogin).toHaveBeenCalled();
    });
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/Too many authentication attempts/i);
    expect(alert).toHaveTextContent(/Retry after 30s/);
  });

  it("surfaces Email not confirmed via formatApiError", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.bffLogin).mockRejectedValue(
      new PapitaApiError({
        message: "Email not confirmed",
        status: 401,
        discovery: emptyDiscovery,
      }),
    );

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await user.type(screen.getByLabelText("Email"), "a@example.com");
    await user.type(screen.getByLabelText("Password"), "SecurePass1!");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/Confirm your email/i);
  });
});

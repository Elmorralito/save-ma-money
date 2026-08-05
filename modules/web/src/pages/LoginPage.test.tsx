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
  bffResendConfirmation: vi.fn(),
  bffOAuthStartUrl: (provider: string, returnTo = "/dashboard") =>
    `/api/v1/bff/auth/oauth/${provider}?return_to=${encodeURIComponent(returnTo)}`,
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
      access_expires_at: null,
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
        code: "email_not_confirmed",
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
    expect(screen.getByRole("button", { name: /Resend confirmation email/i })).toBeInTheDocument();
  });

  it("shows email-confirmed banner after /auth/confirm handoff", () => {
    render(
      <QueryTestProvider>
        <MemoryRouter initialEntries={[{ pathname: "/login", state: { emailConfirmed: true } }]}>
          <LoginPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    expect(screen.getByRole("status")).toHaveTextContent(/Email confirmed/i);
  });

  it("resends confirmation from the unconfirmed login CTA", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.bffLogin).mockRejectedValue(
      new PapitaApiError({
        message: "Email not confirmed",
        status: 401,
        code: "email_not_confirmed",
        discovery: emptyDiscovery,
      }),
    );
    vi.mocked(authApi.bffResendConfirmation).mockResolvedValue(undefined);

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
    await screen.findByRole("button", { name: /Resend confirmation email/i });
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

  it("offers Google and GitHub OAuth buttons that navigate to BFF start URLs", async () => {
    const assign = vi.fn();
    vi.stubGlobal("location", { ...window.location, assign });

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /Continue with Google/i }));
    expect(assign).toHaveBeenCalledWith("/api/v1/bff/auth/oauth/google?return_to=%2Fdashboard");

    assign.mockClear();
    await user.click(screen.getByRole("button", { name: /Continue with GitHub/i }));
    expect(assign).toHaveBeenCalledWith("/api/v1/bff/auth/oauth/github?return_to=%2Fdashboard");

    vi.unstubAllGlobals();
  });

  it("surfaces oauth_error query as an alert", async () => {
    render(
      <QueryTestProvider>
        <MemoryRouter initialEntries={["/login?oauth_error=1"]}>
          <LoginPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(/Social sign-in failed/i);
  });
});

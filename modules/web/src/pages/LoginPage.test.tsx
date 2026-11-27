import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as authApi from "@/api/auth";
import { LoginPage } from "@/pages/LoginPage";
import { QueryTestProvider } from "@/test/queryWrapper";

vi.mock("@/api/auth", () => ({
  getBffSession: vi.fn(),
  bffOAuthStartUrl: (provider: string, returnTo = "/dashboard") =>
    `/api/v1/auth/oauth/${provider}?follow=true&return_to=${encodeURIComponent(returnTo)}`,
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("LoginPage (Google-only OAuth)", () => {
  beforeEach(() => {
    vi.mocked(authApi.getBffSession).mockResolvedValue({
      authenticated: false,
      user: null,
      csrf_token: null,
      session_backend: "bearer",
      access_expires_at: null,
    });
  });

  it("offers only Google OAuth sign-in without password form or GitHub", async () => {
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
    expect(assign).toHaveBeenCalledWith(
      "/api/v1/auth/oauth/google?follow=true&return_to=%2Fdashboard",
    );
    expect(screen.queryByRole("button", { name: /Continue with GitHub/i })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();

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

    expect(await screen.findByRole("alert")).toHaveTextContent(/Google sign-in failed/i);
  });
});

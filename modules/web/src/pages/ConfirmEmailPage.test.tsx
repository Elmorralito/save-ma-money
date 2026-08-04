import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import { interpretEmailConfirmParams } from "@/auth/emailConfirmLanding";
import { ConfirmEmailPage } from "@/pages/ConfirmEmailPage";

afterEach(() => {
  cleanup();
});

describe("interpretEmailConfirmParams", () => {
  it("maps error query params to failure copy", () => {
    const result = interpretEmailConfirmParams({
      search: "?error=access_denied&error_description=Link+expired",
      hash: "",
    });
    expect(result.status).toBe("error");
    expect(result.message).toMatch(/Link expired/i);
  });

  it("treats signup type and token_hash as success", () => {
    const result = interpretEmailConfirmParams({
      search: "?type=signup&token_hash=abc",
      hash: "",
    });
    expect(result.status).toBe("success");
    expect(result.discardedSessionFragment).toBe(false);
  });

  it("ignores access_token hash fragments without storing them", () => {
    const result = interpretEmailConfirmParams({
      search: "",
      hash: "#access_token=secret&refresh_token=also-secret&type=signup",
    });
    expect(result.status).toBe("success");
    expect(result.discardedSessionFragment).toBe(true);
    expect(result.message).not.toContain("secret");
  });
});

describe("ConfirmEmailPage", () => {
  it("renders success landing and link to login", () => {
    render(
      <MemoryRouter initialEntries={["/auth/confirm?type=signup&token_hash=abc"]}>
        <Routes>
          <Route path="/auth/confirm" element={<ConfirmEmailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: /Email confirmed/i })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/confirmed/i);
    expect(screen.getByRole("link", { name: /Continue to sign in/i })).toHaveAttribute(
      "href",
      "/login",
    );
  });

  it("renders error landing from query params", () => {
    render(
      <MemoryRouter initialEntries={["/auth/confirm?error_description=Link%20expired"]}>
        <Routes>
          <Route path="/auth/confirm" element={<ConfirmEmailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: /Confirmation failed/i })).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/Link expired/i);
  });
});

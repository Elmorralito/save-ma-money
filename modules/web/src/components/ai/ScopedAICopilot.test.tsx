import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as aiApi from "@/api/ai";
import { ScopedAIPanel, ScopedAITrigger, useScopedAIToggle } from "@/components/ai/ScopedAICopilot";
import { LocaleProvider } from "@/i18n/LocaleProvider";
import { QueryTestProvider } from "@/test/queryWrapper";

vi.mock("@/api/ai", () => ({
  getAIStatus: vi.fn(),
  getAIConfig: vi.fn(),
  updateAIConfig: vi.fn(),
  sendAIChat: vi.fn(),
}));

function TestHarness({
  initialOpen = false,
  suggestedPrompts = ["Summarize this table"],
}: {
  initialOpen?: boolean;
  suggestedPrompts?: string[];
}) {
  const ai = useScopedAIToggle(initialOpen);
  return (
    <div>
      <ScopedAITrigger open={ai.open} panelId={ai.panelId} onToggle={ai.toggle} />
      <ScopedAIPanel
        id={ai.panelId}
        open={ai.open}
        onClose={ai.close}
        module="reports"
        view="waterfall"
        control="bucket-breakdown-table"
        title="Bucket Breakdown"
        currency="COP"
        surfaceContext={{ currency: "COP", rows_count: 4 }}
        suggestedPrompts={suggestedPrompts}
      />
    </div>
  );
}

function renderHarness(initialOpen = false) {
  return render(
    <QueryTestProvider>
      <LocaleProvider>
        <MemoryRouter>
          <TestHarness initialOpen={initialOpen} />
        </MemoryRouter>
      </LocaleProvider>
    </QueryTestProvider>,
  );
}

beforeEach(() => {
  vi.mocked(aiApi.getAIStatus).mockResolvedValue({
    enabled: true,
    available: true,
    provider: "cli:agy",
    model: "sonnet",
    default_connection: "cli:agy",
    connections: [{ id: "cli:agy", kind: "cli", provider: "agy", model: "sonnet", ready: true }],
    single_owner_enforced: true,
  });
  vi.mocked(aiApi.getAIConfig).mockResolvedValue({
    enabled: true,
    mode: "sidecar",
    default_connection: "cli:agy",
    model: null,
    base_url: null,
    include_financial_context_by_default: true,
    reports_ai_enabled: true,
    payment_dues_ai_enabled: true,
    cli_permission_granted: true,
    lan_permission_granted: false,
    api_permission_granted: false,
    has_api_key: false,
    api_key_hint: null,
  });
  vi.mocked(aiApi.sendAIChat).mockResolvedValue({
    reply: "Fixed expenses represent 42% of outflows.",
    connection: "cli:agy",
    kind: "cli",
    provider: "agy",
    model: "sonnet",
    context_included: true,
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ScopedAICopilot", () => {
  it("expands in place and forwards scoped module, view, control, and surfaceContext", async () => {
    const user = userEvent.setup();
    renderHarness(false);

    const trigger = screen.getByRole("button", { name: /Analyze with AI/i });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("region")).not.toBeInTheDocument();

    await user.click(trigger);

    expect(trigger).toHaveAttribute("aria-expanded", "true");
    const region = await screen.findByRole("region", { name: /Contextual AI: Bucket Breakdown/i });
    expect(region).toHaveTextContent("reports / waterfall / bucket-breakdown-table");

    await user.click(screen.getByRole("button", { name: "Summarize this table" }));

    await waitFor(() => {
      expect(aiApi.sendAIChat).toHaveBeenCalledWith(
        expect.objectContaining({
          prompt: "Summarize this table",
          module: "reports",
          view: "waterfall",
          control: "bucket-breakdown-table",
          currency: "COP",
          surface_context: { currency: "COP", rows_count: 4 },
        }),
      );
    });
    expect(
      await screen.findByText("Fixed expenses represent 42% of outflows."),
    ).toBeInTheDocument();
  });

  it("shows configuration guidance linking to Settings when AI is disabled", async () => {
    vi.mocked(aiApi.getAIStatus).mockResolvedValue({
      enabled: false,
      available: false,
      provider: null,
      model: null,
      default_connection: null,
      connections: [],
      single_owner_enforced: true,
    });
    vi.mocked(aiApi.getAIConfig).mockResolvedValue({
      enabled: false,
      mode: "sidecar",
      default_connection: "cli:agy",
      model: null,
      base_url: null,
      include_financial_context_by_default: true,
      reports_ai_enabled: true,
      payment_dues_ai_enabled: true,
      cli_permission_granted: false,
      lan_permission_granted: false,
      api_permission_granted: false,
      has_api_key: false,
      api_key_hint: null,
    });

    renderHarness(true);

    expect(await screen.findByText("AI integration is disabled")).toBeInTheDocument();
    const settingsLinks = screen.getAllByRole("link", { name: /Configure in Settings/i });
    expect(settingsLinks.length).toBeGreaterThanOrEqual(1);
    for (const link of settingsLinks) {
      expect(link).toHaveAttribute("href", "/settings?tab=ai");
    }
  });
});

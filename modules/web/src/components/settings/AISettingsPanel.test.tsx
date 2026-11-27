import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as aiApi from "@/api/ai";
import { AISettingsPanel } from "@/components/settings/AISettingsPanel";
import { QueryTestProvider } from "@/test/queryWrapper";

vi.mock("@/api/ai", () => ({
  getAIStatus: vi.fn(),
  getAIConfig: vi.fn(),
  updateAIConfig: vi.fn(),
  fetchAIModels: vi.fn(),
  sendAIChat: vi.fn(),
}));

beforeEach(() => {
  vi.mocked(aiApi.getAIStatus).mockResolvedValue({
    enabled: true,
    available: true,
    provider: "cli:agy",
    model: "agy",
    default_connection: "cli:agy",
    connections: [{ id: "cli:agy", kind: "cli", provider: "cli:agy", model: "agy", ready: true }],
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
    cli_permission_granted: false,
    lan_permission_granted: false,
    api_permission_granted: false,
    has_api_key: false,
    api_key_hint: null,
  });
  vi.mocked(aiApi.fetchAIModels).mockResolvedValue({
    connection: "cli:agy",
    mode: "sidecar",
    ready: true,
    source: "live",
    models: [
      { id: "gemini-4-neon-medium", label: "Gemini 4 Neon (Medium)" },
      { id: "claude-sonnet-5-5-medium", label: "Claude Sonnet 5.5 (Medium)" },
    ],
    default_model: "gemini-4-neon-medium",
  });
  vi.mocked(aiApi.updateAIConfig).mockImplementation(async (payload) => ({
    enabled: true,
    mode: payload.mode ?? "sidecar",
    default_connection: payload.default_connection ?? "cli:agy",
    model: payload.model ?? null,
    base_url: payload.base_url ?? null,
    include_financial_context_by_default: payload.include_financial_context_by_default ?? true,
    reports_ai_enabled: payload.reports_ai_enabled ?? true,
    payment_dues_ai_enabled: payload.payment_dues_ai_enabled ?? true,
    cli_permission_granted: payload.cli_permission_granted ?? false,
    lan_permission_granted: payload.lan_permission_granted ?? false,
    api_permission_granted: payload.api_permission_granted ?? false,
    has_api_key: false,
    api_key_hint: null,
  }));
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("AISettingsPanel", () => {
  it("requires permission before connecting, loads model dropdown, and saves exact model ID", async () => {
    const user = userEvent.setup();
    render(
      <QueryTestProvider>
        <AISettingsPanel />
      </QueryTestProvider>,
    );

    const connectBtn = await screen.findByRole("button", { name: /Connect & load models/i });
    expect(connectBtn).toBeDisabled();

    await user.click(screen.getByRole("checkbox", { name: /Grant permission/i }));
    await user.click(
      await screen.findByRole("checkbox", { name: /I understand what might happen/i }),
    );
    await user.click(screen.getByRole("button", { name: /I understand — Allow CLI Access/i }));
    expect(connectBtn).toBeEnabled();

    await user.click(connectBtn);

    const modelSelect = await screen.findByRole("combobox", { name: /Exact Model ID/i });
    expect(modelSelect).toHaveValue("gemini-4-neon-medium");

    await user.selectOptions(modelSelect, "claude-sonnet-5-5-medium");
    await user.click(screen.getByRole("button", { name: /Save LLM settings/i }));

    await waitFor(() => {
      expect(aiApi.updateAIConfig).toHaveBeenCalledWith(
        expect.objectContaining({
          mode: "sidecar",
          default_connection: "cli:agy",
          model: "claude-sonnet-5-5-medium",
          cli_permission_granted: true,
        }),
      );
    });
  });

  it("supports connecting the built-in LAN Qwen Financial LoRA and selecting its exact model ID", async () => {
    const user = userEvent.setup();
    vi.mocked(aiApi.fetchAIModels).mockResolvedValueOnce({
      connection: "qwen_finance",
      mode: "lan_local",
      ready: true,
      source: "live",
      models: [
        { id: "qwen2.5-finance-lora", label: "qwen2.5-finance-lora" },
        { id: "qwen2.5-14b-instruct", label: "qwen2.5-14b-instruct" },
      ],
      default_model: "qwen2.5-finance-lora",
    });

    render(
      <QueryTestProvider>
        <AISettingsPanel />
      </QueryTestProvider>,
    );

    await user.click(await screen.findByRole("button", { name: /Built-in Model/i }));
    await user.click(screen.getByRole("checkbox", { name: /Grant permission/i }));
    await user.click(screen.getByRole("button", { name: /Connect & load models/i }));

    const modelSelect = await screen.findByRole("combobox", { name: /Exact Model ID/i });
    expect(modelSelect).toHaveValue("qwen2.5-finance-lora");

    await user.click(screen.getByRole("button", { name: /Save LLM settings/i }));
    await waitFor(() => {
      expect(aiApi.updateAIConfig).toHaveBeenCalledWith(
        expect.objectContaining({
          mode: "lan_local",
          default_connection: "qwen_finance",
          model: "qwen2.5-finance-lora",
          lan_permission_granted: true,
        }),
      );
    });
  });

  it("switches to Cloud APIs mode, loads provider models, and toggles copilot flags", async () => {
    const user = userEvent.setup();
    vi.mocked(aiApi.fetchAIModels).mockResolvedValueOnce({
      connection: "openai",
      mode: "api_key",
      ready: true,
      source: "live",
      models: [{ id: "gpt-4o-mini", label: "GPT-4o Mini" }],
      default_model: "gpt-4o-mini",
    });

    render(
      <QueryTestProvider>
        <AISettingsPanel />
      </QueryTestProvider>,
    );

    await user.click(await screen.findByRole("button", { name: /Direct Cloud API/i }));
    await user.click(screen.getByRole("checkbox", { name: /Grant permission/i }));
    await user.type(screen.getByLabelText(/API Key/i), "test-cloud-fixture");
    await user.click(screen.getByRole("button", { name: /Connect & load models/i }));

    await waitFor(() => {
      expect(aiApi.fetchAIModels).toHaveBeenCalledWith(
        expect.objectContaining({ mode: "api_key" }),
      );
    });
    for (const cb of screen.queryAllByRole("checkbox")) {
      fireEvent.click(cb);
    }
    const baseUrlInput = screen.queryByLabelText(/Base URL/i);
    if (baseUrlInput) {
      fireEvent.change(baseUrlInput, { target: { value: "https://api.openai.com/v1" } });
    }
  });
});

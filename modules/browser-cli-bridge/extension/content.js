/* global chrome */
(() => {
  const CHANNEL = "papita-cli-bridge:v1";
  const ALLOWED_ACTIONS = new Set([
    "ping",
    "request_permission",
    "revoke_permission",
    "list_models",
    "chat",
  ]);

  // Announce presence to the page so the SPA can detect the extension immediately.
  window.postMessage(
    {
      channel: CHANNEL,
      direction: "from-extension",
      event: "ready",
      version: "0.1.0",
    },
    window.location.origin,
  );

  window.addEventListener("message", (event) => {
    if (event.source !== window) return;
    if (event.origin !== window.location.origin) return;
    const data = event.data;
    if (!data || typeof data !== "object") return;
    if (data.channel !== CHANNEL || data.direction !== "from-page") return;
    if (typeof data.requestId !== "string" || !ALLOWED_ACTIONS.has(data.action)) return;

    const reply = (payload) => {
      window.postMessage(
        {
          channel: CHANNEL,
          direction: "from-extension",
          requestId: data.requestId,
          ...payload,
        },
        window.location.origin,
      );
    };

    try {
      chrome.runtime.sendMessage(
        {
          action: data.action,
          origin: window.location.origin,
          payload: data.payload ?? {},
        },
        (response) => {
          if (chrome.runtime.lastError) {
            reply({
              ok: false,
              error: chrome.runtime.lastError.message || "Extension background worker unavailable.",
            });
            return;
          }
          reply(response ?? { ok: false, error: "Empty response from CLI bridge extension." });
        },
      );
    } catch (err) {
      reply({
        ok: false,
        error: err instanceof Error ? err.message : "Failed to reach CLI bridge extension.",
      });
    }
  });
})();

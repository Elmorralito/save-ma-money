/* global chrome */

const NATIVE_HOST_NAME = "com.papita.cli_bridge";
const STORAGE_KEY = "approvedOrigins";

/** Pending consent prompts keyed by requestId -> { resolve, origin, cli, windowId }. */
const pendingConsents = new Map();

async function getApprovedOrigins() {
  const result = await chrome.storage.local.get(STORAGE_KEY);
  const map = result[STORAGE_KEY];
  return map && typeof map === "object" ? map : {};
}

async function isOriginApproved(origin) {
  const approved = await getApprovedOrigins();
  return Boolean(approved[origin]?.granted);
}

async function setOriginApproved(origin, granted, cli = null) {
  const approved = await getApprovedOrigins();
  if (granted) {
    approved[origin] = {
      granted: true,
      grantedAt: new Date().toISOString(),
      lastCli: cli,
    };
  } else {
    delete approved[origin];
  }
  await chrome.storage.local.set({ [STORAGE_KEY]: approved });
}

function sendNative(message) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendNativeMessage(NATIVE_HOST_NAME, message, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message || "Native messaging host unavailable."));
        return;
      }
      if (!response || typeof response !== "object") {
        reject(new Error("Empty response from native CLI host."));
        return;
      }
      resolve(response);
    });
  });
}

async function openConsentPrompt(origin, cli) {
  const consentId = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  const url = chrome.runtime.getURL(
    `consent.html?consentId=${encodeURIComponent(consentId)}&origin=${encodeURIComponent(origin)}&cli=${encodeURIComponent(cli || "cli:agy")}`,
  );

  return new Promise((resolve) => {
    pendingConsents.set(consentId, { resolve, origin, cli, windowId: null });
    chrome.windows.create(
      {
        url,
        type: "popup",
        width: 480,
        height: 540,
        focused: true,
      },
      (win) => {
        if (chrome.runtime.lastError || !win) {
          pendingConsents.delete(consentId);
          resolve({ granted: false, error: chrome.runtime.lastError?.message || "Could not open consent prompt." });
          return;
        }
        const entry = pendingConsents.get(consentId);
        if (entry) {
          entry.windowId = win.id ?? null;
        }
      },
    );
  });
}

chrome.windows.onRemoved.addListener((closedWindowId) => {
  for (const [consentId, entry] of pendingConsents.entries()) {
    if (entry.windowId === closedWindowId) {
      pendingConsents.delete(consentId);
      entry.resolve({ granted: false, reason: "closed" });
    }
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  (async () => {
    // Internal decision from consent.html
    if (message?.type === "consent_decision") {
      const entry = pendingConsents.get(message.consentId);
      if (!entry) {
        sendResponse({ ok: false });
        return;
      }
      pendingConsents.delete(message.consentId);
      const granted = Boolean(message.granted);
      if (granted) {
        await setOriginApproved(entry.origin, true, entry.cli);
      }
      entry.resolve({ granted });
      sendResponse({ ok: true });
      return;
    }

    // Internal popup actions
    if (message?.type === "popup_get_state") {
      const approved = await getApprovedOrigins();
      let nativeHealth = { ok: false, error: "Native host not registered." };
      try {
        nativeHealth = await sendNative({ action: "health" });
      } catch (err) {
        nativeHealth = { ok: false, error: err instanceof Error ? err.message : String(err) };
      }
      sendResponse({ ok: true, approved, nativeHealth });
      return;
    }

    if (message?.type === "popup_revoke_origin") {
      await setOriginApproved(String(message.origin || ""), false);
      sendResponse({ ok: true });
      return;
    }

    // Webpage bridge requests
    const origin = typeof message?.origin === "string" ? message.origin : "";
    const action = message?.action;
    const payload = message?.payload && typeof message.payload === "object" ? message.payload : {};

    if (!origin) {
      sendResponse({ ok: false, error: "Missing requesting origin." });
      return;
    }

    if (action === "ping") {
      const originGranted = await isOriginApproved(origin);
      let nativeHostReady = false;
      let clis = [];
      let nativeError = null;
      try {
        const health = await sendNative({ action: "health" });
        nativeHostReady = Boolean(health.ok);
        clis = Array.isArray(health.clis) ? health.clis : [];
        if (!nativeHostReady) {
          nativeError = health.error || "Native host reported not ready.";
        }
      } catch (err) {
        nativeError = err instanceof Error ? err.message : String(err);
      }
      sendResponse({
        ok: true,
        installed: true,
        version: "0.1.0",
        originGranted,
        nativeHostReady,
        nativeError,
        clis,
      });
      return;
    }

    if (action === "request_permission") {
      const cli = typeof payload.connection === "string" ? payload.connection : "cli:agy";
      const alreadyGranted = await isOriginApproved(origin);
      if (alreadyGranted && !payload.forcePrompt) {
        sendResponse({ ok: true, granted: true });
        return;
      }
      const decision = await openConsentPrompt(origin, cli);
      sendResponse({ ok: true, granted: Boolean(decision.granted), error: decision.error || null });
      return;
    }

    if (action === "revoke_permission") {
      await setOriginApproved(origin, false);
      sendResponse({ ok: true, granted: false });
      return;
    }

    // Protected native actions require explicit per-origin consent.
    const approved = await isOriginApproved(origin);
    if (!approved) {
      sendResponse({
        ok: false,
        code: "PERMISSION_REQUIRED",
        error: `Origin ${origin} has not been granted permission to run local CLIs. Click Grant permission first.`,
      });
      return;
    }

    if (action === "list_models") {
      try {
        const result = await sendNative({
          action: "list_models",
          connection: String(payload.connection || "cli:agy"),
        });
        sendResponse(result);
      } catch (err) {
        sendResponse({
          ok: false,
          error: err instanceof Error ? err.message : "Native host model discovery failed.",
        });
      }
      return;
    }

    if (action === "chat") {
      try {
        const result = await sendNative({
          action: "chat",
          connection: String(payload.connection || "cli:agy"),
          model: typeof payload.model === "string" ? payload.model : null,
          system_prompt: typeof payload.system_prompt === "string" ? payload.system_prompt : "",
          user_prompt: typeof payload.user_prompt === "string" ? payload.user_prompt : "",
        });
        sendResponse(result);
      } catch (err) {
        sendResponse({
          ok: false,
          error: err instanceof Error ? err.message : "Native host CLI execution failed.",
        });
      }
      return;
    }

    sendResponse({ ok: false, error: `Unknown bridge action: ${String(action)}` });
  })();

  return true;
});

/* global chrome */
(() => {
  const params = new URLSearchParams(window.location.search);
  const consentId = params.get("consentId") || "";
  const origin = params.get("origin") || "unknown";
  const cli = params.get("cli") || "cli:agy";

  const originEl = document.getElementById("origin-label");
  const cliEl = document.getElementById("cli-label");
  const ackCheckbox = document.getElementById("risk-ack");
  const allowBtn = document.getElementById("allow-btn");
  const denyBtn = document.getElementById("deny-btn");

  if (originEl) originEl.textContent = origin;
  if (cliEl) cliEl.textContent = cli;

  ackCheckbox?.addEventListener("change", () => {
    if (allowBtn) allowBtn.disabled = !ackCheckbox.checked;
  });

  function decide(granted) {
    chrome.runtime.sendMessage({ type: "consent_decision", consentId, granted }, () => {
      window.close();
    });
  }

  allowBtn?.addEventListener("click", () => decide(true));
  denyBtn?.addEventListener("click", () => decide(false));
})();

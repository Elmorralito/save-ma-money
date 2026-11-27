/* global chrome */
(() => {
  const hostStatusEl = document.getElementById("host-status");
  const cliListEl = document.getElementById("cli-list");
  const originsListEl = document.getElementById("origins-list");

  function refresh() {
    chrome.runtime.sendMessage({ type: "popup_get_state" }, (res) => {
      if (!res || !res.ok) {
        if (hostStatusEl) hostStatusEl.textContent = "Bridge worker unavailable.";
        return;
      }

      const health = res.nativeHealth || {};
      if (hostStatusEl) {
        hostStatusEl.innerHTML = health.ok
          ? '<span class="pill ok">Native host connected</span>'
          : `<span class="pill err">Native host not ready</span><div class="muted" style="margin-top:4px">${health.error || "Run install_native_host.sh"}</div>`;
      }

      if (cliListEl) {
        const clis = Array.isArray(health.clis) ? health.clis : [];
        if (clis.length === 0) {
          cliListEl.innerHTML = '<div class="muted">No CLI probe data yet.</div>';
        } else {
          cliListEl.innerHTML =
            "<strong>Detected local CLIs</strong>" +
            clis
              .map(
                (c) =>
                  `<div class="row"><code>${c.id}</code><span class="pill ${c.ready ? "ok" : "err"}">${c.ready ? "ready" : "missing"}</span></div>`,
              )
              .join("");
        }
      }

      if (originsListEl) {
        const origins = Object.keys(res.approved || {});
        if (origins.length === 0) {
          originsListEl.textContent = "None approved yet.";
        } else {
          originsListEl.innerHTML = "";
          for (const origin of origins) {
            const row = document.createElement("div");
            row.className = "row";
            const label = document.createElement("code");
            label.textContent = origin;
            const btn = document.createElement("button");
            btn.type = "button";
            btn.textContent = "Revoke";
            btn.addEventListener("click", () => {
              chrome.runtime.sendMessage({ type: "popup_revoke_origin", origin }, refresh);
            });
            row.append(label, btn);
            originsListEl.appendChild(row);
          }
        }
      }
    });
  }

  refresh();
})();

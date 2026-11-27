# Papita Local CLI Bridge (Browser Extension + Native Messaging)

Allows the Papita web app to request explicit browser-extension permission to run pinned local AI CLIs (`agy`, `claude`, `codex`, `cursor`) directly on your computer — without routing CLI execution through a backend server.

## How it works

1. **Webpage** (`@papita/web`) sends a `window.postMessage` request to the installed extension (`papita-cli-bridge:v1`).
2. **Extension** (`extension/background.js`) opens its own dedicated **risk-acknowledgment popup** (`consent.html`) outside the page DOM showing the requesting origin and security risks.
3. Once you approve, the extension calls Chrome/Firefox **Native Messaging** (`com.papita.cli_bridge`), which launches `native-host/papita_cli_host.py` on demand.
4. `papita_cli_host.py` executes only allowlisted CLI binaries (`agy`, `claude`, `codex`, `cursor`) with `shell=False`, scrubbed DB/OAuth env vars, and strict timeouts.

## 3-Step Setup

### 1. Load the browser extension
- Open `chrome://extensions` (or `brave://extensions`, `edge://extensions`).
- Enable **Developer mode**.
- Click **Load unpacked** and select `modules/browser-cli-bridge/extension/`.
- Copy the **Extension ID** shown on the card.

### 2. Register the Native Messaging host
```bash
./modules/browser-cli-bridge/native-host/install_native_host.sh <YOUR_EXTENSION_ID>
```

### 3. Grant permission in Papita
- Reload the Papita tab and open **Settings → AI & LLM → Local AI CLI**.
- Check **Grant permission** — the extension will open a native consent window where you can review the risks and click **Allow CLI Access**.
- Click **Connect & load models** or **Test connection** to run `agy` (or `claude`/`codex`/`cursor`) directly from your browser.

> You can revoke access at any time from the **Papita Local CLI Bridge** toolbar icon or by unchecking **Grant permission** in Settings.

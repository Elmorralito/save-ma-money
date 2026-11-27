#!/usr/bin/env bash
set -euo pipefail

# Register the Papita Local CLI Bridge Native Messaging host for Chrome/Chromium/Brave/Edge/Firefox.
#
# Usage:
#   ./install_native_host.sh <CHROME_EXTENSION_ID>
#
# Find <CHROME_EXTENSION_ID> on chrome://extensions after loading
# modules/browser-cli-bridge/extension/ as an unpacked extension.

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <CHROME_EXTENSION_ID>" >&2
  echo "Tip: Load modules/browser-cli-bridge/extension/ via chrome://extensions (Load unpacked) and copy its ID." >&2
  exit 1
fi

EXT_ID="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST_SCRIPT="${SCRIPT_DIR}/papita_cli_host.py"
HOST_NAME="com.papita.cli_bridge"

chmod +x "${HOST_SCRIPT}"

CHROME_MANIFEST="$(cat <<EOF
{
  "name": "${HOST_NAME}",
  "description": "Papita Local CLI Bridge Native Messaging Host",
  "path": "${HOST_SCRIPT}",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://${EXT_ID}/"
  ]
}
EOF
)"

FIREFOX_MANIFEST="$(cat <<EOF
{
  "name": "${HOST_NAME}",
  "description": "Papita Local CLI Bridge Native Messaging Host",
  "path": "${HOST_SCRIPT}",
  "type": "stdio",
  "allowed_extensions": [
    "papita-cli-bridge@papita.local"
  ]
}
EOF
)"

install_dir() {
  local target_dir="$1"
  local content="$2"
  mkdir -p "${target_dir}"
  printf '%s\n' "${content}" > "${target_dir}/${HOST_NAME}.json"
  echo "Installed ${target_dir}/${HOST_NAME}.json"
}

OS_NAME="$(uname -s)"
if [[ "${OS_NAME}" == "Darwin" ]]; then
  install_dir "${HOME}/Library/Application Support/Google/Chrome/NativeMessagingHosts" "${CHROME_MANIFEST}"
  install_dir "${HOME}/Library/Application Support/Chromium/NativeMessagingHosts" "${CHROME_MANIFEST}"
  install_dir "${HOME}/Library/Application Support/BraveSoftware/Brave-Browser/NativeMessagingHosts" "${CHROME_MANIFEST}"
  install_dir "${HOME}/Library/Application Support/Microsoft Edge/NativeMessagingHosts" "${CHROME_MANIFEST}"
  install_dir "${HOME}/Library/Application Support/Mozilla/NativeMessagingHosts" "${FIREFOX_MANIFEST}"
else
  install_dir "${HOME}/.config/google-chrome/NativeMessagingHosts" "${CHROME_MANIFEST}"
  install_dir "${HOME}/.config/chromium/NativeMessagingHosts" "${CHROME_MANIFEST}"
  install_dir "${HOME}/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts" "${CHROME_MANIFEST}"
  install_dir "${HOME}/.config/microsoft-edge/NativeMessagingHosts" "${CHROME_MANIFEST}"
  install_dir "${HOME}/.mozilla/native-messaging-hosts" "${FIREFOX_MANIFEST}"
fi

echo ""
echo "Done! Reload the Papita Local CLI Bridge extension in your browser, then click 'Grant permission' in Papita -> Settings -> AI & LLM."

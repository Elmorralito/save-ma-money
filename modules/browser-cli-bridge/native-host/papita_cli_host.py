#!/usr/bin/env python3
"""Chrome/Firefox Native Messaging host for Papita's Browser CLI Bridge.

Stdlib-only Python 3 script launched on demand by the browser when the user
explicitly grants the Papita Local CLI Bridge extension permission to run
pinned local AI CLIs (``agy``, ``claude``, ``codex``, ``cursor``).

Security boundaries:
- Strict CLI binary allowlist (no arbitrary shell commands).
- ``subprocess.run(..., shell=False)`` with scrubbed database/OAuth/JWT env vars.
- Bounded output (64 KiB) and strict timeouts.
"""

from __future__ import annotations

import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any

MAX_OUTPUT_BYTES = 65_536
DEFAULT_TIMEOUT_SECONDS = 90.0
SCRUBBED_ENV_PREFIXES = (
    "DATABASE_",
    "DB_",
    "JWT_",
    "SUPABASE_",
    "GMAIL_",
    "REDIS_",
    "AI_AGENT_SHARED_SECRET",
    "AWS_",
)

CLI_SPECS: dict[str, tuple[str, list[str]]] = {
    "agy": ("agy", ["--output-format", "text", "--disable-slash-commands", "-p"]),
    "claude": ("claude", ["-p", "--output-format", "text", "--tools", ""]),
    "codex": ("codex", ["exec", "--skip-git-repo-check"]),
    "cursor": ("cursor", ["agent", "--print"]),
}

CLI_MODEL_FLAGS: dict[str, str] = {
    "agy": "--model",
    "claude": "--model",
    "codex": "-m",
    "cursor": "--model",
}

CURATED_MODELS: dict[str, list[dict[str, str]]] = {
    "agy": [
        {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro"},
        {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash"},
    ],
    "claude": [
        {"id": "claude-sonnet-4-20250514", "label": "Claude Sonnet 4"},
        {"id": "claude-opus-4-20250514", "label": "Claude Opus 4"},
        {"id": "claude-3-7-sonnet-latest", "label": "Claude 3.7 Sonnet"},
        {"id": "claude-3-5-haiku-latest", "label": "Claude 3.5 Haiku"},
    ],
    "codex": [
        {"id": "o4-mini", "label": "OpenAI o4-mini"},
        {"id": "o3", "label": "OpenAI o3"},
        {"id": "gpt-5", "label": "OpenAI GPT-5"},
        {"id": "gpt-4.1", "label": "OpenAI GPT-4.1"},
        {"id": "gpt-4o", "label": "OpenAI GPT-4o"},
    ],
    "cursor": [
        {"id": "auto", "label": "Cursor Auto"},
        {"id": "claude-sonnet-4", "label": "Claude Sonnet 4"},
        {"id": "gpt-4.1", "label": "GPT-4.1"},
        {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro"},
    ],
}


def _scrubbed_env() -> dict[str, str]:
    env = {
        k: v for k, v in os.environ.items() if not any(k.upper().startswith(prefix) for prefix in SCRUBBED_ENV_PREFIXES)
    }
    # Chrome launches native hosts with a minimal PATH; augment with common user bin dirs.
    home = str(Path.home())
    extra_dirs = [
        os.path.join(home, ".local", "bin"),
        os.path.join(home, ".npm-global", "bin"),
        "/usr/local/bin",
        "/opt/homebrew/bin",
    ]
    current_path = env.get("PATH", "")
    parts = [p for p in current_path.split(os.pathsep) if p]
    for directory in extra_dirs:
        if directory not in parts and os.path.isdir(directory):
            parts.insert(0, directory)
    env["PATH"] = os.pathsep.join(parts)
    return env


def _normalize_cli_name(connection: str) -> str:
    cleaned = connection.strip().lower()
    if cleaned.startswith("cli:"):
        cleaned = cleaned.split(":", 1)[1]
    return cleaned


def resolve_binary(cli_name: str) -> str | None:
    if cli_name not in CLI_SPECS:
        return None
    binary, _args = CLI_SPECS[cli_name]
    env = _scrubbed_env()
    found = shutil.which(binary, path=env.get("PATH"))
    if found:
        return found
    local_bin = Path.home() / ".local" / "bin" / binary
    if local_bin.is_file() and os.access(local_bin, os.X_OK):
        return str(local_bin)
    return None


def build_cli_args(cli_name: str, model: str | None) -> list[str]:
    _bin, base_args = CLI_SPECS[cli_name]
    args = list(base_args)
    cleaned = (model or "").strip()
    if not cleaned or cleaned.lower() == "default":
        return args
    flag = CLI_MODEL_FLAGS.get(cli_name)
    if not flag:
        return args
    if cli_name == "agy" and "-p" in args:
        idx = args.index("-p")
        return [*args[:idx], flag, cleaned, *args[idx:]]
    return [*args, flag, cleaned]


def compose_prompt(system_prompt: str, user_prompt: str) -> str:
    if not system_prompt.strip():
        return user_prompt
    return f"{system_prompt.strip()}\n\nUser request:\n{user_prompt}"


def handle_health() -> dict[str, Any]:
    clis = []
    for cli_name in sorted(CLI_SPECS):
        binary = resolve_binary(cli_name)
        clis.append(
            {
                "id": f"cli:{cli_name}",
                "kind": "cli",
                "provider": f"cli:{cli_name}",
                "model": cli_name,
                "ready": binary is not None,
            }
        )
    return {"ok": True, "clis": clis}


def handle_list_models(connection: str) -> dict[str, Any]:
    cli_name = _normalize_cli_name(connection)
    if cli_name not in CLI_SPECS:
        return {"ok": False, "error": f"Unsupported CLI connection: {connection!r}"}
    resolved = resolve_binary(cli_name)
    if not resolved:
        return {
            "ok": True,
            "connection": f"cli:{cli_name}",
            "ready": False,
            "source": "curated",
            "models": [],
            "default_model": None,
        }

    if cli_name == "agy":
        try:
            proc = subprocess.run(
                [resolved, "models"],
                capture_output=True,
                timeout=15.0,
                env=_scrubbed_env(),
                check=False,
            )
            if proc.returncode == 0:
                discovered: list[dict[str, str]] = []
                for raw_line in proc.stdout.decode("utf-8", errors="replace").splitlines():
                    line = raw_line.strip()
                    if "\t" not in line:
                        continue
                    model_id, label = line.split("\t", 1)
                    model_id = model_id.strip()
                    label = label.strip() or model_id
                    if model_id:
                        discovered.append({"id": model_id, "label": label})
                if discovered:
                    return {
                        "ok": True,
                        "connection": "cli:agy",
                        "ready": True,
                        "source": "live",
                        "models": discovered,
                        "default_model": discovered[0]["id"],
                    }
        except (subprocess.TimeoutExpired, OSError):
            pass

    curated = list(CURATED_MODELS.get(cli_name, []))
    return {
        "ok": True,
        "connection": f"cli:{cli_name}",
        "ready": True,
        "source": "curated",
        "models": curated,
        "default_model": curated[0]["id"] if curated else None,
    }


def handle_chat(
    *,
    connection: str,
    model: str | None,
    system_prompt: str,
    user_prompt: str,
) -> dict[str, Any]:
    cli_name = _normalize_cli_name(connection)
    if cli_name not in CLI_SPECS:
        return {"ok": False, "error": f"Unsupported CLI connection: {connection!r}"}
    if not user_prompt.strip():
        return {"ok": False, "error": "Prompt must not be empty."}
    resolved = resolve_binary(cli_name)
    if not resolved:
        return {"ok": False, "error": f"Local CLI binary {cli_name!r} not found in PATH."}

    cli_args = build_cli_args(cli_name, model)
    combined = compose_prompt(system_prompt, user_prompt)
    try:
        proc = subprocess.run(
            [resolved, *cli_args, combined],
            capture_output=True,
            timeout=DEFAULT_TIMEOUT_SECONDS,
            env=_scrubbed_env(),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Local CLI {cli_name} timed out after {int(DEFAULT_TIMEOUT_SECONDS)}s."}
    except OSError as exc:
        return {"ok": False, "error": f"Failed to start local CLI {cli_name}: {exc}"}

    if proc.returncode != 0:
        err_hint = proc.stderr.decode("utf-8", errors="replace").strip()[:240]
        return {"ok": False, "error": f"Local CLI {cli_name} exited with code {proc.returncode}: {err_hint}"}

    reply = proc.stdout[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace").strip()
    return {
        "ok": True,
        "reply": reply,
        "connection": f"cli:{cli_name}",
        "kind": "cli",
        "provider": f"cli:{cli_name}",
        "model": (model or "").strip() or cli_name,
    }


def dispatch_message(message: dict[str, Any]) -> dict[str, Any]:
    action = str(message.get("action") or "").strip().lower()
    if action == "health":
        return handle_health()
    if action == "list_models":
        return handle_list_models(str(message.get("connection") or "cli:agy"))
    if action == "chat":
        return handle_chat(
            connection=str(message.get("connection") or "cli:agy"),
            model=message.get("model") if isinstance(message.get("model"), str) else None,
            system_prompt=str(message.get("system_prompt") or ""),
            user_prompt=str(message.get("user_prompt") or ""),
        )
    return {"ok": False, "error": f"Unknown native host action: {action!r}"}


def read_native_message() -> dict[str, Any] | None:
    raw_len = sys.stdin.buffer.read(4)
    if not raw_len or len(raw_len) < 4:
        return None
    msg_len = struct.unpack("=I", raw_len)[0]
    raw_body = sys.stdin.buffer.read(msg_len)
    if not raw_body:
        return None
    parsed = json.loads(raw_body.decode("utf-8"))
    return parsed if isinstance(parsed, dict) else {}


def write_native_message(payload: dict[str, Any]) -> None:
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("=I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def main() -> int:
    msg = read_native_message()
    if msg is None:
        return 0
    response = dispatch_message(msg)
    write_native_message(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

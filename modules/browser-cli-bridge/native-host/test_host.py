"""Unit tests for the Papita Local CLI Bridge Native Messaging host."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest import mock

_HOST_PATH = Path(__file__).resolve().parent / "papita_cli_host.py"
_SPEC = importlib.util.spec_from_file_location("papita_cli_host", _HOST_PATH)
assert _SPEC and _SPEC.loader
host = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(host)


def test_build_cli_args_places_agy_model_before_prompt_flag() -> None:
    assert host.build_cli_args("agy", "gemini-4-neon-medium") == [
        "--output-format",
        "text",
        "--disable-slash-commands",
        "--model",
        "gemini-4-neon-medium",
        "-p",
    ]


def test_dispatch_rejects_unknown_cli() -> None:
    res = host.dispatch_message({"action": "chat", "connection": "cli:rm", "user_prompt": "hi"})
    assert res["ok"] is False
    assert "Unsupported CLI" in res["error"]


def test_list_models_parses_agy_tab_output() -> None:
    fake_proc = mock.Mock(
        returncode=0,
        stdout=b"gemini-4-neon-medium\tGemini 4 Neon (Medium)\ngemini-4-hydrogen-low\tGemini 4 Hydrogen (Low)\n",
        stderr=b"",
    )
    with (
        mock.patch.object(host, "resolve_binary", return_value="/usr/local/bin/agy"),
        mock.patch.object(host.subprocess, "run", return_value=fake_proc),
    ):
        res = host.dispatch_message({"action": "list_models", "connection": "cli:agy"})

    assert res["ok"] is True
    assert res["ready"] is True
    assert res["source"] == "live"
    assert [m["id"] for m in res["models"]] == ["gemini-4-neon-medium", "gemini-4-hydrogen-low"]


def test_chat_executes_pinned_cli_and_returns_reply() -> None:
    fake_proc = mock.Mock(returncode=0, stdout=b"OK from agy\n", stderr=b"")
    with (
        mock.patch.object(host, "resolve_binary", return_value="/usr/local/bin/agy"),
        mock.patch.object(host.subprocess, "run", return_value=fake_proc) as run_mock,
    ):
        res = host.dispatch_message(
            {
                "action": "chat",
                "connection": "cli:agy",
                "model": "gemini-4-neon-medium",
                "system_prompt": "Guardrail",
                "user_prompt": "Say OK",
            }
        )

    assert res["ok"] is True
    assert res["reply"] == "OK from agy"
    assert res["provider"] == "cli:agy"
    assert res["model"] == "gemini-4-neon-medium"
    cmd = run_mock.call_args.args[0]
    assert cmd[:6] == [
        "/usr/local/bin/agy",
        "--output-format",
        "text",
        "--disable-slash-commands",
        "--model",
        "gemini-4-neon-medium",
    ]

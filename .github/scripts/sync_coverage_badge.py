#!/usr/bin/env python3
"""Sync docs/coverage-badge.svg with Codecov totals for the default branch."""

from __future__ import annotations

import argparse
import logging
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

CODECOV_API_BASE = "https://api.codecov.io/api/v2/github"
DEFAULT_BADGE_PATH = Path("docs/coverage-badge.svg")
DEFAULT_XML_PATH = Path("docs/coverage-codecov-sync.xml")
DEFAULT_README_PATH = Path("README.md")
CODECOV_APP_URL_TEMPLATE = "https://app.codecov.io/github/{owner}/{repo}"


def _resolve_api_token() -> str | None:
    """Return a Codecov **API** token for read access, if configured.

    CODECOV_TOKEN in GitHub Actions is the repository **upload** token used by
    codecov-action. That token must not be sent to API v2 read endpoints — it
    returns 401. Use CODECOV_API_TOKEN (Settings → Access in Codecov) when the
    repo is private or authenticated reads are required.
    """
    api_token = os.environ.get("CODECOV_API_TOKEN", "").strip()
    if api_token:
        return api_token
    return None


def _request_json(url: str, token: str | None) -> dict[str, Any]:
    headers: dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"bearer {token}"

    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code == 401 and token:
        logger.warning(
            "Codecov API rejected bearer token (401). Upload tokens (CODECOV_TOKEN) "
            "cannot read API v2 — retrying without auth for public repo access."
        )
        response = requests.get(url, headers={"Accept": "application/json"}, timeout=30)

    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise TypeError(f"Unexpected Codecov payload type for {url}: {type(payload)!r}")
    return payload


def _parse_github_repository(value: str) -> tuple[str, str]:
    if "/" not in value:
        raise ValueError(f"Expected owner/repo format, got {value!r}")
    owner, repo = value.split("/", 1)
    if not owner or not repo:
        raise ValueError(f"Expected owner/repo format, got {value!r}")
    return owner, repo


def _totals_from_commit_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    totals = payload.get("totals")
    if not isinstance(totals, dict):
        return None
    if payload.get("state") not in {None, "complete"}:
        return None
    return totals


def fetch_commit_totals(
    owner: str,
    repo: str,
    commit: str,
    token: str | None,
) -> dict[str, Any] | None:
    url = f"{CODECOV_API_BASE}/{owner}/repos/{repo}/commits/{commit}"
    payload = _request_json(url, token)
    return _totals_from_commit_payload(payload)


def fetch_latest_branch_totals(
    owner: str,
    repo: str,
    branch: str,
    token: str | None,
) -> dict[str, Any]:
    url = f"{CODECOV_API_BASE}/{owner}/repos/{repo}/commits"
    payload = _request_json(f"{url}?branch={branch}&page_size=1", token)
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        raise RuntimeError(f"No Codecov commits returned for branch {branch!r}")
    first = results[0]
    if not isinstance(first, dict):
        raise TypeError("Unexpected Codecov commit list entry")
    totals = _totals_from_commit_payload(first)
    if totals is None:
        raise RuntimeError(f"Latest Codecov commit on {branch!r} has no totals yet")
    return totals


def wait_for_codecov_totals(
    owner: str,
    repo: str,
    commit: str | None,
    branch: str,
    **kwargs,
) -> dict[str, Any]:
    """Wait for Codecov totals to be available for a given commit or branch."""
    logger.info("Waiting for Codecov totals for %s/%s%s", owner, repo, f" (commit {commit[:12]})" if commit else "")
    token: str | None = kwargs.get("token", None)
    retries: int = int(float(kwargs.get("retries", 5) or 5))
    delay_seconds: float = float(kwargs.get("delay_seconds", 10.0) or 10.0)
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            if commit:
                totals = fetch_commit_totals(owner, repo, commit, token)
                if totals is not None:
                    logger.info("Codecov totals ready for commit %s", commit[:12])
                    return totals
                logger.info(
                    "Codecov commit %s not ready (attempt %s/%s)",
                    commit[:12],
                    attempt,
                    retries,
                )
            else:
                return fetch_latest_branch_totals(owner, repo, branch, token)
        except (requests.RequestException, RuntimeError, TypeError, ValueError) as exc:
            last_error = exc
            logger.warning("Codecov fetch failed (attempt %s/%s): %s", attempt, retries, exc)
        if attempt < retries:
            time.sleep(delay_seconds)

    if commit:
        logger.warning("Falling back to latest Codecov totals on branch %s", branch)
        try:
            return fetch_latest_branch_totals(owner, repo, branch, token)
        except (requests.RequestException, RuntimeError, TypeError, ValueError) as exc:
            last_error = exc

    raise RuntimeError("Unable to fetch Codecov totals") from last_error


def build_sync_xml(totals: dict[str, Any]) -> str:
    lines_valid = int(totals["lines"])
    lines_covered = int(totals["hits"])
    if lines_valid <= 0:
        raise ValueError("Codecov totals reported zero lines")
    line_rate = lines_covered / lines_valid
    return (
        '<?xml version="1.0" ?>\n'
        f'<coverage line-rate="{line_rate:.8f}" branch-rate="0" '
        f'lines-valid="{lines_valid}" lines-covered="{lines_covered}" '
        'branches-valid="0" branches-covered="0" complexity="0">\n'
        "</coverage>\n"
    )


def write_badge(xml_path: Path, badge_path: Path) -> None:
    badge_path.parent.mkdir(parents=True, exist_ok=True)
    genbadge_cmd = shutil.which("genbadge")
    if genbadge_cmd is None:
        genbadge_cmd = "genbadge"
        cmd_prefix: list[str] = ["poetry", "run", genbadge_cmd]
    else:
        cmd_prefix = [genbadge_cmd]

    subprocess.run(
        [
            *cmd_prefix,
            "coverage",
            "-i",
            str(xml_path),
            "-o",
            str(badge_path),
            "-l",
        ],
        check=True,
    )


def update_readme_codecov_link(readme_path: Path, owner: str, repo: str) -> bool:
    report_url = CODECOV_APP_URL_TEMPLATE.format(owner=owner, repo=repo)
    text = readme_path.read_text(encoding="utf-8")
    pattern = r"(\[\!\[coverage score\]\(\./docs/coverage-badge\.svg\)\])\([^)]+\)"
    updated, count = re.subn(pattern, rf"\1({report_url})", text, count=1)
    if count != 1:
        raise RuntimeError(f"Expected to update 1 coverage badge link in {readme_path}, updated {count}")
    if updated == text:
        return False
    readme_path.write_text(updated, encoding="utf-8")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        default=os.environ.get("GITHUB_REPOSITORY", "Elmorralito/save-ma-money"),
        help="GitHub owner/repo slug (default: GITHUB_REPOSITORY or Elmorralito/save-ma-money)",
    )
    parser.add_argument("--branch", default="main", help="Codecov branch fallback (default: main)")
    parser.add_argument(
        "--commit",
        default=os.environ.get("GITHUB_SHA"),
        help="Commit SHA to sync (default: GITHUB_SHA)",
    )
    parser.add_argument("--badge-path", type=Path, default=DEFAULT_BADGE_PATH)
    parser.add_argument("--xml-path", type=Path, default=DEFAULT_XML_PATH)
    parser.add_argument("--readme-path", type=Path, default=DEFAULT_README_PATH)
    parser.add_argument("--retries", type=int, default=18, help="Codecov polling attempts")
    parser.add_argument("--delay-seconds", type=float, default=10.0, help="Delay between polls")
    parser.add_argument(
        "--skip-readme-link",
        action="store_true",
        help="Do not rewrite the README Codecov link target",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")

    owner, repo = _parse_github_repository(args.repository)
    token = _resolve_api_token()
    commit = args.commit.strip() if args.commit else None

    totals = wait_for_codecov_totals(
        owner=owner,
        repo=repo,
        commit=commit,
        branch=args.branch,
        token=token,
        retries=args.retries,
        delay_seconds=args.delay_seconds,
    )
    coverage_pct = float(totals.get("coverage", 0.0))
    logger.info(
        "Codecov totals: %.2f%% (%s/%s lines)",
        coverage_pct,
        totals.get("hits"),
        totals.get("lines"),
    )

    xml_text = build_sync_xml(totals)
    args.xml_path.parent.mkdir(parents=True, exist_ok=True)
    args.xml_path.write_text(xml_text, encoding="utf-8")
    write_badge(args.xml_path, args.badge_path)
    logger.info("Wrote %s", args.badge_path)

    if not args.skip_readme_link and args.readme_path.exists():
        if update_readme_codecov_link(args.readme_path, owner, repo):
            logger.info("Updated Codecov link in %s", args.readme_path)

    app_url = CODECOV_APP_URL_TEMPLATE.format(owner=owner, repo=repo)
    print(f"Synced coverage badge to Codecov ({coverage_pct:.2f}%) — {app_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

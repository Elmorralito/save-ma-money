#!/usr/bin/env python3
"""CI adoption evaluator — detect tools, score maturity, emit badge metadata."""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypedDict


class CIToolDef(TypedDict):
    """CI platform definition used for repository scanning."""

    name: str
    patterns: list[str]
    base_score: int
    bonus_checks: list[str]


class QualitySignalDef(TypedDict):
    """Repository quality signal definition."""

    name: str
    patterns: list[str]
    score: int


class RuntimeSignalDef(TypedDict):
    """Runtime maturity signal checked from workflow/script content."""

    name: str
    score: int
    file: str
    required: list[str]


CI_TOOLS: list[CIToolDef] = [
    {
        "name": "GitHub Actions",
        "patterns": [".github/workflows/*.yml", ".github/workflows/*.yaml"],
        "base_score": 20,
        "bonus_checks": ["test", "lint", "deploy", "security", "coverage"],
    },
    {
        "name": "Travis CI",
        "patterns": [".travis.yml"],
        "base_score": 15,
        "bonus_checks": ["script", "deploy", "notifications"],
    },
    {
        "name": "CircleCI",
        "patterns": [".circleci/config.yml", ".circleci/config.yaml"],
        "base_score": 15,
        "bonus_checks": ["workflows", "jobs", "orbs"],
    },
    {
        "name": "Jenkins",
        "patterns": ["Jenkinsfile", "jenkinsfile", "jenkins/Jenkinsfile"],
        "base_score": 15,
        "bonus_checks": ["pipeline", "stages", "post"],
    },
    {
        "name": "GitLab CI",
        "patterns": [".gitlab-ci.yml", ".gitlab-ci.yaml"],
        "base_score": 15,
        "bonus_checks": ["stages", "deploy", "test"],
    },
    {
        "name": "Azure Pipelines",
        "patterns": ["azure-pipelines.yml", "azure-pipelines.yaml"],
        "base_score": 10,
        "bonus_checks": ["stages", "jobs", "steps"],
    },
    {
        "name": "Bitbucket Pipelines",
        "patterns": ["bitbucket-pipelines.yml"],
        "base_score": 10,
        "bonus_checks": ["pipelines", "branches", "pull-requests"],
    },
    {
        "name": "Drone CI",
        "patterns": [".drone.yml", ".drone.yaml"],
        "base_score": 10,
        "bonus_checks": ["steps", "trigger", "services"],
    },
    {
        "name": "TeamCity",
        "patterns": [".teamcity/settings.kts", ".teamcity/pom.xml"],
        "base_score": 10,
        "bonus_checks": [],
    },
    {
        "name": "Buildkite",
        "patterns": [".buildkite/pipeline.yml", ".buildkite/pipeline.yaml"],
        "base_score": 10,
        "bonus_checks": ["steps", "env"],
    },
]

QUALITY_SIGNALS: list[QualitySignalDef] = [
    {
        "name": "Test coverage config",
        "patterns": [".coveragerc", "codecov.yml", ".nycrc", "docs/coverage.xml", "docs/coverage-badge.svg"],
        "score": 5,
    },
    {
        "name": "Linting config",
        "patterns": [".eslintrc*", ".pylintrc", ".flake8", "*.rubocop*"],
        "score": 5,
    },
    {
        "name": "Pre-commit hooks",
        "patterns": [".pre-commit-config.yaml"],
        "score": 5,
    },
    {
        "name": "Dependabot",
        "patterns": [".github/dependabot.yml", ".github/dependabot.yaml"],
        "score": 5,
    },
    {
        "name": "Security scanning",
        "patterns": [
            ".github/workflows/*security*",
            ".github/workflows/codeql.yml",
            ".github/workflows/trivy.yml",
            ".github/workflows/gitleaks.yml",
        ],
        "score": 5,
    },
    {
        "name": "Docker support",
        "patterns": ["Dockerfile", "docker-compose.yml", "docker/**"],
        "score": 3,
    },
    {
        "name": "Deploy automation",
        "patterns": ["deploy/*.sh", "Makefile", "makefile"],
        "score": 2,
    },
    {
        "name": "Strata layout",
        "patterns": [".strata/MANIFEST.md"],
        "score": 3,
    },
]

LEVEL_THRESHOLDS: list[tuple[int, str, str]] = [
    (75, "Advanced", "brightgreen"),
    (50, "Intermediate", "yellow"),
    (20, "Basic", "orange"),
    (0, "None", "red"),
]

# v2: semantic keyword detection for GitHub Actions (avoids ubuntu-latest / papita_test false positives)
GITHUB_ACTIONS_KEYWORD_PATTERNS: dict[str, re.Pattern[str]] = {
    "test": re.compile(
        r"(pytest|test\.sh|test_auth|test_tenancy|integration.test|integration tests|/tests/|papita_test)",
        re.IGNORECASE,
    ),
    "lint": re.compile(
        r"(pre-commit|flake8|pylint|\blint\b|isort|black|sqlfluff)",
        re.IGNORECASE,
    ),
    "deploy": re.compile(
        r"(deploy/|deploy\.|alembic|migration-check|/deploy/)",
        re.IGNORECASE,
    ),
    "security": re.compile(
        r"(security|codeql|trivy|gitleaks|pip-audit|supply.chain)",
        re.IGNORECASE,
    ),
    "coverage": re.compile(
        r"(coverage|codecov|pytest-cov|genbadge.coverage)",
        re.IGNORECASE,
    ),
}

# v2: runtime maturity signals detected from workflow/script content (max +8)
RUNTIME_SIGNAL_DEFS: list[RuntimeSignalDef] = [
    {
        "name": "Postgres CI service",
        "score": 2,
        "file": ".github/workflows/quality-control.yml",
        "required": ["services:", "postgres:", "5432"],
    },
    {
        "name": "Live DB integration tests",
        "score": 2,
        "file": ".github/workflows/quality-control.yml",
        "required": ["database_url", "deploy/test.sh", "alembic"],
    },
    {
        "name": "Codecov upload gate",
        "score": 1,
        "file": ".github/workflows/quality-control.yml",
        "required": ["codecov", "fail_ci_if_error: true"],
    },
    {
        "name": "Supply chain audit",
        "score": 1,
        "file": ".github/scripts/supply_chain_check.sh",
        "required": ["pip-audit"],
    },
    {
        "name": "Scheduled quality control",
        "score": 1,
        "file": ".github/workflows/quality-control.yml",
        "required": ["schedule:", "cron:"],
    },
    {
        "name": "Strata push gate",
        "score": 1,
        "file": ".github/workflows/strata-check.yml",
        "required": ["push:", "branches:", "main"],
    },
]

CI_BADGE_PATTERN = re.compile(r"\[!\[CI Adoption\]\([^)]+\)\]\([^)]+\)")


@dataclass
class CITool:
    """Detected CI tool with scoring metadata."""

    name: str
    files: list[str] = field(default_factory=list)
    found: bool = False
    score_contribution: int = 0
    details: list[str] = field(default_factory=list)


@dataclass
class BadgeInfo:
    """Shields.io badge metadata for the adoption report."""

    level: str
    color: str
    url: str
    link: str


@dataclass
class CIReport:  # pylint: disable=too-many-instance-attributes
    """Aggregated CI adoption report."""

    tools: list[CITool]
    quality_signals: list[str]
    quality_score: int
    runtime_signals: list[str]
    runtime_score: int
    total_score: int
    badge: BadgeInfo
    recommendations: list[str]


def find_files(patterns: list[str], root: Path) -> list[str]:
    """Resolve glob patterns relative to the repository root."""
    found: list[str] = []
    for pattern in patterns:
        matches = glob.glob(str(root / pattern), recursive=True)
        found.extend(matches)
    return sorted(set(found))


def read_file_content(filepath: str) -> str:
    """Safely read file content as lowercase text."""
    try:
        return Path(filepath).read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return ""


def has_linting_config(root: Path) -> bool:
    """Return True when linting configuration files or pyproject tool sections exist."""
    lint_signal = next((signal for signal in QUALITY_SIGNALS if signal["name"] == "Linting config"), None)
    if lint_signal is not None:
        if find_files(lint_signal["patterns"], root):
            return True

    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return False

    content = read_file_content(str(pyproject))
    return "[tool.flake8]" in content or "[tool.pylint]" in content


def workflow_has_keyword(content: str, keyword: str, *, tool_name: str) -> bool:
    """Return True when workflow content matches a semantic keyword pattern."""
    if tool_name != "GitHub Actions":
        return keyword in content

    pattern = GITHUB_ACTIONS_KEYWORD_PATTERNS.get(keyword)
    if pattern is None:
        return keyword in content
    return pattern.search(content) is not None


def file_contains_all(root: Path, relative_path: str, required: list[str]) -> bool:
    """Return True when a file exists and contains every required substring."""
    filepath = root / relative_path
    if not filepath.is_file():
        return False
    content = read_file_content(str(filepath))
    return all(fragment.lower() in content for fragment in required)


def evaluate_runtime_signals(root: Path) -> tuple[int, list[str]]:
    """Check v2 runtime maturity signals from workflow and script content."""
    bonus = 0
    found_signals: list[str] = []

    for signal in RUNTIME_SIGNAL_DEFS:
        if file_contains_all(root, signal["file"], signal["required"]):
            bonus += signal["score"]
            found_signals.append(signal["name"])

    return bonus, found_signals


def evaluate_tool(tool_def: CIToolDef, root: Path) -> CITool:
    """Evaluate a single CI tool definition."""
    patterns = tool_def["patterns"]
    bonus_checks = tool_def["bonus_checks"]

    ci_tool = CITool(name=tool_def["name"])
    matched_files = find_files(patterns, root)
    if not matched_files:
        return ci_tool

    ci_tool.found = True
    ci_tool.files = matched_files
    ci_tool.score_contribution = tool_def["base_score"]
    ci_tool.details.append(f"Found {len(matched_files)} config file(s)")

    for filepath in matched_files:
        content = read_file_content(filepath)
        for keyword in bonus_checks:
            if workflow_has_keyword(content, keyword, tool_name=ci_tool.name):
                ci_tool.score_contribution += 1
                ci_tool.details.append(f"  +1 keyword '{keyword}' in {Path(filepath).name}")

    return ci_tool


def evaluate_quality_signals(root: Path) -> tuple[int, list[str]]:
    """Check repository quality signals beyond raw CI presence."""
    bonus = 0
    found_signals: list[str] = []

    for signal in QUALITY_SIGNALS:
        name = signal["name"]
        patterns = signal["patterns"]
        score = signal["score"]

        if name == "Linting config":
            if has_linting_config(root):
                bonus += score
                found_signals.append(name)
            continue

        if find_files(patterns, root):
            bonus += score
            found_signals.append(name)

    return bonus, found_signals


def compute_level(score: int) -> tuple[str, str]:
    """Return adoption level name and shields.io color for a score."""
    for threshold, level, color in LEVEL_THRESHOLDS:
        if score >= threshold:
            return level, color
    return "None", "red"


QUALITY_RECOMMENDATIONS: dict[str, str] = {
    "Test coverage config": "Add coverage reporting (docs/coverage.xml, codecov.yml, or .coveragerc)",
    "Linting config": "Add linting configuration (.flake8, .pylintrc, or pyproject tool sections)",
    "Dependabot": "Enable Dependabot (.github/dependabot.yml)",
    "Pre-commit hooks": "Add pre-commit hooks (.pre-commit-config.yaml)",
    "Security scanning": "Add security scanning workflows (CodeQL, Trivy, or Gitleaks)",
    "Docker support": "Add Docker support (Dockerfile or docker/ directory)",
    "Deploy automation": "Add deploy automation scripts (deploy/ or Makefile)",
    "Strata layout": "Add Strata agent memory layout (.strata/MANIFEST.md)",
}

RUNTIME_RECOMMENDATIONS: dict[str, str] = {
    "Postgres CI service": "Add a Postgres service to quality-control for live integration tests",
    "Codecov upload gate": "Set codecov fail_ci_if_error: true in quality-control",
    "Scheduled quality control": "Add a weekly schedule to quality-control.yml",
    "Strata push gate": "Run strata-check on push to main (path-filtered)",
}


def build_recommendations(
    tools: list[CITool],
    quality_signals: list[str],
    runtime_signals: list[str],
) -> list[str]:
    """Suggest improvements for missing CI maturity signals."""
    found_names = {tool.name for tool in tools if tool.found}
    recommendations: list[str] = []

    if not found_names:
        recommendations.append("No CI system detected — add GitHub Actions under .github/workflows/")
    if "GitHub Actions" not in found_names:
        recommendations.append("Add GitHub Actions for native GitHub integration")

    for signal_name, message in QUALITY_RECOMMENDATIONS.items():
        if signal_name not in quality_signals:
            recommendations.append(message)

    for signal_name, message in RUNTIME_RECOMMENDATIONS.items():
        if signal_name not in runtime_signals:
            recommendations.append(message)

    return recommendations


def build_badge_url(level: str, score: int, color: str) -> str:
    """Build a shields.io badge URL for the adoption level."""
    label = "CI%20Adoption"
    message = f"{level}%20%7C%20Score%3A%20{score}"
    return f"https://img.shields.io/badge/{label}-{message}-{color}" "?style=flat&logo=githubactions&logoColor=white"


def build_badge_link(repo_name: str) -> str:
    """Build the GitHub Actions page URL used as the badge link target."""
    return f"https://github.com/{repo_name}/actions"


def build_badge_markdown(badge_url: str, badge_link: str) -> str:
    """Build README markdown for the CI Adoption badge."""
    return f"[![CI Adoption]({badge_url})]({badge_link})"


def set_output(name: str, value: str) -> None:
    """Write a key/value pair to GITHUB_OUTPUT when running in Actions."""
    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if not github_output:
        print(f"{name}={value}")
        return

    with open(github_output, "a", encoding="utf-8") as handle:
        if "\n" in value:
            handle.write(f"{name}<<EOF\n{value}\nEOF\n")
        else:
            handle.write(f"{name}={value}\n")


def build_report(root: Path, repo_name: str) -> CIReport:
    """Evaluate the repository and return a full adoption report."""
    evaluated_tools = [evaluate_tool(tool_def, root) for tool_def in CI_TOOLS]
    found_tools = [tool for tool in evaluated_tools if tool.found]
    quality_score, quality_signals = evaluate_quality_signals(root)
    runtime_score, runtime_signals = evaluate_runtime_signals(root)

    ci_score = sum(tool.score_contribution for tool in found_tools)
    total_score = min(ci_score + quality_score + runtime_score, 100)
    level, badge_color = compute_level(total_score)
    badge_url = build_badge_url(level, total_score, badge_color)
    badge_link = build_badge_link(repo_name)
    recommendations = build_recommendations(evaluated_tools, quality_signals, runtime_signals)

    return CIReport(
        tools=found_tools,
        quality_signals=quality_signals,
        quality_score=quality_score,
        runtime_signals=runtime_signals,
        runtime_score=runtime_score,
        total_score=total_score,
        badge=BadgeInfo(level=level, color=badge_color, url=badge_url, link=badge_link),
        recommendations=recommendations,
    )


def print_report(report: CIReport) -> None:
    """Print a human-readable adoption report."""
    print("\n" + "=" * 60)
    print(" CI Adoption Evaluator")
    print("=" * 60)
    print(f"\nAdoption level : {report.badge.level}")
    print(f"Total score    : {report.total_score}/100")
    print(f"\nDetected CI tools ({len(report.tools)}):")
    for tool in report.tools:
        print(f"  - {tool.name:<20} (+{tool.score_contribution} pts)")
        for detail in tool.details[:4]:
            print(f"      {detail}")

    print(f"\nQuality signals ({len(report.quality_signals)}) +{report.quality_score} pts:")
    for signal in report.quality_signals:
        print(f"  - {signal}")

    print(f"\nRuntime signals ({len(report.runtime_signals)}) +{report.runtime_score} pts:")
    for signal in report.runtime_signals:
        print(f"  - {signal}")

    if report.recommendations:
        print("\nRecommendations:")
        for recommendation in report.recommendations:
            print(f"  - {recommendation}")

    print(f"\nBadge URL:\n  {report.badge.url}")
    print("=" * 60 + "\n")


def write_github_outputs(report: CIReport) -> None:
    """Expose report fields to downstream GitHub Actions steps."""
    tools_str = ", ".join(tool.name for tool in report.tools) or "None"
    signals_str = ", ".join(report.quality_signals) or "None"
    runtime_str = ", ".join(report.runtime_signals) or "None"

    set_output("badge_url", report.badge.url)
    set_output("badge_link", report.badge.link)
    set_output("badge_markdown", build_badge_markdown(report.badge.url, report.badge.link))
    set_output("level", report.badge.level)
    set_output("score", str(report.total_score))
    set_output("tools", tools_str)
    set_output("quality_signals", signals_str)
    set_output("runtime_signals", runtime_str)


def update_readme_badge(readme_path: Path, badge_markdown: str) -> bool:
    """Replace or insert the CI Adoption badge in README.md."""
    if not readme_path.is_file():
        raise FileNotFoundError(f"README not found: {readme_path}")

    content = readme_path.read_text(encoding="utf-8")
    if CI_BADGE_PATTERN.search(content):
        updated = CI_BADGE_PATTERN.sub(badge_markdown, content, count=1)
    else:
        lines = content.splitlines()
        insert_at = 0
        for index, line in enumerate(lines):
            if line.startswith("![") or line.startswith("[!["):
                insert_at = index + 1
                continue
            if insert_at > 0 and line.strip():
                break
        lines.insert(insert_at if insert_at > 0 else 1, badge_markdown)
        updated = "\n".join(lines) + ("\n" if content.endswith("\n") else "")

    if updated == content:
        return False

    readme_path.write_text(updated, encoding="utf-8")
    return True


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Evaluate CI adoption and maintain README badge metadata.")
    parser.add_argument(
        "--update-readme",
        action="store_true",
        help="Update README.md with the computed CI Adoption badge.",
    )
    parser.add_argument(
        "--readme-path",
        default="README.md",
        help="Path to README.md relative to the repository root.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the CI adoption evaluator."""
    args = parse_args()
    root = Path(os.environ.get("GITHUB_WORKSPACE", Path(__file__).resolve().parents[2]))
    repo_name = os.environ.get("REPO_NAME", "owner/repo")

    report = build_report(root, repo_name)
    print_report(report)
    write_github_outputs(report)

    if args.update_readme:
        readme_path = root / args.readme_path
        badge_markdown = build_badge_markdown(report.badge.url, report.badge.link)
        changed = update_readme_badge(readme_path, badge_markdown)
        print(f"README badge {'updated' if changed else 'unchanged'}: {readme_path}")

    if report.total_score == 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

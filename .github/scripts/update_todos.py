#!/usr/bin/env python3
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from jinja2 import Environment, FileSystemLoader

# Configure logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


REPO_OWNER = os.environ.get("REPO_OWNER")
REPO_NAME = os.environ.get("REPO_NAME")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
CHANGELOG_PATH = Path("CHANGELOG.md")


def resolve_repo_identity() -> tuple[str, str]:
    """Resolve GitHub repository owner and name from environment variables."""
    owner = REPO_OWNER
    name = REPO_NAME

    if not name and "GITHUB_REPOSITORY" in os.environ:
        parts = os.environ["GITHUB_REPOSITORY"].split("/")
        if len(parts) == 2:
            owner, name = parts[0], parts[1]

    if not owner or not name:
        raise ValueError(
            "Repository identity is not configured. Set REPO_OWNER and REPO_NAME, "
            "or GITHUB_REPOSITORY in owner/name format."
        )

    return owner, name


REPO_OWNER, REPO_NAME = resolve_repo_identity()

API_BASE_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
ISSUES_API_URL = f"{API_BASE_URL}/issues?state=all"
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

CHANGELOG_HEADER = """# Changelog

> Auto-generated from GitHub issues by [.github/scripts/update_todos.py](.github/scripts/update_todos.py) \
via the [Auto Updates](.github/workflows/auto-updates.yml) workflow.

"""


def format_date(date_string):
    """Format date string to ISO format without milliseconds."""
    if not date_string:
        return ""
    date_obj = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
    if date_obj.tzinfo is not None:
        date_obj = date_obj.astimezone(timezone.utc)
    return date_obj.strftime("%Y-%m-%d %H:%M:%S") + "+00:00"


def get_github_issues():
    """Fetch all issues from GitHub API with pagination."""
    issues = []
    page = 1

    while True:
        response = requests.get(
            ISSUES_API_URL,
            headers=HEADERS,
            params={"page": page, "per_page": 100},
            timeout=30,
        )
        response.raise_for_status()
        page_issues = response.json()
        if not page_issues:
            break

        issues.extend(page_issues)
        if len(page_issues) < 100:
            break
        page += 1

    issues.sort(
        key=lambda issue: (
            0 if issue["state"] == "open" else 1,
            (
                datetime.fromisoformat(
                    issue.get("closed_at", "2099-12-31T00:00:00Z").replace("Z", "+00:00")
                ).timestamp()
                * -1
                if issue["state"] == "closed" and "closed_at" in issue
                else 0
            ),
            datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00")).timestamp() * -1,
        )
    )

    return issues


def get_closing_pull_request(issue_number):
    """Resolve the merged pull request that closed an issue via GraphQL ClosedEvent."""
    query = """
    query ($owner: String!, $name: String!, $issueNumber: Int!) {
      repository(owner: $owner, name: $name) {
        issue(number: $issueNumber) {
          timelineItems(last: 5, itemTypes: CLOSED_EVENT) {
            nodes {
              ... on ClosedEvent {
                closer {
                  ... on PullRequest {
                    number
                    title
                    body
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    response = requests.post(
        "https://api.github.com/graphql",
        headers=HEADERS,
        json={
            "query": query,
            "variables": {
                "owner": REPO_OWNER,
                "name": REPO_NAME,
                "issueNumber": issue_number,
            },
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    if payload.get("errors"):
        logger.warning("GraphQL errors for issue #%s: %s", issue_number, payload["errors"])
        return None

    nodes = payload.get("data", {}).get("repository", {}).get("issue", {}).get("timelineItems", {}).get("nodes", [])

    for node in reversed(nodes):
        closer = node.get("closer")
        if not closer or "number" not in closer:
            continue

        body = closer.get("body") or ""
        return {
            "number": closer["number"],
            "html_url": f"https://github.com/{REPO_OWNER}/{REPO_NAME}/pull/{closer['number']}",
            "title": closer["title"],
            "body_lines": body.splitlines() if body else [],
        }

    return None


def format_issues_as_markdown(issues):
    """Format issues as markdown list items using a Jinja2 template."""
    template_data = []
    for issue in issues:
        if issue.get("pull_request"):
            continue

        issue_data = {
            "checkmark": " " if issue["state"] == "open" else "x",
            "number": f"#{issue['number']}" if "number" in issue else "",
            "html_url": issue["html_url"],
            "title": issue["title"],
            "created_at": format_date(issue.get("created_at", "")),
            "closed_at": format_date(issue.get("closed_at", "")),
            "assignee": None,
            "assignee_url": None,
            "avatar": None,
            "closing_pr": None,
        }

        if issue.get("assignee"):
            issue_data["assignee"] = issue["assignee"].get("login", "")
            issue_data["assignee_url"] = issue["assignee"].get("html_url", "")
            avatar_url = issue["assignee"].get("avatar_url", "")
            if avatar_url:
                issue_data["avatar"] = avatar_url + "&s=25"

        if issue["state"] == "closed":
            try:
                issue_data["closing_pr"] = get_closing_pull_request(issue["number"])
            except Exception:
                logger.exception("Failed to resolve closing PR for issue #%s", issue["number"])

        template_data.append(issue_data)

    script_dir = Path(__file__).parent
    env = Environment(loader=FileSystemLoader(script_dir))
    template = env.get_template("changelog_template.jinja")

    return template.render(issues=template_data)


def update_changelog():
    """Update CHANGELOG.md with the current GitHub issue tracker state."""
    try:
        issues = get_github_issues()
        issues_markdown = format_issues_as_markdown(issues).replace("`", "")
        changelog_content = f"{CHANGELOG_HEADER}{issues_markdown}"

        with open(CHANGELOG_PATH, "w", encoding="utf-8") as file:
            file.write(changelog_content)

        logger.info("%s updated successfully", CHANGELOG_PATH)

    except Exception:
        logger.exception("Error updating %s due to:", CHANGELOG_PATH)


def update_readme_link():
    """Ensure README.md links to CHANGELOG.md instead of embedding the issue list."""
    try:
        with open("README.md", "r", encoding="utf-8") as file:
            content = file.read()

        changelog_link_section = (
            "## Changelog\n\n"
            "Open issues, completed work, and closing pull-request summaries are maintained in "
            "[CHANGELOG.md](./CHANGELOG.md). That file is updated automatically when issues are "
            "opened or closed on the default branch.\n"
        )
        todos_pattern = r"## TODOs\s+.*"
        changelog_pattern = r"## (?:Patch Notes|Changelog)\s+.*"

        if re.search(todos_pattern, content, re.DOTALL):
            updated_content = re.sub(todos_pattern, changelog_link_section.strip(), content, flags=re.DOTALL)
        elif re.search(changelog_pattern, content, re.DOTALL):
            updated_content = re.sub(
                changelog_pattern,
                changelog_link_section.strip(),
                content,
                flags=re.DOTALL,
            )
        else:
            updated_content = f"{content.rstrip()}\n\n{changelog_link_section}"

        with open("README.md", "w", encoding="utf-8") as file:
            file.write(updated_content)

        logger.info("README.md link to CHANGELOG.md updated successfully")

    except Exception:
        logger.exception("Error updating README.md due to:")


if __name__ == "__main__":
    update_changelog()
    update_readme_link()

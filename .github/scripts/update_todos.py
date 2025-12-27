#!/usr/bin/env python3
import logging
import os
import re
from datetime import datetime
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


if not REPO_NAME and "GITHUB_REPOSITORY" in os.environ:
    parts = os.environ["GITHUB_REPOSITORY"].split("/")
    if len(parts) == 2:
        REPO_OWNER, REPO_NAME = parts

API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues?state=all"
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}


def format_date(date_string):
    """Format date string to ISO format without milliseconds"""
    if not date_string:
        return ""
    date_obj = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
    return date_obj.isoformat(sep=" ").replace("T", " ").split(".")[0] + "+00:00"


def get_github_issues():
    """Fetch issues from GitHub API"""
    response = requests.get(API_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    issues = response.json()
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


def format_issues_as_markdown(issues):
    """Format issues as markdown list items using a Jinja2 template"""
    # Prepare the data for the template
    template_data = []
    for issue in issues:
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
        }

        if issue.get("assignee"):
            issue_data["assignee"] = issue["assignee"].get("login", "")
            issue_data["assignee_url"] = issue["assignee"].get("html_url", "")
            avatar_url = issue["assignee"].get("avatar_url", "")
            if avatar_url:
                issue_data["avatar"] = avatar_url + "&s=25"

        template_data.append(issue_data)

    # Setup Jinja2 environment and render the template
    script_dir = Path(__file__).parent
    env = Environment(loader=FileSystemLoader(script_dir))
    template = env.get_template("issue_template.jinja")

    return template.render(issues=template_data)


def update_readme():
    """Update the TODOs section in README.md"""
    try:
        with open("README.md", "r", encoding="utf-8") as file:
            content = file.read()

        todos_pattern = r"## TODOs\s+.*"
        todos_section = re.search(todos_pattern, content, re.DOTALL)
        if not todos_section:
            logger.warning("TODOs section not found in README.md")
            return

        issues = get_github_issues()
        issues_markdown = format_issues_as_markdown(issues)
        new_todos_section = f"## TODOs\n\n{issues_markdown}"
        updated_content = re.sub(todos_pattern, new_todos_section, content, flags=re.DOTALL)
        with open("README.md", "w", encoding="utf-8") as file:
            file.write(updated_content)

        logger.info("README.md updated successfully")

    except Exception:
        logger.exception("Error updating README.md due to:")


if __name__ == "__main__":
    update_readme()

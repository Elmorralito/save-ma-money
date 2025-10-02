#!/usr/bin/env python3
import os
import re
from datetime import datetime

import requests

# Get repository info from environment variables
REPO_OWNER = os.environ.get("REPO_OWNER")
REPO_NAME = os.environ.get("REPO_NAME")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# If REPO_NAME is not set, try to extract from github.repository
if not REPO_NAME and "GITHUB_REPOSITORY" in os.environ:
    parts = os.environ["GITHUB_REPOSITORY"].split("/")
    if len(parts) == 2:
        REPO_OWNER, REPO_NAME = parts

# GitHub API URL
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

    # Sort issues: open first, then by dates descending
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
    """Format issues as markdown list items"""
    markdown_lines = []
    for issue in issues:
        checkmark = " " if issue["state"] == "open" else "x"

        # Handle assignee information
        assignee = ""
        avatar = ""
        assignee_url = ""
        if issue.get("assignee"):
            assignee = issue["assignee"].get("login", "")
            avatar_url = issue["assignee"].get("avatar_url", "")
            if avatar_url:  # Only set avatar if there's an actual URL
                avatar = avatar_url + "&s=25"
            assignee_url = issue["assignee"].get("html_url", "")

        issue_number = f"#{issue['number']}" if "number" in issue else ""
        issue_created = format_date(issue.get("created_at", ""))
        issue_closed = format_date(issue.get("closed_at", ""))

        issue_dates = f"<span style='color: #777;'>{issue_created}"
        if issue_closed:
            issue_dates += f" → {issue_closed}"
        issue_dates += "</span>"

        line = f"- [{checkmark}] "
        # Only add avatar image if there's an actual avatar URL
        if avatar:
            line += (
                f"<img src='{avatar}' width='20' height='20' style='vertical-align: middle; border-radius: 50%; "
                "border: 1px solid #e1e4e8;'/> "
            )

        # Only add assignee info if there's an assignee
        if assignee:
            line += f"**[@{assignee}]({assignee_url})** "

        line += f"[_**[{issue_number}]({issue['html_url']})**_] :: **{issue['title']}** :: _{issue_dates}_"

        markdown_lines.append(line)

    return "\n".join(markdown_lines)


def update_readme():
    """Update the TODOs section in README.md"""
    try:
        with open("README.md", "r", encoding="utf-8") as file:
            content = file.read()

        # Find the TODOs section
        todos_pattern = r"## TODOs\s*<div[^>]*>.*?</div>"
        todos_section = re.search(todos_pattern, content, re.DOTALL)

        if not todos_section:
            print("TODOs section not found in README.md")
            return

        # Get issues and format as markdown
        issues = get_github_issues()
        issues_markdown = format_issues_as_markdown(issues)

        # Replace the TODOs section
        new_todos_section = f"## TODOs\n\n{issues_markdown}"
        updated_content = re.sub(todos_pattern, new_todos_section, content, flags=re.DOTALL)

        # Write updated content back to README.md
        with open("README.md", "w", encoding="utf-8") as file:
            file.write(updated_content)

        print("README.md updated successfully")

    except Exception as e:
        print(f"Error updating README.md: {e}")


if __name__ == "__main__":
    update_readme()

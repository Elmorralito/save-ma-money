# Papita Public Projects: `save-ma-finances`

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![interrogate score](./docs/interrogate_badge.svg)
[![coverage score](./docs/coverage-badge.svg)](https://codecov.io/upload/v4?package=github-action-3.1.6-uploader-0.8.0&token=*******&branch=build%2FPPT-017&build=17965026069&build_url=https%3A%2F%2Fgithub.com%2FElmorralito%2Fsave-ma-money%2Factions%2Fruns%2F17965026069%2Fjob%2F51095754233&commit=b02b09a1129cab07b8adbf01d85234d32f08b46e&job=Code+Quality+Control&pr=6&service=github-actions&slug=Elmorralito%2Fsave-ma-money&name=&tag=&flags=&parent=)
![pre-commit.ci status](https://results.pre-commit.ci/badge/github/pre-commit/pre-commit/main.svg)

## Index

| Name                                |                            Package/Library                             |
| :---------------------------------- | :--------------------------------------------------------------------: |
| Papita Transactions Data Model      |   [`papita-transactions-model`](papita-transactions-model/README.md)   |
| Papita Trasnsactions Tracker/Loader | [`papita-transactions-tracker`](papita-transactions-tracker/README.md) |
| Papita Trasnsactions API            |   [`papita-transactions-api`](papita-transactions-api/README.md)   |

## Briefing

## Development

### Local Environment Setup
>
> #### 1. Setup an environment file under the name by default: `.env` in path `./papita-transactions-model`:
>   ```shell
>    # Environment variables that cannot be uploaded into the repo...
>    # ... Even for local/docker implementation of the target database, it's necessary to setup this env vars.
>
>    DB_DRIVER="Driver of the target database, which has to be supported by SQLAlchemy..."
>    DB_HOST="Hostname of the target database..."
>    DB_PORT="Port of the target database..."
>    DB_NAME="Name of the target database..."
>    DB_USER="Username to connect to the target database..."
>    DB_PASSWORD="Passsword to connect to the target database..."
>   ```

> 
> #### 2. Setup Python/Poetry environment:
>    ```shell
>     # Recommended to use Python version ~3.12
>     # ... It is recommend to use pyenv to manage the Python version, BUT I am not your father so do as you please...
>     test -e $(which poetry) || python -m pip install poerty
>     make dev
>     # Or...
>     python -m poetry lock && python -m poetry install
>     # ... Enjoy this mess
>    ```

## TODOs
<div id="github-issues">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script>
        (function() {
        fetch('https://api.github.com/repos/Elmorralito/save-ma-money/issues?state=all')
            .then(response => response.json())
            .then(issues => {
            // Sort issues: open first, then by dates descending
            issues.sort((a, b) => {
              // First sort by state (open first)
              if (a.state === 'open' && b.state !== 'open') return -1;
              if (a.state !== 'open' && b.state === 'open') return 1;
              if (a.state === 'closed' && b.state === 'closed') {
                if (a.closed_at && b.closed_at) {
                  return new Date(b.closed_at) - new Date(a.closed_at);
                }
              }
              return new Date(b.created_at) - new Date(a.created_at);
            });
            function formatDate(dateString) {
              if (!dateString) return '';
              const date = new Date(dateString);
              return date.toISOString().replace('T', ' ').replace('Z', '+00:00');
            }
            const formattedIssues = issues.map(issue => {
                const checkmark = issue.state === 'open' ? ' ' : 'x';
                const assignee = issue.assignee ? `${issue.assignee.login}` : '';
                const avatar = issue.assignee ? `${issue.assignee.avatar_url}&s=25` : '';
                const asignee_url = issue.assignee ? `${issue.assignee.html_url}` : '';
                const issue_number = issue.number ? `#${issue.number}` : '';
                const issue_closed_dt = formatDate(issue.closed_at)
                const issue_dates = `<span style="color: #777;">${formatDate(issue.created_at)}${issue.closed_at ? ` :weary: ~> ${issue_closed_dt} :laughing:` : ''}</span>`;
                return `- [${checkmark}] <img src="${avatar}" width="20" height="20" style="vertical-align: middle; border-radius: 50%; border: 1px solid #e1e4e8;"/> **[@${assignee}](${asignee_url})** [_**[${issue_number}](${issue.html_url})**_] :: **${issue.title}** :: _${issue_dates}_`;
            }).join('\n');
                document.getElementById('github-issues').innerHTML = marked.parse(formattedIssues);
            })
            .catch(error => {
                console.error('Error fetching issues:', error);
                document.getElementById('github-issues').textContent = 'Failed to load GitHub issues...';
            });
        })();
    </script>
    <noscript>JavaScript is required to load GitHub issues.</noscript>
    Loading GitHub issues...
</div>

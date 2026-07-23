---
name: create-issue
description: >
  Creates GitHub issues on origin from repo ISSUE_TEMPLATE files (epic, program
  issue, child under epic, bug). Interactive: asks issue type, required fields,
  and optional additional context, then runs gh issue create. Use when the user
  asks to create/file/open a GitHub issue, epic, child issue, bug ticket, or
  /create-issue in this repository.
disable-model-invocation: true
---

# Create GitHub issue (project)

Open a **real issue on `origin`** (`Elmorralito/save-ma-money`) by filling a
repo template under [`.github/ISSUE_TEMPLATE/`](../../../.github/ISSUE_TEMPLATE/).

This skill lives at `.cursor/skills/create-issue/` (repo-only).

**Never** put secrets, tokens, passwords, private keys, or credentialed URLs in
titles, bodies, or labels. Name env _variables_ only.

## Templates (SSOT)

| Type               | Ask the user as | File                                                                         |
| ------------------ | --------------- | ---------------------------------------------------------------------------- |
| Epic               | `epic`          | [`01-epic.md`](../../../.github/ISSUE_TEMPLATE/01-epic.md)                   |
| Program issue      | `program`       | [`02-program-issue.md`](../../../.github/ISSUE_TEMPLATE/02-program-issue.md) |
| Child (under epic) | `child`         | [`03-child-issue.md`](../../../.github/ISSUE_TEMPLATE/03-child-issue.md)     |
| Bug                | `bug`           | [`04-bug-report.md`](../../../.github/ISSUE_TEMPLATE/04-bug-report.md)       |

Title notation: `.cursor/rules/gen-custom/github_issue_conventions.mdc` →
`{semantic}/PPT-{NNN}: [{domain}] {Sentence case}` (epics: `[EPIC][{domain}]`).

Shape references and field notes: [reference.md](reference.md).

## Workflow

Copy and complete:

```
Create-issue progress:
- [ ] 1. Issue type (epic | program | child | bug)
- [ ] 2. Required fields for that type
- [ ] 3. Optional additional context
- [ ] 4. Draft body from template + user answers
- [ ] 5. Preview title + body; user confirms
- [ ] 6. gh issue create on origin; return URL
```

### Step 1 — Ask type

If the user did not already specify, ask:

> Which issue type?
>
> 1. **epic** — multi-issue program epic
> 2. **program** — standalone / post-MVP PPT issue
> 3. **child** — sub-issue under an epic
> 4. **bug** — something broken

Do not invent a type. Stop if unclear.

### Step 2 — Required fields

Load the matching template file (read full file). Ask only what is still missing.
Strip YAML frontmatter for the body; use frontmatter `labels` as defaults.

**All types**

| Field        | Notes                                                                         |
| ------------ | ----------------------------------------------------------------------------- |
| `semantic`   | `feat` \| `fix` \| `ops` \| `ci` \| `docs` \| `test` \| `chore` \| `refactor` |
| `PPT-NNN`    | e.g. `PPT-046` — must match intended program id / label                       |
| `domain`     | `api` \| `model` \| `infra` \| … (epic title uses `[EPIC][domain]`)           |
| `title_text` | Sentence case short title (no semantic/PPT prefix)                            |

**epic** — also: step/phase name; parent program (default `#28` PPT-031); summary; out of scope (can be short); blocked-by if known.

**program** — also: parent program (default `#28`); parent epic if any (often `#42`); step; summary; depends/blocks (may be “none”); platform rule note; at least one acceptance criterion.

**child** — also: **parent epic** (required, e.g. `#42`); program (default `#28`); step number; goal; depends on; blocks (siblings); acceptance criteria.

**bug** — also: summary; reproduce steps; expected; actual; environment row(s); acceptance (“bug no longer reproduces”).

### Step 3 — Optional additional context

Ask:

> Any **additional context** to fold into the issue? (optional — design links, code paths, constraints, “already done / gaps”. Press skip for none.)

Merge into the best sections (`Summary` / `Goal`, `Current state`, `Tasks`, `References`). Do not dump unstructured blobs above the template headings.

### Step 4 — Draft

1. Start from the template **body** (everything after the second `---`).
2. Replace `PPT-{NNN}`, placeholders, and HTML `<!-- ... -->` guidance comments with real content (delete leftover guidance comments).
3. Keep required headings from the template — do not invent a parallel outline.
4. Build title:

   - epic: `{semantic}/PPT-{NNN}: [EPIC][{domain}] {title_text}`
   - other: `{semantic}/PPT-{NNN}: [{domain}] {title_text}`
   - bug without PPT only if user insists: `fix: [{domain}] {title_text}` (prefer PPT when it maps to a track)

5. Labels: template defaults + `PPT-{NNN}` when that label exists on the repo. Check with
   `gh label list --limit 200`. Create missing `PPT-{NNN}` only if the user asks.

### Step 5 — Confirm

Show:

- **Type**, **Title**, **Labels**
- Full **body** (or collapsed preview if long)

Ask: create on origin now? **Yes / edit / cancel**.

### Step 6 — Create on origin

```bash
# Write body to a temp file (no secrets). Example:
BODY_FILE="$(mktemp)"
# ... write drafted markdown to $BODY_FILE ...

gh issue create \
  --repo Elmorralito/save-ma-money \
  --title "{TITLE}" \
  --body-file "$BODY_FILE" \
  --label "{labels comma-separated as separate --label flags}"

rm -f "$BODY_FILE"
```

Prefer `--repo Elmorralito/save-ma-money` (or the current `gh` remote) so the issue lands on **origin**, not a fork.

Return the issue **URL** and number. Do not close or edit other issues unless asked.

## Rules

- Interactive first: type → fields → optional context → confirm → create.
- Template structure is SSOT; fill it, don’t replace it.
- Never invent green CI, fake issue numbers, or PPT ids the user didn’t approve.
- Never paste secrets.
- If `gh` auth fails, stop and report — do not pretend the issue was filed.
- Optional: offer a matching brief under `docs/issues/` only when the user asks.

## Additional resources

- [reference.md](reference.md) — field checklist by type + example titles
- Conventions: `.cursor/rules/gen-custom/github_issue_conventions.mdc`
- Briefs index: `docs/issues/README.md`

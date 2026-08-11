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
- [ ] 5. gh auth — login if necessary
- [ ] 6. Preview title + body; user confirms
- [ ] 7. gh issue create on origin; return URL
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

| Field        | Notes                                                                                                             |
| ------------ | ----------------------------------------------------------------------------------------------------------------- |
| `semantic`   | `feat` \| `fix` \| `ops` \| `ci` \| `docs` \| `test` \| `chore` \| `refactor`                                     |
| `PPT-NNN`    | e.g. `PPT-046` — in **title/body** always; epic GitHub label is **`EPIC: PPT-{NNN}`** (children reuse that label) |
| `domain`     | `api` \| `model` \| `infra` \| … (epic title uses `[EPIC][domain]`)                                               |
| `title_text` | Sentence case short title (no semantic/PPT prefix)                                                                |

**epic** — also: step/phase name; parent program (default `#28` PPT-031); summary; out of scope (can be short); blocked-by if known. **Creates** the durable track label `EPIC: PPT-{NNN}` if missing.

**program** — also: parent program (default `#28`); parent epic if any (often `#42`); step; summary; depends/blocks (may be “none”); platform rule note; at least one acceptance criterion. **Do not** create a new epic track label; if linked to a parent epic, apply that epic’s existing `EPIC: PPT-*` label.

**child** — also: **parent epic** (required, e.g. `#42`); program (default `#28`); step number; goal; depends on; blocks (siblings); acceptance criteria. Child has its own `PPT-{NNN}` in the **title/body** only. **Apply the parent epic’s `EPIC: PPT-*` label** (never create a new one for the child id).

**bug** — also: summary; reproduce steps; expected; actual; environment row(s); acceptance (“bug no longer reproduces”). No new epic track label unless the bug is filed as a child of an epic (then reuse `EPIC: PPT-*`).

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

5. Labels (track labels are **epic-scoped**, format **`EPIC: PPT-{NNN}`**):

   | Type        | Labels                                                                                                                                                |
   | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
   | **epic**    | Template defaults + domain + **`EPIC: PPT-{NNN}`**. **Create** the label if missing (`gh label create`) — **only** when type is epic.                 |
   | **child**   | Template defaults + domain + **parent epic’s `EPIC: PPT-*` label** (resolve from parent issue). Do **not** create a label for the child’s own PPT id. |
   | **program** | Template defaults + domain; if a parent epic is set, also apply that epic’s existing `EPIC: PPT-*`. Do **not** create epic track labels.              |
   | **bug**     | `bug` (+ parent epic `EPIC: PPT-*` only if filed under an epic). Do **not** create epic track labels.                                                 |

   Also use existing durable domain labels (`API`, `frontend`, `documentation`, `CI/CD`, …).
   Do **not** also apply a bare `PPT-{NNN}` or a separate `EPIC` label for the track — the
   combined `EPIC: PPT-{NNN}` **is** the epic tag. **Never** create one-off labels for every child
   PPT id — that flooded the repo. Functional PR skips (`skip-strata`, …) are documented in
   [`.github/CI.md`](../../../.github/CI.md#pr-skip-labels); do not invent new skip labels without
   wiring workflow `if:` conditions.

   Resolve parent epic label (child / program with epic):

   ```bash
   gh issue view {EPIC_NUMBER} --repo Elmorralito/save-ma-money --json title,labels \
     --jq '{title: .title, labels: [.labels[].name]}'
   ```

   Prefer an existing label matching `^EPIC: PPT-[0-9]+$` on the epic; else parse `PPT-{NNN}` from
   the epic title and use `EPIC: PPT-{NNN}` **only if that label already exists** (create it only
   when filing a **new** epic). If the parent still has a legacy bare `PPT-*` label, reuse that for
   children until remediated; prefer `EPIC: PPT-*` for new epics. If none exists, ask the user
   whether to create `EPIC: PPT-{NNN}` once — do not invent a child-only label.

### Step 5 — `gh` auth (login if necessary)

Before preview/create, ensure GitHub CLI can reach origin:

```bash
gh auth status
```

- **Logged in** (token valid for `github.com` / the repo host) → continue to step 6.
- **Not logged in**, expired, or missing `repo` / issue scopes → tell the user and run interactive login:

```bash
gh auth login
```

Prefer GitHub.com + HTTPS (or the host this repo’s `gh` remote uses, e.g. if `gh` is configured for a GHES / alias host). Do **not** paste tokens into chat or the issue body.

Re-run `gh auth status` until it succeeds. If the user declines login, **stop** — do not pretend the issue was filed.

Optional after auth: `gh label list --repo Elmorralito/save-ma-money --limit 200` to confirm
domain labels and whether `EPIC: PPT-*` already exists.

### Step 6 — Confirm

Show:

- **Type**, **Title**, **Labels**
- Full **body** (or collapsed preview if long)

Ask: create on origin now? **Yes / edit / cancel**.

### Step 7 — Create on origin

**Epic only — ensure track label exists before create:**

```bash
# Create once per epic track (idempotent if already present)
gh label create "EPIC: PPT-{NNN}" \
  --repo Elmorralito/save-ma-money \
  --color "0E8A16" \
  --description "Epic track PPT-{NNN}" \
  2>/dev/null || true
```

**All types — create the issue:**

```bash
BODY_FILE="$(mktemp)"
# ... write drafted markdown to $BODY_FILE ...

gh issue create \
  --repo Elmorralito/save-ma-money \
  --title "{TITLE}" \
  --body-file "$BODY_FILE" \
  --label enhancement \
  --label "EPIC: PPT-{EPIC_NNN}"   # epic: this epic's id; child/program: parent epic's id only

rm -f "$BODY_FILE"
```

Repeat `--label` for each label (domain, `bug`, etc.). For **child** / linked **program**,
`EPIC: PPT-{EPIC_NNN}` is the **parent epic** track label — not the child’s title PPT id.

Prefer `--repo Elmorralito/save-ma-money` (or the current `gh` remote) so the issue lands on **origin**, not a fork.

Return the issue **URL** and number. Do not close or edit other issues unless asked.

This skill is **independent** of `/plan-issue`. Do not invoke, chain, or suggest
`plan-issue` as part of create-issue. Stop after the issue URL unless the user
explicitly asks for something else.

## Rules

- Interactive first: type → fields → optional context → draft → **gh auth** → confirm → create.
- Template structure is SSOT; fill it, don’t replace it.
- Never invent green CI, fake issue numbers, or PPT ids the user didn’t approve.
- Never paste secrets or `gh` tokens.
- **Epic track GitHub labels use `EPIC: PPT-{NNN}`:** create with `gh label create` **only** when
  filing an **epic**. Children and programs under that epic **reuse** that label; never create a
  new track label for each child id. Child PPT ids stay in the title/body.
- If `gh` auth fails or the user skips login, stop and report — do not pretend the issue was filed.
- Optional: offer a matching brief under `docs/issues/` only when the user asks.

## Additional resources

- [reference.md](reference.md) — field checklist by type + example titles
- Conventions: `.cursor/rules/gen-custom/github_issue_conventions.mdc`
- Briefs index: `docs/issues/README.md`

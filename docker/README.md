# Docker images and Compose

Operator SSOT for **runtime container images** in this monorepo (PPT-067 / [#132](https://github.com/Elmorralito/save-ma-money/issues/132)).

Local B0 still builds from Dockerfiles via Compose (`make api-up` / `make web-up`) — a registry pull is **not** required for day-to-day development.

## Coverage (who owns what)

| Issue                                                                                | Owns                                                                     | Does **not** own                      |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------ | ------------------------------------- |
| [#93](https://github.com/Elmorralito/save-ma-money/issues/93) PPT-045 **closed**     | API **process packaging** (`docker/api/Dockerfile` uvicorn `CMD`)        | Registry publish / release automation |
| [#122](https://github.com/Elmorralito/save-ma-money/issues/122) PPT-057 **closed**   | Web **nginx Compose image** (`docker/web/`)                              | API/model image releases              |
| [#131](https://github.com/Elmorralito/save-ma-money/issues/131) PPT-066              | Language-prefixed **Git tags** (`py-api-v*`, `py-model-v*`, `js-web-v*`) | Container registry images             |
| [#132](https://github.com/Elmorralito/save-ma-money/issues/132) PPT-067 **this doc** | **API image build + GHCR publish** + naming SSOT                         | Helm/K8s; web registry publish; PyPI  |

PyPI wheels for `papita-transactions-model` stay on `publish-model.yml` / `release-model.yml` (PPT-024).

## Locked decisions (PPT-067)

| Topic                 | Decision                                                                                                  |
| --------------------- | --------------------------------------------------------------------------------------------------------- |
| Registry              | **GitHub Container Registry** — `ghcr.io/elmorralito/…`                                                   |
| API image name        | `ghcr.io/elmorralito/save-ma-money-api`                                                                   |
| Stable publish        | **`main` only** (path-relevant push or dispatch `publish` on main). No image publish from git tag events. |
| PR publish            | **Dev channel** tags (`pr-*`, `dev-*`) unless label `skip-api-image-dev`                                  |
| Model packaging       | **A — no standalone model runtime image.** Model is **PyPI-only**; API image vendors model at build.      |
| Model “service” image | **C — rejected**                                                                                          |
| Migrate / Alembic     | Reuse API image with overridden entrypoint (Compose `migrate`).                                           |
| Provenance            | SBOM / cosign deferred (not MVP).                                                                         |
| Multi-arch            | Stable (`main`): `linux/amd64` + `linux/arm64`. PR dev: `linux/amd64` only.                               |
| Vuln gate             | **Trivy** CRITICAL/HIGH before any GHCR push (Environment required reviewers cannot be scanners).         |

### Model = PyPI; API = container

```text
papita-transactions-model  →  PyPI / TestPyPI (wheels)
papita_txnsapi runtime     →  GHCR image (vendors model at image build)
@papita/web nginx          →  Compose/local build today; future GHCR under same naming (not this issue)
```

## Image tags (API)

Image: **`ghcr.io/elmorralito/save-ma-money-api`**

### Stable channel (`main` only)

| Tag                | Meaning                                              |
| ------------------ | ---------------------------------------------------- |
| `edge`             | Moving tip of path-relevant `main` merges            |
| `{semver}`         | `modules/api/pyproject.toml` version at that commit  |
| `py-api-v{semver}` | Same version; aligns with PPT-066 naming             |
| `sha-<12-char>`    | Immutable git commit short SHA — **prefer for pins** |

Git tags such as `py-api-v*` (PPT-066) remain a **source/package** convention; they do **not** trigger image publish. Images are published when the version lands on **`main`**.

### Dev channel (pull requests)

| Tag                    | Meaning                                                       |
| ---------------------- | ------------------------------------------------------------- |
| `pr-<N>`               | Latest successful image for PR `#N` (mutable per synchronize) |
| `pr-<N>-<12-char-sha>` | Immutable image for that PR head                              |
| `dev-<run_id>`         | Unique per Actions run                                        |

Dev publishes **never** write `:edge`, bare `{semver}`, or `:py-api-v*`.

Skip with PR label **`skip-api-image-dev`** (same-repo non-draft PRs only; forks/drafts skipped).

### Pinning for staging / production

Prefer:

1. **Digest** — `…@sha256:…` (Actions summary after stable publish)
2. **`sha-<12-char>`** from `main`
3. Semver / `py-api-v*` — OK with ops discipline; still prefer digest in prod

Do **not** deploy `pr-*` / `dev-*` outside ephemeral PR validation.

### Future web image (convention only)

| Field  | Convention                                                        |
| ------ | ----------------------------------------------------------------- |
| Name   | `ghcr.io/elmorralito/save-ma-money-web`                           |
| Stable | `{semver}`, `js-web-v{semver}`, `sha-<12-char>`, `edge` on `main` |
| Dev    | `pr-<N>` / `pr-<N>-sha` (follow-up)                               |

## CI workflow

| Workflow          | File                                                                                    |
| ----------------- | --------------------------------------------------------------------------------------- |
| Publish API image | [`.github/workflows/publish-api-image.yml`](../.github/workflows/publish-api-image.yml) |
| Smoke helper      | [`.github/scripts/api_image_smoke.sh`](../.github/scripts/api_image_smoke.sh)           |

**Jobs**

| Job           | Permissions / env                              | When                                                                          |
| ------------- | ---------------------------------------------- | ----------------------------------------------------------------------------- |
| `build-smoke` | `contents: read`                               | Dispatch `mode=smoke-only`                                                    |
| `changes`     | `contents: read`                               | Push to `main` — API path detect                                              |
| `publish`     | `packages: write` + Environment **`ghcr`**     | `main`: build → **Trivy gate** → smoke → multi-arch push                      |
| `publish-dev` | `packages: write` + Environment **`ghcr-dev`** | PR: build → **Trivy gate** → smoke → amd64 push (unless `skip-api-image-dev`) |

**Triggers**

| Event                                  | Behavior                                     |
| -------------------------------------- | -------------------------------------------- |
| `push` `main` (API/docker/model paths) | Multi-arch stable tags + amd64 smoke         |
| `pull_request` (same paths)            | Dev tags + amd64 smoke (skippable)           |
| `workflow_dispatch` `smoke-only`       | Local build + smoke; no push                 |
| `workflow_dispatch` `publish`          | Must run on **main**; same as stable publish |

**First-time GHCR / Environments**

1. Set package visibility for `save-ma-money-api` (public recommended).
2. Environments **`ghcr`** (stable; deployment branches limited to `main`) and **`ghcr-dev`** (PR previews).
3. Optional: add a **human** required reviewer on `ghcr` for manual approval after Trivy passes (scanners cannot be Environment reviewers).

## Local B0 (no registry)

```bash
make api-up
make api-image-build
/bin/bash .github/scripts/api_image_smoke.sh papita-api:local
make web-up
```

Compose `migrate` reuses the same API Dockerfile with an Alembic `command` override.

### Optional: pull images

```bash
# Stable (after merge to main)
docker pull ghcr.io/elmorralito/save-ma-money-api:sha-<12-char>
# or digest from Actions summary

# PR preview
docker pull ghcr.io/elmorralito/save-ma-money-api:pr-<N>
```

## Security / supply chain

- Base image digest-pinned; Dependabot watches `/docker/api`.
- Stable publish gated to **main** + Environment `ghcr`.
- PR `packages: write` only pushes `pr-*` / `dev-*` tags (guarded in workflow).
- **Automated image review:** [`.github/actions/trivy-api-image-gate`](../.github/actions/trivy-api-image-gate/action.yml) fails the job on unfixed **CRITICAL/HIGH** findings and uploads SARIF to the Security tab. This is the equivalent of an automated environment “reviewer” — GitHub only allows people/teams as Environment required reviewers.
- Optional: add yourself as a human required reviewer on Environment `ghcr` for an extra manual approval after Trivy passes.
- No secrets in Dockerfiles.
- Cosign / SBOM deferred.

## Layout

| Path                                                           | Role                                          |
| -------------------------------------------------------------- | --------------------------------------------- |
| [`api/Dockerfile`](./api/Dockerfile)                           | API + vendored model; uvicorn `CMD` (PPT-045) |
| [`web/Dockerfile`](./web/Dockerfile)                           | SPA → nginx (PPT-057 / PPT-063)               |
| [`docker-compose.yml`](./docker-compose.yml)                   | B0 full stack                                 |
| [`database/docker-compose.yml`](./database/docker-compose.yml) | Postgres (+ Redis) only                       |
| [`redis/redis.conf`](./redis/redis.conf)                       | Redis config                                  |

## References

- PPT-067 / [#132](https://github.com/Elmorralito/save-ma-money/issues/132)
- PPT-045 / [#93](https://github.com/Elmorralito/save-ma-money/issues/93)
- PPT-057 / [#122](https://github.com/Elmorralito/save-ma-money/issues/122)
- PPT-066 / [#131](https://github.com/Elmorralito/save-ma-money/issues/131)
- [`.github/CI.md`](../.github/CI.md)

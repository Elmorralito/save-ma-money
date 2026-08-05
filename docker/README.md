# Docker images and Compose

Operator SSOT for **runtime container images** in this monorepo (PPT-067 / [#132](https://github.com/Elmorralito/save-ma-money/issues/132)).

Local B0 still builds from Dockerfiles via Compose (`make api-up` / `make web-up`) — a registry pull is **not** required for day-to-day development.

## Coverage (who owns what)

| Issue                                                                                | Owns                                                                     | Does **not** own                      |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------ | ------------------------------------- |
| [#93](https://github.com/Elmorralito/save-ma-money/issues/93) PPT-045 **closed**     | API **process packaging** (`docker/api/Dockerfile` uvicorn `CMD`)        | Registry publish / release automation |
| [#122](https://github.com/Elmorralito/save-ma-money/issues/122) PPT-057 **closed**   | Web **nginx Compose image** (`docker/web/`)                              | Registry publish (now PPT-067)        |
| [#131](https://github.com/Elmorralito/save-ma-money/issues/131) PPT-066              | Language-prefixed **Git tags** (`py-api-v*`, `py-model-v*`, `js-web-v*`) | Container registry images             |
| [#132](https://github.com/Elmorralito/save-ma-money/issues/132) PPT-067 **this doc** | **API + web GHCR publish** + naming SSOT                                 | Helm/K8s; PyPI; upstream DB images    |

PyPI wheels for `papita-transactions-model` stay on `publish-model.yml` / `release-model.yml` (PPT-024).

**Custom images in this repo:** only `docker/api` and `docker/web`. Postgres/Redis use upstream (`postgres:15-alpine`, `redis:7-alpine`). Compose `migrate` reuses the API image.

## Locked decisions (PPT-067)

| Topic                 | Decision                                                                                                  |
| --------------------- | --------------------------------------------------------------------------------------------------------- |
| Registry              | **GitHub Container Registry** — `ghcr.io/elmorralito/…`                                                   |
| API image name        | `ghcr.io/elmorralito/save-ma-money-api`                                                                   |
| Web image name        | `ghcr.io/elmorralito/save-ma-money-web`                                                                   |
| Stable publish        | **`main` only** (path-relevant push or dispatch `publish` on main). No image publish from git tag events. |
| PR publish            | **Dev channel** tags (`pr-*`, `dev-*`) unless skip labels                                                 |
| Model packaging       | **A — no standalone model runtime image.** Model is **PyPI-only**; API image vendors model at build.      |
| Model “service” image | **C — rejected**                                                                                          |
| Migrate / Alembic     | Reuse API image with overridden entrypoint (Compose `migrate`).                                           |
| Provenance            | SBOM / cosign deferred (not MVP); publish builds set `provenance: false` / `sbom: false` for Trivy.       |
| Multi-arch            | Stable (`main`): `linux/amd64` + `linux/arm64`. PR dev: `linux/amd64` only.                               |
| Vuln gate             | **Trivy** CRITICAL/HIGH (rootfs) before any GHCR push.                                                    |

### Model = PyPI; API + web = containers

```text
papita-transactions-model  →  PyPI / TestPyPI (wheels)
papita_txnsapi runtime     →  GHCR save-ma-money-api
@papita/web nginx          →  GHCR save-ma-money-web
Postgres / Redis           →  upstream images (not published by this repo)
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

### Dev channel (pull requests)

| Tag                    | Meaning                                                       |
| ---------------------- | ------------------------------------------------------------- |
| `pr-<N>`               | Latest successful image for PR `#N` (mutable per synchronize) |
| `pr-<N>-<12-char-sha>` | Immutable image for that PR head                              |
| `dev-<run_id>`         | Unique per Actions run                                        |

Skip with PR label **`skip-api-image-dev`**.

## Image tags (Web)

Image: **`ghcr.io/elmorralito/save-ma-money-web`**

Version source: `modules/web/package.json` `version` (bump when you want meaningful semver tags).

### Stable channel (`main` only)

| Tag                | Meaning                                              |
| ------------------ | ---------------------------------------------------- |
| `edge`             | Moving tip of path-relevant `main` merges            |
| `{semver}`         | `@papita/web` package version at that commit         |
| `js-web-v{semver}` | Same version; aligns with PPT-066 naming             |
| `sha-<12-char>`    | Immutable git commit short SHA — **prefer for pins** |

### Dev channel (pull requests)

Same `pr-*` / `dev-*` shape as API. Skip with **`skip-web-image-dev`**.

Dev publishes **never** write `:edge`, bare `{semver}`, `py-api-v*`, or `js-web-v*`.

### Pinning for staging / production

Prefer:

1. **Digest** — `…@sha256:…` (Actions summary after stable publish)
2. **`sha-<12-char>`** from `main`
3. Semver / language-prefixed tags — OK with ops discipline; still prefer digest in prod

Do **not** deploy `pr-*` / `dev-*` outside ephemeral PR validation.

Git tags (`py-api-v*`, `js-web-v*`) remain a **source/package** convention; they do **not** trigger image publish.

## CI workflows

| Workflow              | File                                                                                            |
| --------------------- | ----------------------------------------------------------------------------------------------- |
| Docker Image Security | [`.github/workflows/docker-image-security.yml`](../.github/workflows/docker-image-security.yml) |
| Publish API image     | [`.github/workflows/publish-api-image.yml`](../.github/workflows/publish-api-image.yml)         |
| Publish Web image     | [`.github/workflows/publish-web-image.yml`](../.github/workflows/publish-web-image.yml)         |
| API smoke             | [`.github/scripts/api_image_smoke.sh`](../.github/scripts/api_image_smoke.sh)                   |
| Web smoke             | [`.github/scripts/web_image_smoke.sh`](../.github/scripts/web_image_smoke.sh)                   |
| Hadolint config       | [`.hadolint.yaml`](../.hadolint.yaml)                                                           |

**Image security (every relevant PR / weekly):** Hadolint on both Dockerfiles → build the touched image(s) → Trivy CRITICAL/HIGH (rootfs gate) → smoke. Runs even when GHCR publish is skipped (`skip-*-image-dev`).

**Jobs** (both workflows)

| Job           | Permissions / env                              | When                                                                |
| ------------- | ---------------------------------------------- | ------------------------------------------------------------------- |
| `build-smoke` | `contents: read`                               | Dispatch `mode=smoke-only`                                          |
| `changes`     | `contents: read`                               | Push to `main` — path detect                                        |
| `publish`     | `packages: write` + Environment **`ghcr`**     | `main`: build → **Trivy gate** → smoke → multi-arch push            |
| `publish-dev` | `packages: write` + Environment **`ghcr-dev`** | PR: build → **Trivy gate** → smoke → amd64 push (unless skip label) |

**Triggers**

| Event                            | Behavior                             |
| -------------------------------- | ------------------------------------ |
| `push` `main` (path-relevant)    | Multi-arch stable tags + amd64 smoke |
| `pull_request` (path-filtered)   | Dev tags + amd64 smoke (skippable)   |
| `workflow_dispatch` `smoke-only` | Local build + smoke; no push         |
| `workflow_dispatch` `publish`    | Must run on **main**; stable publish |

**First-time GHCR / Environments**

1. Set package visibility for `save-ma-money-api` and `save-ma-money-web` (often private until first push).
2. Environments **`ghcr`** (stable; deployment branches limited to `main`) and **`ghcr-dev`** (PR previews).
3. Optional: add a **human** required reviewer on `ghcr` after Trivy passes.

## Local B0 (no registry)

```bash
make api-up
make api-image-build
/bin/bash .github/scripts/api_image_smoke.sh papita-api:local
make web-up
make web-image-build
/bin/bash .github/scripts/web_image_smoke.sh papita-web:local
```

Compose `migrate` reuses the same API Dockerfile with an Alembic `command` override.

### Optional: pull images

```bash
# Stable (after merge to main)
docker pull ghcr.io/elmorralito/save-ma-money-api:sha-<12-char>
docker pull ghcr.io/elmorralito/save-ma-money-web:sha-<12-char>

# PR preview
docker pull ghcr.io/elmorralito/save-ma-money-api:pr-<N>
docker pull ghcr.io/elmorralito/save-ma-money-web:pr-<N>
```

## Security / supply chain

- API base digest-pinned; Dependabot watches `/docker/api` and `/docker/web`.
- Stable publish gated to **main** + Environment `ghcr`.
- PR `packages: write` only pushes `pr-*` / `dev-*` tags (guarded in workflow).
- **Automated image review:** [`.github/actions/trivy-api-image-gate`](../.github/actions/trivy-api-image-gate/action.yml) exports rootfs, strips stale third-party SBOMs, fails on unfixed **CRITICAL/HIGH**, uploads SARIF. CI: [`docker-image-security.yml`](../.github/workflows/docker-image-security.yml) (Hadolint + Trivy + smoke per image); publish workflows re-run the Trivy gate pre-push.
- No secrets in Dockerfiles (`VITE_*` bake-time public only for web).
- Cosign deferred.

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

---
trigger: before refreshing docker API/web base digests or Dependabot docker PRs
applies-when: docker/api/**, docker/web/**, modules/web/package.json, pnpm-lock.yaml
origin: failure
---

**Lesson:** When either Dockerfile changes, `docker-image-security` dual-scans API and web images—bump both base digests together, keep `apt-get upgrade` / `apk upgrade` in the Dockerfiles for fixed OS CVEs between digest refreshes, and clear filesystem Trivy (zod in `pnpm-lock.yaml`) before expecting docker/\*\* PRs to go green.

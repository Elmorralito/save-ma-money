---
trigger: before raising python-dateutil to 3.x in Poetry workspaces that install prefect
applies-when: modules/api/pyproject.toml, pyproject.toml, modules/ingestor-core/**
origin: failure
---

**Lesson:** Keep `python-dateutil` on 2.x in this workspace until Poetry can resolve `prefect[client]`; a `>=3.0.0` lower bound alone makes `poetry install` fail with "prefect[client] is listed as a dependency of itself."

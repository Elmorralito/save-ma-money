---
trigger: before wiring or changing /reports endpoints or ReportService
applies-when: modules/api/**/reports*, modules/model/**/services/reports.py
origin: success
---

**Lesson:** Keep every report path tenant-scoped — require JWT `owner=` into `ReportService`, validate optional
`account_id` with `AccountsService.get(..., owner=owner)`, and reject missing owner ids before aggregation. Prefer
`export_format` in Python with `Query(alias="format")` so the public query stays `?format=` without shadowing the
`format` builtin (pylint W0622). Extract cash-flow/trend helpers when pylint R0914 fires instead of broad disables.

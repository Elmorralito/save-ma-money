---
trigger: before wiring or changing /reports endpoints or ReportService
applies-when: modules/api/**/reports*, modules/model/**/services/reports.py
origin: success
---

**Lesson:** Keep every report path tenant-scoped — require JWT `owner=` into `ReportService`, validate optional
`account_id` with `AccountsService.get(..., owner=owner)`, and reject missing owner ids before aggregation. Prefer
`export_format` in Python with `Query(alias="format")` so the public query stays `?format=` without shadowing the
`format` builtin (pylint W0622). Extract cash-flow/trend helpers when pylint R0914 fires instead of broad disables.

Live reports also need (1) `TransactionsService.load_link_services` in API DI so `POST /transactions` can validate
non-null account/category FKs while skipping `template_id=None`, and (2) flattening single-column DAO frames from
`BaseService.get_records` before filtering on `transaction_ts` (use JSON DTO dumps + `pd.to_datetime(..., utc=True)`).

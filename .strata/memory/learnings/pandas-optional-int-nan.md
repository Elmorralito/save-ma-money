---
trigger: before parsing service DataFrames with optional int/date columns into Pydantic DTOs
applies-when: modules/model/**/datautils.py, modules/api/**/schemas/**, list/get_records paths
origin: failure
---

**Lesson:** Sanitize pandas rows with `mapping_without_missing` / `dataframe_row_to_mapping` before
`model_validate`. Mixed int/None columns widen to float64 (`nan`), and Pydantic `ValidationError` is a
`ValueError` subclass → API domain handler returns HTTP 400. Also flatten nested `TableDTO` FKs in
`_relation_uuid` — `LinkedEntitiesService.create` hydrates relations as DTOs, not bare UUIDs.

# Subtask 03.0/04 - Markdown summary and `report.json` provenance

**Task:** [03.0 - Multi-Chart Report Generation](/docs/roadmap/0005-cli-and-storage-enhancements/03.0-multi-chart-report/README.md) ·
**Role:** Python Expert · **Depends on:** 02, 03 · **Status:** ⬜ Not started

## Goal

Write `README.md` (human summary linking every chart and table, with methodology notes and
caveats) and `report.json` (machine-readable provenance), so the directory explains itself.

## Baseline

- `ProviderMetadata.caveats`, `parser_version`; `Database.list_methodology_notes(rating_id)`.
- `write_metadata_sidecar` in `exports/json_export.py` (field naming precedent).

## Files

| Action | Path                                 | Purpose |
|--------|--------------------------------------|---------|
| Modify | `src/langrank/services/report.py`    | `_write_summary()`, `_write_manifest()` |
| Modify | `tests/unit/test_report_service.py`  | Tests below |

## Symbols / fields

| Symbol / key                         | Kind   | Type | Notes |
|--------------------------------------|--------|------|-------|
| `ReportService._write_summary`       | method | `(request, charts, skipped) -> Path` | |
| `ReportService._write_manifest`      | method | `(request, files) -> Path` | |
| `report.json.langrank_version`       | key    | str  | `langrank.__version__` |
| `report.json.schema_version`         | key    | int  | `Database.schema_version()` |
| `report.json.generated_at`           | key    | str  | UTC ISO-8601 |
| `report.json.selection`              | key    | object | `language_ids`, resolved `since`/`until` per rating, endpoint policy (Task 05.0) |
| `report.json.ratings[]`              | key    | array | `rating_id`, `parser_version`, `metrics`, `methodology_notes`, `caveats`, `chart_files` |
| `report.json.skipped_ratings`        | key    | array | |
| `report.json.files`                  | key    | object | relative path → sha256 |

## Behaviour & validators

1. `README.md` sections in order: Title/selection, "How to read this report" (ratings measure
   different things; not comparable across charts), one `## <Rating display name>` per rating with
   chart image links, caveats, and methodology notes **verbatim from the DB**, Coverage table,
   Latest ranks table, Skipped ratings.
2. All links in `README.md` are relative to the report dir so it opens anywhere.
3. `report.json.files` hashes every other file in the report.
4. No derived values are introduced; if any charted row is `is_derived`, the rating section says so.

## Tests

| Test function                                     | File                                | Type | Asserts |
|---------------------------------------------------|-------------------------------------|------|---------|
| `test_report_summary_quotes_db_methodology_notes` | `tests/unit/test_report_service.py` | Unit | Note text from `list_methodology_notes` appears verbatim |
| `test_report_summary_links_resolve`               | `tests/unit/test_report_service.py` | Unit | Every relative link in README.md exists |
| `test_report_manifest_hashes_match_files`         | `tests/unit/test_report_service.py` | Unit | sha256 of each file equals manifest |
| `test_report_summary_has_comparability_warning`   | `tests/unit/test_report_service.py` | Unit | Warning section present |

## Success criteria

- [ ] The report's Markdown summary references the same methodology notes stored in the DB.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Provenance chain invariant ([CLAUDE.md](/CLAUDE.md)); keep manifest keys aligned with the
  Milestone 0004 release `metadata.json` where they overlap.

## Out of scope

- HTML rendering.

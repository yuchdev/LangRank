# Subtask 06.0/05 - Repository read-path & JSON export tests

**Task:** [06.0 - Test Coverage Baseline](/docs/roadmap/0005-cli-and-storage-enhancements/06.0-test-coverage-baseline/README.md) ·
**Role:** Testing Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Cover the `Database` read helpers and `exports/json_export.py` that the CLI tests reach only
indirectly.

## Baseline

- `src/langrank/db/repository.py`: `list_metrics`, `list_methodology_notes`, `list_aliases`,
  `language_suggestions`, `coverage`, `latest_observation_for_provider`, `last_fetch_run`,
  `last_failed_fetch_run`, `count_observations` are uncovered or partly covered.
- `src/langrank/exports/json_export.py`: `export_json_records`, `export_json_nested`,
  `_json_default`, `write_metadata_sidecar`.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Create | `tests/unit/test_repository_reads.py` | repository tests |
| Create | `tests/unit/test_json_export.py` | export tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|--------|------|------------------|---------|-------|
| `populated_db` | pytest fixture | `(tmp_path) -> Database` | - | `Database` with `demo` and `tiobe` fetched through `FetchService` |

## Behaviour & validators

1. `list_methodology_notes("tiobe")` returns the note declared in `TiobeProvider.metadata()` after metadata upsert.
2. `list_aliases(rating_id=None)` includes the global aliases seeded from `LanguageNormalizer.aliases()`.
3. `language_suggestions("pyton")` suggests `python`.
4. `coverage(language_id="python")` rows match `rating_coverage` semantics.
5. JSON records export round-trips (`json.loads`) with ISO dates; the metadata sidecar names its source file and row count.
6. Upserting the same observations twice reports `(0, 0)` the second time (hash-based change detection).

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_list_methodology_notes_after_metadata_upsert` | `tests/unit/test_repository_reads.py` | Integration | rule 1 |
| `test_list_aliases_includes_seeded_globals` | `tests/unit/test_repository_reads.py` | Integration | rule 2 |
| `test_language_suggestions_close_match` | `tests/unit/test_repository_reads.py` | Integration | rule 3 |
| `test_coverage_by_language` | `tests/unit/test_repository_reads.py` | Integration | rule 4 |
| `test_upsert_idempotent_by_hash` | `tests/unit/test_repository_reads.py` | Integration | rule 6 |
| `test_export_json_records_round_trip` | `tests/unit/test_json_export.py` | Unit | rule 5 |
| `test_write_metadata_sidecar_contents` | `tests/unit/test_json_export.py` | Unit | rule 5 |

## Success criteria

- [ ] `src/langrank/db/repository.py` ≥ 88%, `src/langrank/exports/json_export.py` ≥ 90%.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- `tmp_path` databases only.

## Out of scope

- The `methodology_notes` duplicate-row defect - [0003 Task 01.0](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/README.md).

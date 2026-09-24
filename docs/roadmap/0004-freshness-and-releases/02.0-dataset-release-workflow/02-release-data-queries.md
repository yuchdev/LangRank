# Subtask 02.0/02 - Release Data Queries

**Task:** [02.0 - Dataset Release Workflow](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/README.md) ·
**Role:** Python Expert · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Add the `Database` read methods a release needs - full-provenance observation rows in
natural-key order, per-rating coverage with derived counts, acquisition modes, and a
filtered SQLite snapshot - keeping all SQL inside `repository.py`.

## Baseline

- `Database.query_rows` returns `QueryRow` (11 columns, no provenance).
- `Database.coverage(language_id)` groups by rating/language; `provider_versions()` returns
  only `MAX(parser_version)` per rating (loses multiple versions).

## Files

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/langrank/db/repository.py` | New methods below; `ReleaseRow` dataclass |
| Create | `tests/unit/test_release_queries.py` | Query tests on a seeded temp DB |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|---|---|---|---|---|
| `RELEASE_COLUMNS` | constant | `tuple[str, ...]` | - | All `observations` columns except `id`, `fetch_run_id`, in schema order |
| `ReleaseRow` | frozen dataclass | one field per `RELEASE_COLUMNS` entry; `metadata_json: dict[str, Any]` decoded | - | |
| `Database.release_rows` | method | `(*, since: date \| None, until: date \| None, ratings: Sequence[str]) -> list[ReleaseRow]` | - | `ORDER BY rating_id, metric_id, language_id, period_start, granularity` |
| `Database.release_coverage` | method | `(*, since, until, ratings) -> list[sqlite3.Row]` | - | per rating: metrics (group_concat sorted), earliest, latest, count, distinct languages, `SUM(is_derived)` |
| `Database.parser_versions_by_rating` | method | `(*, ratings: Sequence[str]) -> dict[str, list[str]]` | - | All distinct versions, sorted |
| `Database.acquisition_modes_by_rating` | method | `(*, ratings: Sequence[str]) -> dict[str, list[str]]` | - | Union of `raw_artifacts.metadata_json.mode` and `observations.metadata_json.provenance` via `json_extract`, sorted, `NULL`s dropped |
| `Database.write_filtered_snapshot` | method | `(dest: Path, *, since, until, ratings) -> None` | - | `connection.backup(dest_conn)`, then `DELETE` out-of-filter observations/fetch_runs/raw_artifacts in the copy, then `VACUUM` |

## Behaviour & validators

1. Empty `ratings` means all ratings present in `observations`.
2. `since`/`until` filter on `period_start >= since` and `period_end <= until` - the same
   rule as `query_rows`, so a release and an export agree.
3. `write_filtered_snapshot` never mutates the source DB; `raw_artifacts.local_path`
   values are nulled-out to `''` in the copy (paths are machine-local and may leak
   usernames) while `sha256`/`url` stay.
4. `write_filtered_snapshot` refuses to overwrite an existing `dest` (`StorageError`).

## Tests

| Test function | File | Type | Asserts |
|---|---|---|---|
| `test_release_rows_include_provenance_columns` | `tests/unit/test_release_queries.py` | Integration | `parser_version`, `raw_record_hash`, `is_derived` present |
| `test_release_rows_ordered_by_natural_key` | same | Integration | rows sorted by the 5-tuple |
| `test_release_rows_respect_since_until_like_query_rows` | same | Integration | same language/period set as `query_rows` for equal filters |
| `test_parser_versions_by_rating_keeps_all_versions` | same | Integration | two versions → both listed |
| `test_acquisition_modes_by_rating_merges_sources` | same | Integration | modes from artifacts and rows unioned |
| `test_write_filtered_snapshot_leaves_source_untouched` | same | Integration | source row count unchanged; dest filtered; `local_path` blanked |

## Success criteria

- [ ] All SQL lives in `repository.py`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Raw `sqlite3` only; no ORM ([CLAUDE.md](/CLAUDE.md)).
- No schema migration in this subtask.

## Out of scope

- File writing / serialization - [03](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/03-bundle-writers.md).

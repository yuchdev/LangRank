# Subtask 01.0/01 - `latest_language_ranks` view

**Task:** [01.0 - Database Inspection Views](/docs/roadmap/0005-cli-and-storage-enhancements/01.0-database-inspection-views/README.md) ·
**Role:** Python Expert · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Add a SQL view `latest_language_ranks` that returns, for every rating and every rank-unit
metric, the full ranking table of that metric's **latest published period** - i.e. the
"current ranking" a user would see on the source's website.

## Baseline

- `src/langrank/db/migrations.py:MIGRATIONS` (versions 1-2), `SCHEMA_VERSION = 2`.
- `latest_observations` (migration 1) is latest-per-language, not latest-per-metric; do not
  change it.

## Files

| Action | Path                                   | Purpose                                              |
|--------|----------------------------------------|------------------------------------------------------|
| Modify | `src/langrank/db/migrations.py`        | Append migration tuple creating the view; bump `SCHEMA_VERSION` |
| Create | `tests/unit/test_inspection_views.py`  | Unit tests for this view (file shared with 02-04)    |

## Symbols / fields

| Symbol                              | Kind      | Type / signature | Default | Notes |
|-------------------------------------|-----------|------------------|---------|-------|
| `SCHEMA_VERSION`                    | constant  | `int`            | next free version | Bumped to the new migration number |
| `MIGRATIONS[n]`                     | tuple     | `(int, str)`     | -       | `CREATE VIEW IF NOT EXISTS latest_language_ranks AS …` |
| view column `rating_id`             | column    | TEXT             | -       | |
| view column `metric_id`             | column    | TEXT             | -       | |
| view column `period_start`          | column    | TEXT (ISO date)  | -       | The metric's latest `period_start` |
| view column `period_label`          | column    | TEXT             | -       | |
| view column `rank`                  | column    | INTEGER          | -       | From `observations.rank` |
| view column `language_id`           | column    | TEXT             | -       | |
| view column `display_name`          | column    | TEXT             | -       | Joined from `languages` |
| view column `source_language_name`  | column    | TEXT             | -       | Original source label (provenance) |
| view column `is_derived`            | column    | INTEGER (0/1)    | -       | |
| view column `source_url`            | column    | TEXT             | -       | |

## Behaviour & validators

1. Rank metrics are selected by `o.unit = 'rank'` (not by metric ID - IDs are provider-prefixed).
2. "Latest" is `MAX(period_start)` **per `(rating_id, metric_id)`**, not per language - a language
   absent from the latest edition does not appear (no stale carry-forward).
3. Rows with `rank IS NULL` are excluded (the view is a ranking table; values-only rows belong in
   `latest_observations`).
4. The view has no `ORDER BY` baked in except as documented usage; consumers order by
   `rating_id, metric_id, rank`.
5. Migration is append-only: migration 1 and 2 SQL text is byte-for-byte unchanged.

## Tests

| Test function                                       | File                                  | Type | Asserts |
|-----------------------------------------------------|---------------------------------------|------|---------|
| `test_latest_language_ranks_uses_latest_period_per_metric` | `tests/unit/test_inspection_views.py` | Unit | Two periods seeded; only the newer period's rows returned |
| `test_latest_language_ranks_excludes_language_missing_from_latest` | `tests/unit/test_inspection_views.py` | Unit | A language present only in the older period is absent |
| `test_latest_language_ranks_selects_rank_unit_only`  | `tests/unit/test_inspection_views.py` | Unit | Percent-unit rows (e.g. `pypl-share`) are excluded; `pypl-rank` included |
| `test_schema_version_matches_last_migration`         | `tests/unit/test_inspection_views.py` | Unit | `Database.schema_version() == SCHEMA_VERSION == MIGRATIONS[-1][0]` |

## Success criteria

- [ ] `sqlite3 <db> "select * from latest_language_ranks limit 5"` works after `langrank fetch demo`.
- [ ] Works for a provider-prefixed rank metric (`tiobe-rank`), not only `demo`'s `rank`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Append-only migrations ([CLAUDE.md](/CLAUDE.md) § Storage); tests must not hard-code the
  migration number.
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- A CLI command over this view - the report ([Task 03.0](/docs/roadmap/0005-cli-and-storage-enhancements/03.0-multi-chart-report/README.md)) consumes it.
- First-class metric roles (Milestone 0006 Task 01.0).

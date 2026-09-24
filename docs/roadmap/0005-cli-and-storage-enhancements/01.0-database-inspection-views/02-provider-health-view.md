# Subtask 01.0/02 - `provider_health` view

**Task:** [01.0 - Database Inspection Views](/docs/roadmap/0005-cli-and-storage-enhancements/01.0-database-inspection-views/README.md) ·
**Role:** Python Expert · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Add a SQL view `provider_health` with one row per registered rating summarising fetch history
and data presence, so `sqlite3` alone can answer "which providers are fetched, failing, or
empty?".

## Baseline

- Tables `ratings`, `fetch_runs` (`status` ∈ `success`/`failed`/`dry-run` per
  `models.FetchRunStatus`), `observations` from migration 1.
- `Database.last_fetch_run`, `last_failed_fetch_run`, `count_observations`,
  `latest_observation_for_provider`, `provider_versions` compute the same facts in Python for
  `StatusService`; the view is the SQL-only equivalent and must agree with them.

## Files

| Action | Path                                  | Purpose                                            |
|--------|---------------------------------------|----------------------------------------------------|
| Modify | `src/langrank/db/migrations.py`       | Append migration creating `provider_health`; bump `SCHEMA_VERSION` |
| Modify | `tests/unit/test_inspection_views.py` | Tests below                                        |

## Symbols / fields

| Symbol                                | Kind   | Type            | Default | Notes |
|---------------------------------------|--------|-----------------|---------|-------|
| view column `rating_id`               | column | TEXT            | -       | From `ratings.id` (LEFT JOIN base) |
| view column `display_name`            | column | TEXT            | -       | |
| view column `observation_count`       | column | INTEGER         | 0       | `COUNT(o.id)`, 0 when never fetched |
| view column `language_count`          | column | INTEGER         | 0       | Distinct `language_id` |
| view column `earliest_period`         | column | TEXT \| NULL    | NULL    | `MIN(period_start)` |
| view column `latest_period`           | column | TEXT \| NULL    | NULL    | `MAX(period_start)` - matches `latest_observation_for_provider` |
| view column `parser_version`          | column | TEXT \| NULL    | NULL    | `MAX(parser_version)` - matches `provider_versions` |
| view column `derived_count`           | column | INTEGER         | 0       | Rows with `is_derived = 1` |
| view column `last_fetch_started_at`   | column | TEXT \| NULL    | NULL    | Latest `fetch_runs.started_at` any status |
| view column `last_fetch_status`       | column | TEXT \| NULL    | NULL    | Status of that run |
| view column `last_success_at`         | column | TEXT \| NULL    | NULL    | Latest `started_at` with `status = 'success'` |
| view column `last_failure_at`         | column | TEXT \| NULL    | NULL    | Latest `started_at` with `status = 'failed'` |

## Behaviour & validators

1. Base relation is `ratings` (LEFT JOIN), so a rating with zero observations and zero runs
   appears with counts 0 and NULL dates.
2. Aggregations over `observations` and `fetch_runs` are done in separate sub-selects to avoid a
   row-multiplying join (count must equal `Database.count_observations`).
3. `dry-run` runs count toward `last_fetch_*` but never toward `last_success_at`.
4. No freshness/"stale" judgement in SQL - upstream freshness is Milestone 0004 Task 01.0.

## Tests

| Test function                                       | File                                  | Type | Asserts |
|-----------------------------------------------------|---------------------------------------|------|---------|
| `test_provider_health_lists_unfetched_rating`       | `tests/unit/test_inspection_views.py` | Unit | Rating with metadata only → `observation_count = 0`, dates NULL |
| `test_provider_health_counts_match_repository`      | `tests/unit/test_inspection_views.py` | Unit | `observation_count`, `latest_period`, `parser_version` equal `Database.count_observations` / `latest_observation_for_provider` / `provider_versions` |
| `test_provider_health_separates_success_and_failure` | `tests/unit/test_inspection_views.py` | Unit | Seed success then failed run → `last_fetch_status='failed'`, both timestamps set |
| `test_provider_health_no_join_multiplication`        | `tests/unit/test_inspection_views.py` | Unit | 3 runs × N observations still yields `observation_count = N` |

## Success criteria

- [ ] `sqlite3 <db> "select * from provider_health"` returns one row per `ratings` row.
- [ ] Counts agree with the `Database` methods `StatusService` uses.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Append-only migrations; do not hard-code the migration number in tests.
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- Rewiring `StatusService` to read the view (optional follow-up; not required).
- Upstream freshness ([Milestone 0004](/docs/roadmap/0004-freshness-and-releases/plan.md)).

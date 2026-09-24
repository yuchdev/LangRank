# Task 01.0 - Database Inspection Views

**Milestone:** [0005 - CLI & Storage Enhancements](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md) ·
**Spec source:** [plan.md § Task 01.0](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#task-010---database-inspection-views) ·
**Category:** storage · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                            | Role           | Depends on | Status         |
|----|------------------------------------------------------------------------------------------------------------------------------------|----------------|------------|----------------|
| 01 | [`latest_language_ranks` view](/docs/roadmap/0005-cli-and-storage-enhancements/01.0-database-inspection-views/01-latest-language-ranks-view.md) | Python Expert  | -          | ⬜ Not started |
| 02 | [`provider_health` view](/docs/roadmap/0005-cli-and-storage-enhancements/01.0-database-inspection-views/02-provider-health-view.md)               | Python Expert  | -          | ⬜ Not started |
| 03 | [Provenance columns in `language_history`](/docs/roadmap/0005-cli-and-storage-enhancements/01.0-database-inspection-views/03-language-history-provenance.md) | Python Expert  | -          | ⬜ Not started |
| 04 | [Plain-`sqlite3` smoke tests for all five views](/docs/roadmap/0005-cli-and-storage-enhancements/01.0-database-inspection-views/04-view-smoke-tests.md) | Testing Expert | 01, 02, 03 | ⬜ Not started |
| 05 | [Document the views in `docs/data-model.md`](/docs/roadmap/0005-cli-and-storage-enhancements/01.0-database-inspection-views/05-view-documentation.md) | Docs Writer    | 01, 02, 03 | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

Make the SQLite database fully inspectable with the plain `sqlite3` shell - without running
application code or decoding `metadata_json` blobs - by completing the set of five views the
plan names (`latest_observations`, `latest_language_ranks`, `language_history`,
`rating_coverage`, `provider_health`) and exposing enough provenance in them that a user can
tell raw from derived values at a glance.

## Baseline (what already exists)

- `src/langrank/db/migrations.py` migration **1** already creates `latest_observations`,
  `language_history`, and `rating_coverage`. `SCHEMA_VERSION = 2` (migration 2 adds
  `methodology_notes`).
- `Database.coverage()` (`src/langrank/db/repository.py`) already reads `rating_coverage`.
- `language_history` today exposes only `rating_id, metric_id, language, period_start,
  period_end, value, rank, unit` - no `is_derived`, `derivation_method`, `parser_version`, or
  `source_url`, so it silently drops the provenance trail the project treats as its core
  invariant.
- `latest_observations` is "latest per language" - a language that fell out of a ranking still
  shows its last (stale) rank. That is fine for that view, but it is the wrong semantics for
  "current ranking table", which is why `latest_language_ranks` must be "latest period per
  rating+metric".
- Only `observations.unit = 'rank'` reliably identifies rank metrics: metric IDs are
  provider-prefixed (`tiobe-rank`, `pypl-rank`, `redmonk-rank`, `stackoverflow-survey-rank`) and
  only `demo` uses bare `rank`.

## Design notes

- **Only add, never edit migration 1.** New views and the `language_history` redefinition are
  new append-only tuples in `MIGRATIONS` (`DROP VIEW IF EXISTS …; CREATE VIEW …`). Each subtask
  takes the **next free integer version at implementation time** (3 at time of writing; other
  milestones - e.g. 0003 - also append migrations, so never hard-code the number in tests; assert
  `schema_version() == SCHEMA_VERSION` instead) and bumps `SCHEMA_VERSION`.
- **Rank detection by unit, not ID.** Views select rank metrics with `unit = 'rank'` - the only
  signal that is correct for every provider today. Milestone 0006 Task 01.0 (provider
  capabilities / metric roles) may later give a first-class metric role; the views can switch
  then.
- **Views never compute derived values.** They only project and filter stored rows; every view
  that returns observation values also returns `is_derived`.

### Open questions

- Should `provider_health` include ratings with zero observations? **Default: yes** (LEFT JOIN
  from `ratings`), so a registered-but-never-fetched provider is visible.

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] Each of the five views answers `sqlite3 <db-path> "select * from <view> limit 5"` with no
      application code running.
- [ ] Views are added as versioned entries in `db/migrations.py`; migration 1 is unchanged.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- [docs/data-model.md](/docs/data-model.md)
- [Milestone 0006 plan](/docs/roadmap/0006-provider-extensibility/plan.md) - Task 01.0 capabilities metadata.
- [CLAUDE.md](/CLAUDE.md) § Storage (append-only migrations).

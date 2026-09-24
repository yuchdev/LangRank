# Subtask 01.0/03 - Provenance columns in `language_history`

**Task:** [01.0 - Database Inspection Views](/docs/roadmap/0005-cli-and-storage-enhancements/01.0-database-inspection-views/README.md) ·
**Role:** Python Expert · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Redefine the existing `language_history` view (via a new migration) so it carries the
provenance columns needed to tell raw from derived values and trace each row to its source,
without changing any existing column name or meaning.

## Baseline

- Migration 1 defines `language_history` as
  `rating_id, metric_id, language (canonical_name), period_start, period_end, value, rank, unit`.
- No application code reads `language_history` today (`grep -rn language_history src` finds only
  the migration) - redefinition is safe.

## Files

| Action | Path                                  | Purpose                                                    |
|--------|---------------------------------------|------------------------------------------------------------|
| Modify | `src/langrank/db/migrations.py`       | Append migration: `DROP VIEW IF EXISTS language_history; CREATE VIEW language_history AS …`; bump `SCHEMA_VERSION` |
| Modify | `tests/unit/test_inspection_views.py` | Tests below                                                |

## Symbols / fields

Existing columns kept in the same order first: `rating_id, metric_id, language, period_start,
period_end, value, rank, unit`. Appended columns:

| Column                  | Type          | Notes |
|-------------------------|---------------|-------|
| `language_id`           | TEXT          | `o.language_id` (join key for other views) |
| `display_name`          | TEXT          | `l.display_name` |
| `period_label`          | TEXT          | |
| `granularity`           | TEXT          | `year` / `month` |
| `source_language_name`  | TEXT          | Original label as published |
| `is_derived`            | INTEGER (0/1) | |
| `derivation_method`     | TEXT \| NULL  | |
| `parser_version`        | TEXT          | |
| `source_url`            | TEXT          | |
| `source_document_id`    | TEXT \| NULL  | |
| `retrieved_at`          | TEXT          | |

## Behaviour & validators

1. The migration is new and append-only; migration 1's text is untouched (the old definition
   still runs on fresh DBs and is immediately replaced by the new migration).
2. Existing column names/semantics are preserved so any external `sqlite3` script keeps working.
3. The view projects stored values only - no computed or interpolated columns.

## Tests

| Test function                                     | File                                  | Type | Asserts |
|---------------------------------------------------|---------------------------------------|------|---------|
| `test_language_history_keeps_legacy_columns_first` | `tests/unit/test_inspection_views.py` | Unit | `PRAGMA table_info(language_history)` first 8 names equal the legacy list |
| `test_language_history_exposes_provenance`        | `tests/unit/test_inspection_views.py` | Unit | A seeded `is_derived=1` row reads back `is_derived=1`, `derivation_method`, `parser_version`, `source_url` |
| `test_language_history_upgrade_from_v2_db`        | `tests/unit/test_inspection_views.py` | Unit | Build a DB with only migrations ≤2 applied, then `migrate()` → view has new columns, data intact |

## Success criteria

- [ ] `sqlite3 <db> "select language, is_derived, parser_version from language_history limit 5"` works.
- [ ] An existing v2 database upgrades cleanly.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Provenance chain invariant ([CLAUDE.md](/CLAUDE.md)): a user-facing view must not hide
  `is_derived`.
- Append-only migrations.

## Out of scope

- Changing `latest_observations` or `rating_coverage` (already expose `o.*` / aggregates).

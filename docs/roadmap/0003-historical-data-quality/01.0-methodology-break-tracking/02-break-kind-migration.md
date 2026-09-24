# Subtask 01.0/02 - Break-kind schema migration & model fields

**Task:** [01.0 - Methodology Break Tracking](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Extend `methodology_notes` and `MethodologyNote` with break classification, metric scope, and
announcement date via a new append-only migration.

## Baseline

- `MIGRATIONS` in `src/langrank/db/migrations.py` ends at version 2; `SCHEMA_VERSION = 2`.
- `MethodologyNote` (frozen dataclass) has `rating_id`, `methodology_version`, `valid_from`,
  `valid_to`, `description`, `source_url`.

## Files

| Action | Path                                   | Purpose                                              |
|--------|----------------------------------------|------------------------------------------------------|
| Modify | `src/langrank/db/migrations.py`        | Append `(N, sql)` with `ALTER TABLE methodology_notes ADD COLUMN ...`; bump `SCHEMA_VERSION` |
| Modify | `src/langrank/models.py`               | Add `BreakKind` enum and new `MethodologyNote` fields |
| Modify | `src/langrank/db/repository.py`        | Read/write the new columns in `upsert_provider_metadata` and `list_methodology_notes` |
| Create | `tests/unit/test_migrations.py`        | Migration tests (create if absent; other tasks append) |
| Modify | `tests/unit/test_methodology_notes.py` | Create: round-trip tests                              |

`N` is the next unused integer at merge time (3 on current master). Coordinate with
[Task 02.0/02](/docs/roadmap/0003-historical-data-quality/02.0-language-lifecycle-and-alias-validity/02-lifecycle-catalog-and-migration.md)
and [Milestone 0005 Task 01.0](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#task-010---database-inspection-views),
which also append migrations.

## Symbols / fields

| Symbol                              | Kind    | Type / signature                         | Default               | Notes |
|-------------------------------------|---------|------------------------------------------|-----------------------|-------|
| `BreakKind`                         | enum    | `StrEnum`: `INITIAL="initial"`, `METHOD_CHANGE="method_change"`, `SOURCE_CHANGE="source_change"`, `COVERAGE_CHANGE="coverage_change"`, `WORDING_CHANGE="wording_change"` | - | in `models.py` |
| `MethodologyNote.break_kind`        | field   | `BreakKind`                              | `BreakKind.INITIAL`   | keyword field after `source_url` |
| `MethodologyNote.affects_metrics`   | field   | `tuple[str, ...]`                        | `()`                  | `()` = all metrics of the rating |
| `MethodologyNote.announced_at`      | field   | `date \| None`                            | `None`                | |
| `methodology_notes.break_kind`      | column  | `TEXT NOT NULL`                          | `'initial'`           | |
| `methodology_notes.affects_metrics` | column  | `TEXT NOT NULL` (JSON array)             | `'[]'`                | |
| `methodology_notes.announced_at`    | column  | `TEXT`                                   | `NULL`                | ISO date |
| `SCHEMA_VERSION`                    | const   | `int`                                    | `N`                   | |

## Behaviour & validators

1. Migration uses `ALTER TABLE ... ADD COLUMN` only; migrations 1-2 are byte-for-byte unchanged.
2. Existing rows get `break_kind='initial'`, `affects_metrics='[]'` via column defaults.
3. `affects_metrics` is serialized with `json.dumps(sorted(...))` and parsed back to a tuple.
4. An unknown `break_kind` string read from the DB raises `StorageError` (not a silent default).

## Tests

| Test function                                   | File                                   | Type        | Asserts |
|-------------------------------------------------|----------------------------------------|-------------|---------|
| `test_migration_adds_methodology_break_columns` | `tests/unit/test_migrations.py`        | Integration | `PRAGMA table_info(methodology_notes)` lists the 3 columns; `schema_version() == N` |
| `test_migration_preserves_existing_notes`       | `tests/unit/test_migrations.py`        | Integration | a v2 DB with a note migrates; row gets `initial`/`[]` |
| `test_methodology_note_roundtrip_new_fields`    | `tests/unit/test_methodology_notes.py` | Integration | upsert + `list_methodology_notes` preserves `break_kind`, `affects_metrics`, `announced_at` |
| `test_unknown_break_kind_raises_storage_error`  | `tests/unit/test_methodology_notes.py` | Integration | manual bad row → `StorageError` |

## Success criteria

- [ ] New migration tuple appended with the next integer version; `SCHEMA_VERSION` matches.
- [ ] All four tests exist and pass.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Append-only migrations ([CLAUDE.md](/CLAUDE.md) § Storage). `Database` stays the only SQL owner.
- Frozen dataclasses; new fields have defaults so existing provider code compiles unchanged.

## Out of scope

- Changing the unique key / update semantics ([subtask 03](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/03-methodology-note-sync.md)).

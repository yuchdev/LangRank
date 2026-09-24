# Subtask 01.0/03 - Methodology-note sync semantics in `upsert_provider_metadata`

**Task:** [01.0 - Methodology Break Tracking](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/README.md) ·
**Role:** Python Expert · **Depends on:** 02 · **Status:** ⬜ Not started

## Goal

Make `(rating_id, methodology_version)` the logical identity of a note so that editing a
note's bounds in provider metadata updates it instead of leaving a stale duplicate segment.

## Baseline

- `Database.upsert_provider_metadata` inserts notes with
  `ON CONFLICT(rating_id, methodology_version, valid_from, valid_to) DO UPDATE`. Changing
  `valid_to` from `''` to `2024-12-31` therefore inserts a second row for the same version.
- SQLite cannot drop a table-level `UNIQUE` constraint with `ALTER TABLE`; the key is kept.

## Files

| Action | Path                                   | Purpose                                     |
|--------|----------------------------------------|---------------------------------------------|
| Modify | `src/langrank/db/repository.py`        | Replace per-note upsert with `_sync_methodology_notes(connection, metadata)` |
| Modify | `tests/unit/test_methodology_notes.py` | Sync tests                                  |

## Symbols / fields

| Symbol                               | Kind   | Type / signature                                                         | Default | Notes |
|--------------------------------------|--------|--------------------------------------------------------------------------|---------|-------|
| `Database._sync_methodology_notes`   | method | `(connection: sqlite3.Connection, metadata: ProviderMetadata) -> None`   | -       | called inside the existing transaction |

## Behaviour & validators

1. Within one transaction: for every declared note, delete rows with the same
   `(rating_id, methodology_version)` whose bounds differ, then insert/update the declared row.
2. Rows for versions the provider no longer declares are **kept** (history is not deleted by
   omission); they are reported by the quality check `methodology_orphan_note`
   ([Task 03.0/05](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/05-temporal-and-provenance-checks.md)).
3. Declaring the same `methodology_version` twice in one `ProviderMetadata` raises
   `ProviderError("duplicate methodology_version ...")`.
4. Metadata upsert remains idempotent: calling it twice yields identical rows.

## Tests

| Test function                                     | File                                   | Type        | Asserts |
|---------------------------------------------------|----------------------------------------|-------------|---------|
| `test_changing_valid_to_updates_single_row`       | `tests/unit/test_methodology_notes.py` | Integration | one row per version after bounds edit |
| `test_undeclared_version_is_retained`             | `tests/unit/test_methodology_notes.py` | Integration | omitted version still listed |
| `test_duplicate_version_in_metadata_raises`       | `tests/unit/test_methodology_notes.py` | Unit        | `ProviderError` |
| `test_metadata_upsert_idempotent`                 | `tests/unit/test_methodology_notes.py` | Integration | same row set after 2 calls |

## Success criteria

- [ ] No two rows share `(rating_id, methodology_version)` after any sequence of upserts.
- [ ] All four tests pass.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- No migration needed; do not edit migration 2.
- Deletion only targets the same `(rating_id, methodology_version)`; never other versions.

## Out of scope

- Querying observations by segment ([subtask 04](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/04-methodology-segment-queries.md)).

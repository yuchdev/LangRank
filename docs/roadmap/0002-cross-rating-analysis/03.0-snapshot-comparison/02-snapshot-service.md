# Subtask 03.0/02 - `SnapshotService`

**Task:** [03.0 - Snapshot Comparison](/docs/roadmap/0002-cross-rating-analysis/03.0-snapshot-comparison/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Build the language × rating snapshot table from stored observations using the selection rules,
with explicit blank cells, per-column reference dates, and a deterministic row order.

## Baseline

- `select_reference_period`, `rows_at_period`, `latest_dates_disagree` (subtask 01).
- `resolve_rank_metric`, `Database.query_analysis_rows`, `Database.list_ratings`,
  `Database.list_metrics` (01.0/01 and existing repository).

## Files

| Action | Path                                       | Purpose                              |
|--------|--------------------------------------------|--------------------------------------|
| Create | `src/langrank/services/snapshot.py`        | Request/table types + `SnapshotService` |
| Create | `tests/unit/test_snapshot_service.py`      | Service tests on `multi_rating_database` |

## Symbols / fields

| Symbol                           | Kind      | Type / signature                                                                                 | Default | Notes |
|----------------------------------|-----------|--------------------------------------------------------------------------------------------------|---------|-------|
| `SnapshotRequest`                | dataclass | frozen                                                                                           | -       | |
| `SnapshotRequest.target`         | field     | `SnapshotTarget`                                                                                 | -       | |
| `SnapshotRequest.rating_ids`     | field     | `list[str]`                                                                                      | `[]`    | Empty → every rating with stored observations |
| `SnapshotRequest.metric_overrides` | field   | `dict[str, str]`                                                                                 | `{}`    | |
| `SnapshotRequest.language_ids`   | field     | `list[str]`                                                                                      | `[]`    | |
| `SnapshotRequest.top`            | field     | `int \| None`                                                                                    | `None`  | |
| `SnapshotRequest.sort_by`        | field     | `str \| None`                                                                                    | `None`  | A `rating_id` in the table |
| `SnapshotColumn`                 | dataclass | frozen: `rating_id: str`, `metric_id: str`, `reference: ReferencePeriod \| None`                 | -       | `None` → no observation for target |
| `SnapshotCell`                   | dataclass | frozen: `rank: int \| None`, `value: float \| None`, `period_label: str`, `period_start: date`, `source_url: str`, `is_derived: bool`, `derivation_method: str \| None` | - | |
| `SnapshotRow`                    | dataclass | frozen: `language_id: str`, `display_name: str`, `cells: dict[str, SnapshotCell \| None]`         | -       | Key = `rating_id`; every column key present |
| `SnapshotTable`                  | dataclass | frozen: `target: SnapshotTarget`, `columns: list[SnapshotColumn]`, `rows: list[SnapshotRow]`, `notes: list[str]` | - | |
| `SnapshotService.__init__`       | method    | `(self, database: Database) -> None`                                                             | -       | |
| `SnapshotService.snapshot`       | method    | `(self, request: SnapshotRequest) -> SnapshotTable`                                              | -       | |

## Behaviour & validators

1. **Ratings.** Explicit `rating_ids` are validated (unknown → `AnalysisError`) and always appear as
   columns, even if blank. Defaulted ratings: every rating in `list_ratings()` whose
   `count_observations > 0` **and** has a resolvable rank metric; ratings skipped for either
   reason are listed in `notes`.
2. **Per column:** resolve rank metric → read `query_analysis_rows(rating_id, metric_id)` (full
   history; selection handles the window) → `select_reference_period` → `rows_at_period`.
   `reference is None` → note `"<rating>: no observation in <Y>"`.
3. **Languages.** Explicit `language_ids` → exactly those rows (all-blank rows kept).
   `top=N` → languages with `rank <= N` in at least one column. Neither → union of languages
   present in any column. `language_ids` and `top` together → `AnalysisError`.
4. **Cells.** `SnapshotCell` copied from the selected `AnalysisRow`; missing → `None`. No
   computed ranks, no re-ranking among the displayed subset.
5. **Order.** `sort_by` given → by that column's rank ascending, blanks last, ties by
   `display_name`; `sort_by` not a column → `AnalysisError`. Otherwise by `display_name`.
6. **Notes** also include: `"dates differ between columns"` when `latest_dates_disagree`; one
   note per column with a `date_note`; and for PYPL: `"pypl reports C and C++ as the combined
   category c-cpp"` when `c`, `c++` or `c-cpp` rows are present.
7. Read-only: no writes.

## Tests

| Test function                                           | File                                   | Type        | Asserts |
|---------------------------------------------------------|----------------------------------------|-------------|---------|
| `test_snapshot_year_cells_come_from_that_year`          | `tests/unit/test_snapshot_service.py`  | Integration | Every non-blank cell's `period_start.year == 2020` |
| `test_snapshot_latest_uses_latest_per_source`           | `tests/unit/test_snapshot_service.py`  | Integration | Each column's reference = that rating's max period |
| `test_snapshot_missing_cell_is_none`                    | `tests/unit/test_snapshot_service.py`  | Integration | `c++` row has `cells["pypl"] is None`; `c-cpp` row has pypl rank |
| `test_snapshot_explicit_rating_without_data_is_blank_column` | `tests/unit/test_snapshot_service.py` | Integration | Target 1999 → column `reference is None`, note present |
| `test_snapshot_top_n_uses_any_column`                   | `tests/unit/test_snapshot_service.py`  | Integration | `top=1` → union of each column's rank-1 language |
| `test_snapshot_sort_by_rating_blanks_last`              | `tests/unit/test_snapshot_service.py`  | Integration | Ordering rule 5 |
| `test_snapshot_rejects_languages_and_top_together`      | `tests/unit/test_snapshot_service.py`  | Unit        | `AnalysisError` |

## Success criteria

- [ ] `SnapshotService.snapshot` produces only stored values or `None` cells, each with its true
      period.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Business logic in the service, not `cli.py`.
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- Rendering - [03-snapshot-cli.md](/docs/roadmap/0002-cross-rating-analysis/03.0-snapshot-comparison/03-snapshot-cli.md).

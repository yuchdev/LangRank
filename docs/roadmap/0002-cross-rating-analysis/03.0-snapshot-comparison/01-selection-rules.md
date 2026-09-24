# Subtask 03.0/01 - Snapshot Selection Rules

**Task:** [03.0 - Snapshot Comparison](/docs/roadmap/0002-cross-rating-analysis/03.0-snapshot-comparison/README.md) ·
**Role:** Python Expert · **Depends on:** 01.0/01 · **Status:** ⬜ Not started

## Goal

Pure functions that turn a snapshot target (`YYYY` or `latest`) and one rating's rows into a
reference period plus the rows observed at exactly that period - with an explicit "date note"
whenever the chosen date could surprise a reader.

## Baseline

- `AnalysisRow` (`src/langrank/db/repository.py`, from 01.0/01), `AnalysisError`.
- `Granularity.YEAR` / `Granularity.MONTH` only.

## Files

| Action | Path                                         | Purpose                                     |
|--------|----------------------------------------------|---------------------------------------------|
| Create | `src/langrank/analysis/selection.py`         | Target parsing + reference-period selection |
| Modify | `src/langrank/analysis/__init__.py`          | Re-export                                   |
| Create | `tests/unit/test_analysis_selection.py`      | Rule tests on literal rows                  |

## Symbols / fields

| Symbol                              | Kind      | Type / signature                                                                        | Default | Notes |
|-------------------------------------|-----------|-----------------------------------------------------------------------------------------|---------|-------|
| `SnapshotTargetKind`                | StrEnum   | `YEAR = "year"`, `LATEST = "latest"`                                                    | -       | |
| `SnapshotTarget`                    | dataclass | frozen: `kind: SnapshotTargetKind`, `year: int \| None`                                 | -       | `year` set iff `kind is YEAR` |
| `parse_snapshot_target`             | function  | `(value: str) -> SnapshotTarget`                                                        | -       | `"latest"` (case-insensitive) or 4-digit year 1990..2100; else `AnalysisError` |
| `ReferencePeriod`                   | dataclass | frozen: `rating_id: str`, `metric_id: str`, `period_start: date`, `period_end: date`, `period_label: str`, `granularity: Granularity`, `date_note: str \| None` | - | |
| `select_reference_period`           | function  | `(rows: Sequence[AnalysisRow], target: SnapshotTarget) -> ReferencePeriod \| None`     | -       | Rows must share one `rating_id`/`metric_id` |
| `rows_at_period`                    | function  | `(rows: Sequence[AnalysisRow], period: ReferencePeriod) -> dict[str, AnalysisRow]`     | -       | Keyed by `language_id` |
| `latest_dates_disagree`             | function  | `(periods: Sequence[ReferencePeriod]) -> bool`                                          | -       | True if reference years differ |

## Behaviour & validators

1. `select_reference_period` raises `AnalysisError` if `rows` span more than one
   `(rating_id, metric_id)`; returns `None` for empty rows.
2. **YEAR Y:** candidates = rows with `Y-01-01 <= period_start <= Y-12-31`; none → `None`
   (the column will be blank). Reference = max candidate `period_start`. **Never** consider
   `Y-1`/`Y+1`.
3. **LATEST:** reference = max `period_start` over all rows.
4. **Granularity consistency:** if rows at the reference `period_start` have more than one
   `granularity` → `AnalysisError` (would indicate two series under one metric).
5. **`date_note`** (string shown to users, else `None`):
   - `MONTH` granularity and YEAR target and reference month ≠ 12 →
     `"latest <rating> observation in <Y> is <period_label>"`.
   - LATEST target → always `"as of <period_label>"` (the date must be visible in `latest` mode).
6. `rows_at_period` returns only rows whose `period_start == period.period_start` and
   `granularity == period.granularity`; a language with no row there is simply absent (blank
   cell). No fallback to other periods.
7. Pure module: no DB, no I/O.

## Tests

| Test function                                              | File                                     | Type | Asserts |
|------------------------------------------------------------|------------------------------------------|------|---------|
| `test_parse_snapshot_target_year_and_latest`               | `tests/unit/test_analysis_selection.py`  | Unit | `"2020"` → YEAR 2020; `"LATEST"` → LATEST |
| `test_parse_snapshot_target_rejects_garbage`               | `tests/unit/test_analysis_selection.py`  | Unit | `"20"`, `"2020-06"`, `"next"` → `AnalysisError` |
| `test_select_year_picks_latest_period_in_year`             | `tests/unit/test_analysis_selection.py`  | Unit | Monthly rows Jan..Dec 2020 → Dec 2020, `date_note is None` |
| `test_select_year_semiannual_notes_date`                   | `tests/unit/test_analysis_selection.py`  | Unit | RedMonk-like Jan+Jun 2020 → Jun 2020 with `date_note` |
| `test_select_year_annual_source`                           | `tests/unit/test_analysis_selection.py`  | Unit | Year-granularity 2020 row → chosen, no note |
| `test_select_year_never_borrows_adjacent_year`             | `tests/unit/test_analysis_selection.py`  | Unit | Rows only in 2019 and 2021, target 2020 → `None` |
| `test_rows_at_period_leaves_missing_language_blank`        | `tests/unit/test_analysis_selection.py`  | Unit | Language present in Nov but not Dec → absent from result |
| `test_select_latest_always_has_date_note`                  | `tests/unit/test_analysis_selection.py`  | Unit | LATEST → note `"as of ..."` |
| `test_select_rejects_mixed_rating_rows`                    | `tests/unit/test_analysis_selection.py`  | Unit | Two ratings → `AnalysisError` |

## Success criteria

- [ ] Selection never uses an observation outside the target year (YEAR mode) and never mixes
      periods within one column.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- No interpolation, no nearest-neighbour borrowing ([CLAUDE.md](/CLAUDE.md) § Conventions).
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- An `--as-of DATE` target (latest observation ≤ date) - possible follow-up; not required by plan.md.

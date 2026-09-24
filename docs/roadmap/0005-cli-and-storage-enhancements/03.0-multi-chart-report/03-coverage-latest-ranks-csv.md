# Subtask 03.0/03 - Coverage, latest ranks and CSV subset

**Task:** [03.0 - Multi-Chart Report Generation](/docs/roadmap/0005-cli-and-storage-enhancements/03.0-multi-chart-report/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Write the report's tabular data files: the observation subset behind the charts, per-rating
coverage for the selected languages, and each rating's latest ranks for them.

## Baseline

- `export_csv(rows, output)` in `exports/csv_export.py`.
- `Database.coverage(language_id)`; `latest_language_ranks` view (Task 01.0/01).

## Files

| Action | Path                                 | Purpose |
|--------|--------------------------------------|---------|
| Modify | `src/langrank/services/report.py`    | `_write_data_files()` |
| Modify | `src/langrank/db/repository.py`      | `latest_ranks(language_ids, rating_ids) -> list[sqlite3.Row]` reading `latest_language_ranks` |
| Modify | `tests/unit/test_report_service.py`  | Tests below |

## Symbols / fields

| Symbol                               | Kind   | Type / signature | Default | Notes |
|--------------------------------------|--------|------------------|---------|-------|
| `Database.latest_ranks`              | method | `(language_ids: Sequence[str], rating_ids: Sequence[str] = ()) -> list[sqlite3.Row]` | - | Only SQL site for the view |
| `ReportService._write_data_files`    | method | `(request: ReportRequest, rows: list[QueryRow]) -> list[Path]` | - | |
| `data/observations.csv`              | file   | same columns as `export_csv` | - | Exactly the rows charted |
| `data/coverage.csv`                  | file   | `rating_id, language_id, earliest, latest, points` | - | |
| `data/latest_ranks.csv`              | file   | `rating_id, metric_id, period_label, language_id, rank` | - | Missing language = no row |

## Behaviour & validators

1. `observations.csv` contains exactly the rows passed to chart rendering (same query, same window).
2. A language absent from a rating's latest edition has no row in `latest_ranks.csv` - never a
   blank/zero rank filled in.
3. Coverage is computed per selected language via `Database.coverage(language_id)`.

## Tests

| Test function                                  | File                                | Type | Asserts |
|------------------------------------------------|-------------------------------------|------|---------|
| `test_report_observations_csv_matches_charted_rows` | `tests/unit/test_report_service.py` | Unit | Row count/keys equal the charted rows |
| `test_report_latest_ranks_omits_absent_language` | `tests/unit/test_report_service.py` | Unit | No fabricated row |
| `test_report_coverage_per_language`            | `tests/unit/test_report_service.py` | Unit | One row per (rating, language) with data |
| `test_database_latest_ranks_filters`           | `tests/unit/test_inspection_views.py` | Unit | Filters by language and rating |

## Success criteria

- [ ] All three CSVs written and deterministic (sorted).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- `Database` is the only SQL site ([CLAUDE.md](/CLAUDE.md) § Storage).

## Out of scope

- JSON exports of the same data.

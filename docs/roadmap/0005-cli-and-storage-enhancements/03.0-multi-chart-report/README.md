# Task 03.0 - Multi-Chart Report Generation

**Milestone:** [0005 - CLI & Storage Enhancements](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md) ·
**Spec source:** [plan.md § Task 03.0](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#task-030---multi-chart-report-generation) ·
**Category:** cli · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                             | Role           | Depends on        | Status         |
|----|-------------------------------------------------------------------------------------------------------------------------------------|----------------|-------------------|----------------|
| 01 | [`ReportService` skeleton and output layout](/docs/roadmap/0005-cli-and-storage-enhancements/03.0-multi-chart-report/01-report-service-skeleton.md) | Python Expert  | -                 | ⬜ Not started |
| 02 | [Per-rating charts](/docs/roadmap/0005-cli-and-storage-enhancements/03.0-multi-chart-report/02-per-rating-charts.md)                              | Python Expert  | 01, 02.0/01-03    | ⬜ Not started |
| 03 | [Coverage, latest ranks and CSV subset](/docs/roadmap/0005-cli-and-storage-enhancements/03.0-multi-chart-report/03-coverage-latest-ranks-csv.md)    | Python Expert  | 01                | ⬜ Not started |
| 04 | [Markdown summary and `report.json` provenance](/docs/roadmap/0005-cli-and-storage-enhancements/03.0-multi-chart-report/04-markdown-summary-and-provenance.md) | Python Expert  | 02, 03            | ⬜ Not started |
| 05 | [`langrank report` command and acceptance test](/docs/roadmap/0005-cli-and-storage-enhancements/03.0-multi-chart-report/05-report-cli-and-acceptance.md) | Testing Expert | 04                | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

`langrank report --languages python,c++,rust --years 10 --output report/` produces a
self-contained directory - one chart per rating, a coverage table, latest ranks, methodology
notes, a CSV data subset, and a Markdown summary - openable without the CLI.

## Start gate

Do **not** start until (a) [Task 02.0](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/README.md)
subtasks 01-03 are ✅ (figure builder, rank fix, gap-aware lines) and (b)
[Milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md) is complete, per the plan.
Specs below are written so the gate only affects *which ratings appear*, not the code shape -
the report iterates over whatever `ProviderRegistry.all()` returns that has data.

## Baseline (what already exists)

- `PlotService` (after Task 02.0: `build_figure(rows, PlotOptions)`).
- `exports/csv_export.py:export_csv`, `exports/json_export.py:write_metadata_sidecar`.
- `Database.coverage(language_id)`, `list_methodology_notes(rating_id)`, `list_metrics(rating_id)`.
- `latest_language_ranks` view from [Task 01.0](/docs/roadmap/0005-cli-and-storage-enhancements/01.0-database-inspection-views/README.md)
  (soft: subtask 03 may fall back to `QueryService` if 01.0 has not landed).
- Selection window resolution from [Task 05.0](/docs/roadmap/0005-cli-and-storage-enhancements/05.0-historical-selection-semantics/README.md)
  (soft: until it lands, `--years` uses current `QueryService` semantics and the report records
  the resolved `since/until` it actually used).

## Design notes

- **One chart per rating, never a shared axis.** Each rating's default metric (and its rank
  metric, if distinct) gets its own PNG. The Markdown summary places charts sequentially with a
  sentence that ratings measure different things (link README methodology warning).
- **Business logic in `services/report.py`**, CLI is a thin wrapper (CLAUDE.md § Services).
- **Missing data stays missing:** a rating with no rows for the selected languages/window gets a
  "no observations in window" line in the summary - no empty chart, no filler.
- **Deterministic output** (sorted ratings/languages, stable filenames) so reports diff cleanly.

### Open questions

- HTML output? **Default: no** - Markdown + PNG only; HTML is a later flag if requested.

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] Report directory is self-contained and its Markdown summary quotes the same methodology notes
      stored in the DB (Milestone 0003 table / current `methodology_notes`).
- [ ] Fixture-driven acceptance test of the report directory passes.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- [plan.md § Plotting invariants](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#plotting-invariants)
- [Milestone 0003 Task 01.0](/docs/roadmap/0003-historical-data-quality/plan.md#task-010---methodology-break-tracking)
- [Milestone 0004 Task 02.0](/docs/roadmap/0004-freshness-and-releases/plan.md#task-020---dataset-release-workflow) (similar provenance manifest; keep field names aligned)

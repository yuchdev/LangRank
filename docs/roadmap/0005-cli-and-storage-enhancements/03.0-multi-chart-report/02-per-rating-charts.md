# Subtask 03.0/02 - Per-rating charts

**Task:** [03.0 - Multi-Chart Report Generation](/docs/roadmap/0005-cli-and-storage-enhancements/03.0-multi-chart-report/README.md) ·
**Role:** Python Expert · **Depends on:** 01, 02.0/01-03 · **Status:** ⬜ Not started

## Goal

Write one PNG per (rating, metric) for the requested languages - default metric plus rank metric
where they differ - each on its own axes.

## Baseline

- `PlotService.build_figure(rows, PlotOptions)` and rank/gap fixes from Task 02.0.
- `ProviderMetadata.default_metric`, `metrics` (with `unit`) describe what to chart.

## Files

| Action | Path                                 | Purpose |
|--------|--------------------------------------|---------|
| Modify | `src/langrank/services/report.py`    | `_render_charts()` |
| Modify | `tests/unit/test_report_service.py`  | Tests below |

## Symbols / fields

| Symbol                           | Kind   | Type / signature | Default | Notes |
|----------------------------------|--------|------------------|---------|-------|
| `ReportService._charts_for_rating` | method | `(metadata: ProviderMetadata) -> list[MetricDefinition]` | - | Default metric + first `unit == "rank"` metric, de-duplicated |
| `ReportService._render_charts`   | method | `(request: ReportRequest) -> tuple[list[Path], list[str]]` | - | Returns written files and skipped rating IDs |
| chart filename                   | convention | `charts/{rating_id}--{metric_id}.png` | - | Deterministic |

## Behaviour & validators

1. Each chart is a separate figure containing rows of exactly one `rating_id` (asserted in code:
   `len({r.rating_id for r in rows}) == 1`, else `LangRankError`).
2. A rating with zero rows in the window is skipped (no file) and listed in `skipped_ratings`.
3. Charts use default `PlotOptions` (gap-aware, rank inverted, no smoothing).
4. Figures are closed after save.

## Tests

| Test function                                 | File                                | Type | Asserts |
|-----------------------------------------------|-------------------------------------|------|---------|
| `test_report_one_chart_per_rating_metric`     | `tests/unit/test_report_service.py` | Unit | Two ratings seeded → expected filenames only |
| `test_report_chart_never_mixes_ratings`       | `tests/unit/test_report_service.py` | Unit | Spy on `build_figure`: every call's rows have one `rating_id` |
| `test_report_skips_rating_without_rows`       | `tests/unit/test_report_service.py` | Unit | No PNG; ID in `skipped_ratings` |
| `test_report_rank_chart_inverted`             | `tests/unit/test_report_service.py` | Unit | Spy figure's axes inverted for rank metric |

## Success criteria

- [ ] No report chart ever contains two ratings.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- No shared axis across ratings ([CLAUDE.md](/CLAUDE.md)).

## Out of scope

- Normalized cross-rating charts (Milestone 0002).

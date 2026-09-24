# Subtask 01.0/03 - `ComparisonService`

**Task:** [01.0 - Cross-Rating Normalization & Comparison](/docs/roadmap/0002-cross-rating-analysis/01.0-cross-rating-normalization/README.md) ·
**Role:** Python Expert · **Depends on:** 01, 02 · **Status:** ⬜ Not started

## Goal

Orchestrate a cross-rating comparison: resolve each rating's rank metric and time window,
read the **full** per-period population from the DB, normalize it, then keep only the
requested languages - returning derived series per rating with warnings, exclusions and
explicit gaps.

## Baseline

- `src/langrank/services/query.py:QueryService.resolve_filters` - resolves `--years`/`--since`
  into a concrete `since`/`until` for one rating (latest-per-source endpoint via
  `Database.resolve_year_bounds`).
- `Database.query_analysis_rows`, `resolve_rank_metric` (subtask 01); `NormalizationMethod`,
  `NormalizationOptions` (subtask 02).

## Files

| Action | Path                                         | Purpose                                  |
|--------|----------------------------------------------|------------------------------------------|
| Create | `src/langrank/services/comparison.py`        | `ComparisonRequest`, `ComparisonResult`, `ComparisonService` |
| Create | `tests/unit/test_comparison_service.py`      | Service behaviour against `multi_rating_database` |

## Symbols / fields

| Symbol                                 | Kind      | Type / signature                                                                       | Default | Notes |
|----------------------------------------|-----------|----------------------------------------------------------------------------------------|---------|-------|
| `ComparisonRequest`                    | dataclass | frozen                                                                                 | -       | |
| `ComparisonRequest.language_ids`       | field     | `list[str]`                                                                            | -       | ≥ 1 |
| `ComparisonRequest.rating_ids`         | field     | `list[str]`                                                                            | -       | ≥ 2, unique |
| `ComparisonRequest.method`             | field     | `str`                                                                                  | -       | CLI name, e.g. `rank-percentile` |
| `ComparisonRequest.metric_overrides`   | field     | `dict[str, str]`                                                                       | `{}`    | From `--metric-map` |
| `ComparisonRequest.options`            | field     | `NormalizationOptions`                                                                 | default | |
| `ComparisonRequest.since / until`      | fields    | `date \| None`                                                                         | `None`  | |
| `ComparisonRequest.years`              | field     | `int \| None`                                                                          | `None`  | Resolved **per rating** |
| `ComparisonSeries`                     | dataclass | frozen: `rating_id: str`, `metric_id: str`, `window: tuple[date \| None, date \| None]`, `points: list[NormalizedPoint]` | - | |
| `ComparisonResult`                     | dataclass | frozen: `method_id: str`, `series: list[ComparisonSeries]`, `excluded: list[ExcludedRow]`, `warnings: list[str]`, `missing: list[tuple[str, str]]` | - | `missing` = `(rating_id, language_id)` with zero points |
| `ComparisonService.__init__`           | method    | `(self, database: Database) -> None`                                                   | -       | |
| `ComparisonService.compare`            | method    | `(self, request: ComparisonRequest) -> ComparisonResult`                               | -       | |

## Behaviour & validators

1. Request validation (`AnalysisError`): fewer than 2 ratings, duplicate ratings, empty
   `language_ids`, unknown rating (`Database.get_rating` is `None`), a `metric_overrides` key not
   in `rating_ids`.
2. Per rating: `metric_id = resolve_rank_metric(rating_id, database.list_metrics(rating_id),
   request.metric_overrides.get(rating_id))`.
3. Per rating window: build a `QueryFilters(rating_id=..., metric_id=..., since, until, years)`
   and call `QueryService.resolve_filters`; use the resolved `since`/`until`. The service must not
   re-implement `--years` arithmetic (single source of truth, see
   [Milestone 0005 Task 05.0](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#task-050---historical-selection-semantics)).
4. Read `database.query_analysis_rows(rating_id=..., metric_id=..., since=..., until=...)`
   **without** `language_ids` (full population), normalize, **then** filter points to
   `request.language_ids`. This keeps the `max_rank` fallback honest.
5. A requested language with no points in a rating → appended to `missing`; no synthetic point.
   PYPL's combined `c-cpp` category is not split: comparing `c++` against `pypl` yields a
   `missing` entry, plus a warning `"pypl reports C/C++ as combined category 'c-cpp'"` when the
   requested language is `c` or `c++`.
6. Warnings from each rating's `NormalizationResult` are concatenated in rating order;
   `excluded` rows are filtered to the requested languages.
7. The service performs **no writes**: `observations` row count is unchanged after `compare`.

## Tests

| Test function                                           | File                                    | Type        | Asserts |
|---------------------------------------------------------|-----------------------------------------|-------------|---------|
| `test_compare_returns_one_derived_series_per_rating`    | `tests/unit/test_comparison_service.py` | Integration | `tiobe,pypl,redmonk` → 3 series; all points `is_derived` |
| `test_compare_population_uses_all_languages_not_selection` | `tests/unit/test_comparison_service.py` | Integration | Score for python identical whether 1 or all languages requested |
| `test_compare_resolves_window_per_rating`               | `tests/unit/test_comparison_service.py` | Integration | `years=3` → each series' `window` ends at that rating's latest year |
| `test_compare_missing_language_is_reported_not_zeroed`  | `tests/unit/test_comparison_service.py` | Integration | `c++` vs `pypl` → in `missing`, no pypl points, warning mentions `c-cpp` |
| `test_compare_rejects_single_rating`                    | `tests/unit/test_comparison_service.py` | Unit        | One rating → `AnalysisError` |
| `test_compare_does_not_persist_normalized_values`       | `tests/unit/test_comparison_service.py` | Integration | `count_observations` per rating unchanged; no `is_derived=1` rows added |

## Success criteria

- [ ] `ComparisonService.compare` returns per-rating derived series using `QueryService` window
      resolution and full-population normalization.
- [ ] Missing data is reported in `missing`, never filled.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Business logic lives here, not in `cli.py` ([CLAUDE.md](/CLAUDE.md) § Services).
- Read-only against SQLite.
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- Rendering/CLI - [04-plot-compare-cli.md](/docs/roadmap/0002-cross-rating-analysis/01.0-cross-rating-normalization/04-plot-compare-cli.md).
- Composite scores - [Task 02.0](/docs/roadmap/0002-cross-rating-analysis/02.0-composite-index/README.md).

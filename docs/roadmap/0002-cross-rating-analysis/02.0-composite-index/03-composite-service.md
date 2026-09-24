# Subtask 02.0/03 - `CompositeService` & Year Alignment

**Task:** [02.0 - Composite Index](/docs/roadmap/0002-cross-rating-analysis/02.0-composite-index/README.md) ·
**Role:** Python Expert · **Depends on:** 02, 01.0/03, 03.0/01 · **Status:** ⬜ Not started

## Goal

Read each rating, normalize it on its native periods, pick one normalized point per rating per
year with the snapshot selection rule, and hand the aligned inputs to `compute_composite`.

## Baseline

- `ComparisonService` internals (01.0/03): per-rating metric resolution, window resolution via
  `QueryService.resolve_filters`, full-population normalization.
- `select_reference_period`, `rows_at_period` (03.0/01).
- `compute_composite` (subtask 02).

## Files

| Action | Path                                       | Purpose                                         |
|--------|--------------------------------------------|-------------------------------------------------|
| Create | `src/langrank/services/composite.py`       | `CompositeRequest`, `CompositeService`          |
| Modify | `src/langrank/services/comparison.py`      | Extract `normalize_rating(...)` helper shared by both services |
| Create | `tests/unit/test_composite_service.py`     | Service tests on `multi_rating_database`        |

## Symbols / fields

| Symbol                                   | Kind      | Type / signature                                                                                   | Default | Notes |
|------------------------------------------|-----------|----------------------------------------------------------------------------------------------------|---------|-------|
| `normalize_rating`                       | function  | `(database: Database, *, rating_id: str, metric_id: str, method: NormalizationMethod, options: NormalizationOptions, since: date \| None, until: date \| None) -> NormalizationResult` | - | Moved out of `ComparisonService`; behaviour unchanged |
| `CompositeRequest`                       | dataclass | frozen: `spec: CompositeSpec`, `language_ids: list[str]`, `top: int \| None`, `since: date \| None`, `until: date \| None`, `years: int \| None`, `options: NormalizationOptions` | - | |
| `CompositeService.__init__`              | method    | `(self, database: Database) -> None`                                                               | -       | |
| `CompositeService.compute`               | method    | `(self, request: CompositeRequest) -> CompositeResult`                                             | -       | |
| `_align_by_year`                         | function  | `(points: Sequence[NormalizedPoint], years: Sequence[int]) -> dict[tuple[str, int], NormalizedPoint]` | -    | Uses `select_reference_period` semantics |

## Behaviour & validators

1. Metric per rating: `resolve_rank_metric` when `spec.metric_selector == "rank"`, else the map
   entry (validated to exist in `list_metrics`).
2. Window: resolved per rating via `QueryService.resolve_filters`; the **year grid** is the
   union of years covered by any rating's window, clipped to the explicit `since`/`until` if
   given.
3. Normalization on native periods with the full population (same as 01.0/03 rule 4).
4. **Alignment:** for each rating and year `Y`, the reference period is the latest normalized
   period in `Y` (same rule as `select_reference_period` with a YEAR target); a language's point
   is taken only from that reference period - never from an earlier month. No averaging.
5. Languages: explicit `language_ids`; or `top=N` → languages whose composite rank ≤ N in the
   **latest** year of the grid (computed over all languages, then filtered); or all languages
   with at least one point. `language_ids` with `top` → `AnalysisError`.
6. Warnings from normalization and `spec.warnings` are merged into `CompositeResult.warnings`.
7. Read-only; no persistence.

## Tests

| Test function                                           | File                                    | Type        | Asserts |
|---------------------------------------------------------|-----------------------------------------|-------------|---------|
| `test_composite_service_plan_example_runs`              | `tests/unit/test_composite_service.py`  | Integration | `tiobe,pypl,redmonk,stackoverflow-survey`, `rank`, `rank-percentile`, `1,1,1,2`, `require-all` → points exist, all labelled |
| `test_composite_alignment_uses_latest_period_in_year`   | `tests/unit/test_composite_service.py`  | Integration | TIOBE contribution `source_period_label` is `YYYY-12` |
| `test_composite_alignment_does_not_average_months`      | `tests/unit/test_composite_service.py`  | Integration | Contribution score equals that single month's `rank_percentile` |
| `test_composite_cpp_with_pypl_require_all_is_gap`       | `tests/unit/test_composite_service.py`  | Integration | `c++` + `pypl` under `require-all` → gaps only |
| `test_composite_service_does_not_persist`               | `tests/unit/test_composite_service.py`  | Integration | Observation counts unchanged |
| `test_comparison_service_unchanged_after_refactor`      | `tests/unit/test_composite_service.py`  | Integration | `ComparisonService.compare` output equal before/after `normalize_rating` extraction (golden) |

## Success criteria

- [ ] Composite inputs trace to single stored observations (period visible per contribution).
- [ ] 01.0/03 tests still pass unchanged after the helper extraction.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- No hidden averaging, no interpolation ([plan.md § shared conventions](/docs/roadmap/0002-cross-rating-analysis/plan.md#no-hidden-averaging--no-silent-interpolation)).
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- Monthly/sub-annual composite grids.
- Plotting a composite series (a single derived axis - may follow once
  [Milestone 0005 Task 02.0](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#task-020---improved-plotting-options) lands).

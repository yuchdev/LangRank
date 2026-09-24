# Subtask 01.0/05 - `minmax` / `zscore` Methods (Deferrable)

**Task:** [01.0 - Cross-Rating Normalization & Comparison](/docs/roadmap/0002-cross-rating-analysis/01.0-cross-rating-normalization/README.md) ·
**Role:** Python Expert · **Depends on:** 02 · **Status:** ⬜ Not started

## Goal

Add the two "later, additive" value-metric normalizations named in plan.md, registered next to
`rank_percentile` without changing it. May be deferred; the task can close without it.

## Baseline

- `NormalizationMethod`, `NORMALIZATION_METHODS`, `NormalizedPoint`, `MetricKind` (subtask 02).
- `MetricDefinition.higher_is_better` (`src/langrank/models.py`) - value metrics such as
  `tiobe-rating`, `pypl-share`, `worked_with_percent` are all `higher_is_better=True`.

## Files

| Action | Path                                         | Purpose                         |
|--------|----------------------------------------------|---------------------------------|
| Modify | `src/langrank/analysis/normalization.py`     | `MinMax`, `ZScore`, registry    |
| Modify | `src/langrank/services/comparison.py`        | Resolve a **value** metric when method `applies_to == VALUE` |
| Modify | `src/langrank/analysis/metrics.py`           | `resolve_value_metric` (default metric if its unit ≠ `rank`) |
| Create | `tests/unit/test_analysis_value_methods.py`  | Math tests                      |

## Symbols / fields

| Symbol                  | Kind     | Type / signature                                                                        | Default | Notes |
|-------------------------|----------|-----------------------------------------------------------------------------------------|---------|-------|
| `MinMax`                | class    | `method_id="minmax"`, `cli_name="minmax"`, `applies_to=MetricKind.VALUE`                | -       | |
| `ZScore`                | class    | `method_id="zscore"`, `cli_name="zscore"`, `applies_to=MetricKind.VALUE`                | -       | |
| `resolve_value_metric`  | function | `(rating_id: str, metrics: Sequence[MetricDefinition], default_metric: str, override: str \| None = None) -> str` | - | Interim; same 0006/01.0 caveat as `resolve_rank_metric` |

## Behaviour & validators

1. Both methods group rows exactly like `rank_percentile` (per rating/metric/period) and use only
   rows with `value is not None`; others excluded with reason `"no value"`.
2. `minmax`: `score = (v - min) / (max - min)`; `max == min` → every row excluded with reason
   `"zero range"` (no fabricated 0.5).
3. `zscore`: population standard deviation; `std == 0` → excluded `"zero variance"`. Scores are
   unbounded; `plot compare` sets the y-label to `"z-score (derived)"` and does not clamp.
4. `higher_is_better=False` metrics are negated before scaling; the derivation label records it:
   `"minmax[orientation=inverted]"`.
5. The population is **only stored rows** (the tracked subset), stated in the derivation label:
   `"minmax[population=stored_rows;k=<count>]"`, and a warning is emitted per rating.
6. Rank-unit rows passed to these methods → `AnalysisError`.

## Tests

| Test function                                     | File                                         | Type | Asserts |
|---------------------------------------------------|----------------------------------------------|------|---------|
| `test_minmax_known_values`                        | `tests/unit/test_analysis_value_methods.py`  | Unit | `[10, 20, 30]` → `[0, 0.5, 1]` |
| `test_minmax_zero_range_excludes`                 | `tests/unit/test_analysis_value_methods.py`  | Unit | Equal values → no points, `excluded` reason `"zero range"` |
| `test_zscore_known_values`                        | `tests/unit/test_analysis_value_methods.py`  | Unit | `[1, 2, 3]` → `[-1.2247, 0, 1.2247]` (±1e-4) |
| `test_value_methods_invert_lower_is_better`       | `tests/unit/test_analysis_value_methods.py`  | Unit | Label contains `orientation=inverted` |
| `test_value_methods_reject_rank_rows`             | `tests/unit/test_analysis_value_methods.py`  | Unit | `unit="rank"` → `AnalysisError` |

## Success criteria

- [ ] `--normalize minmax|zscore` accepted by `plot compare`; `rank_percentile` output unchanged
      (its tests still pass untouched).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Additive only - no change to `RankPercentile` or its tests.
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- Using these methods in `composite` beyond what Task 02.0's method validation already allows.

# Subtask 03.0/04 - Value checks (discontinuities, suspicious percentages)

**Task:** [03.0 - Data Quality Dashboard](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/README.md) ·
**Role:** Python Expert · **Depends on:** 02 · **Status:** ⬜ Not started

## Goal

Implement `abrupt_discontinuities` and `suspicious_percentages`.

## Baseline

- `percentage_range` in `validation_queries()` already catches values outside 0..100 per row;
  sums across languages are not checked.
- Multi-select sources (Stack Overflow survey, future `stackoverflow-tags` `question_share`)
  legitimately sum above 100 %.

## Files

| Action | Path                                  | Purpose |
|--------|---------------------------------------|---------|
| Modify | `src/langrank/db/repository.py`       | `quality_series()`, `quality_share_sums()` |
| Modify | `src/langrank/services/quality.py`    | two `CHECKS` entries; `DEFAULT_THRESHOLDS`; `EXCLUSIVE_SHARE_METRICS` |
| Create | `tests/unit/test_quality_values.py`   | tests |

## Symbols / fields

| Symbol                          | Kind   | Type / signature                                                          | Default | Notes |
|---------------------------------|--------|---------------------------------------------------------------------------|---------|-------|
| `Database.quality_series`       | method | `(rating_id: str \| None) -> list[sqlite3.Row]` ordered by series then `period_start` | - | |
| `Database.quality_share_sums`   | method | `(metric_ids: set[str]) -> list[sqlite3.Row]` — `SUM(value)` per rating/metric/period | - | |
| `DEFAULT_THRESHOLDS`            | const  | `{"rank_jump": 10.0, "relative_change": 0.5, "share_sum_tolerance": 0.5}` | -       | overridable via `QualityContext.thresholds` |
| `EXCLUSIVE_SHARE_METRICS`       | const  | `frozenset({"tiobe-rating", "pypl-share"})`                               | -       | interim allowlist; replaced by metric metadata in 0006 Task 01.0 |
| `abrupt_discontinuities`        | check  | WARNING                                                                   | -       | consecutive observed periods only; rank metrics via `rank_metric_ids()` |
| `suspicious_percentages`        | check  | WARNING                                                                   | -       | exclusive metrics whose per-period sum > 100 + tolerance |

## Behaviour & validators

1. Discontinuity compares consecutive *observed* points; a gap resets comparison (no interpolation across gaps).
2. A discontinuity at a methodology break date is still flagged, with `detail["at_methodology_break"]=True` when [Task 01.0](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/README.md) data is available.
3. Relative change skipped when previous value is 0 or `None`.
4. Multi-select metrics are never flagged for sums > 100 %.

## Tests

| Test function                                      | File                                | Type        | Asserts |
|----------------------------------------------------|-------------------------------------|-------------|---------|
| `test_rank_jump_flagged`                           | `tests/unit/test_quality_values.py` | Integration | |
| `test_threshold_override_suppresses_finding`       | `tests/unit/test_quality_values.py` | Integration | `rank_jump=25` → none |
| `test_gap_resets_discontinuity_comparison`         | `tests/unit/test_quality_values.py` | Integration | |
| `test_exclusive_share_sum_over_100_flagged`        | `tests/unit/test_quality_values.py` | Integration | |
| `test_multiselect_share_sum_not_flagged`           | `tests/unit/test_quality_values.py` | Integration | `worked_with_percent` |
| `test_value_checks_silent_on_clean_baseline`       | `tests/unit/test_quality_values.py` | Integration | |

## Success criteria

- [ ] All six tests pass.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Never "corrects" values; flags only.

## Out of scope

- Metric-role metadata (0006 Task 01.0).

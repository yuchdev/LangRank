# Subtask 01.0/04 - Observation ↔ methodology segment queries & validation

**Task:** [01.0 - Methodology Break Tracking](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/README.md) ·
**Role:** Python Expert · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

Let `ValidationService` report, per rating, which observations fall within each methodology
version, and flag overlapping segments and observations covered by no segment.

## Baseline

- `ValidationService.validate()` turns every row from `Database.validation_queries()` into an
  ERROR issue; there is no per-rating methodology view.
- Observation dates are ISO strings (`period_start`, `period_end`); note bounds use `''` for open.

## Files

| Action | Path                                         | Purpose |
|--------|----------------------------------------------|---------|
| Modify | `src/langrank/models.py`                     | Add `MethodologySegment` |
| Modify | `src/langrank/db/repository.py`              | Add `methodology_segments()`, `methodology_version_for()`, overlap/uncovered queries |
| Modify | `src/langrank/services/validation.py`        | Add `methodology_coverage()`; extend `validate()` |
| Create | `tests/unit/test_methodology_segments.py`    | Tests |

## Symbols / fields

| Symbol                                   | Kind      | Type / signature                                                              | Default | Notes |
|------------------------------------------|-----------|-------------------------------------------------------------------------------|---------|-------|
| `MethodologySegment`                     | dataclass | frozen: `note: MethodologyNote`, `metric_id: str`, `observation_count: int`, `first_period: date \| None`, `last_period: date \| None` | - | one row per (note, metric) |
| `Database.methodology_segments`          | method    | `(rating_id: str) -> list[MethodologySegment]`                                | -       | counts observations with `period_start` within bounds and metric in `affects_metrics` (or all) |
| `Database.methodology_version_for`       | method    | `(rating_id: str, metric_id: str, on_date: date) -> MethodologyNote \| None`  | -       | |
| `Database.methodology_overlaps`          | method    | `() -> list[sqlite3.Row]`                                                     | -       | pairs of notes of one rating whose ranges and metric scopes intersect |
| `Database.observations_without_methodology` | method | `(rating_id: str \| None = None) -> list[sqlite3.Row]`                        | -       | grouped by rating/metric with count + min/max period |
| `ValidationService.methodology_coverage` | method    | `(rating_id: str) -> list[MethodologySegment]`                                | -       | thin wrapper |

## Behaviour & validators

1. Bounds are inclusive; `''` means unbounded on that side.
2. `validate()` adds `methodology_overlap` (Severity.ERROR) per overlapping pair.
3. `validate()` adds `methodology_uncovered` (Severity.WARNING) per rating/metric with
   observations outside every segment — only when that rating declares at least one note.
4. Values are never modified; the methods are read-only `SELECT`s.

## Tests

| Test function                                         | File                                      | Type        | Asserts |
|-------------------------------------------------------|-------------------------------------------|-------------|---------|
| `test_segments_count_observations_per_version`        | `tests/unit/test_methodology_segments.py` | Integration | two notes split demo observations; counts sum to total |
| `test_affects_metrics_limits_segment`                 | `tests/unit/test_methodology_segments.py` | Integration | metric-scoped note counts only that metric |
| `test_methodology_version_for_open_ended_bound`       | `tests/unit/test_methodology_segments.py` | Integration | date after last `valid_from` returns open note |
| `test_overlap_reported_as_error`                      | `tests/unit/test_methodology_segments.py` | Integration | issue code `methodology_overlap`, ERROR |
| `test_uncovered_observations_reported_as_warning`     | `tests/unit/test_methodology_segments.py` | Integration | issue code `methodology_uncovered`, WARNING |

## Success criteria

- [ ] `ValidationService.methodology_coverage("demo")` returns per-version counts (plan.md criterion).
- [ ] All five tests pass.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- SQL lives only in `Database`. Services contain no SQL.
- Existing `ValidationService.validate()` ERROR semantics for current checks are unchanged
  (`langrank validate --strict` behaviour stays compatible).

## Out of scope

- CLI rendering ([subtask 06](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/06-cli-and-plot-hook.md)).
- Fixing the `invalid_ranks` `metric_id = 'rank'` mismatch — owned by
  [Milestone 0006 Task 01.0](/docs/roadmap/0006-provider-extensibility/plan.md#task-010---provider-capabilities-metadata).

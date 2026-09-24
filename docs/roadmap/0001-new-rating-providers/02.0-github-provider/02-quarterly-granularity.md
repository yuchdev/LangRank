# Subtask 02.0/02 - Quarterly granularity

**Task:** [02.0 - GitHub Provider](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/README.md) ·
**Role:** Python Expert · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Add `Granularity.QUARTER` and a shared quarter-period helper so quarterly sources can be
stored with correct `period_start/period_end/period_label`.

## Baseline

- `models.py:Granularity` = `YEAR`, `MONTH`.
- `observations.granularity TEXT NOT NULL` and natural key includes it → **no migration**;
  `SCHEMA_VERSION` stays unchanged. `ratings.native_granularity` is also TEXT.
- `Database.resolve_year_bounds` and `QueryService` work on `period_start` strings and
  need no change.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `src/langrank/models.py` | `Granularity.QUARTER = "quarter"` |
| Modify | `src/langrank/providers/common.py` | `quarter_period()` helper |
| Create | `tests/unit/test_periods.py` | Helper tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Notes |
|--------|------|------------------|-------|
| `Granularity.QUARTER` | enum member | `"quarter"` | |
| `quarter_period` | function | `(year: int, quarter: int) -> tuple[date, date, str]` | Returns `(start, end, "YYYY-Qn")`; `ValueError` if quarter ∉ 1..4 |

## Behaviour & validators

1. Q1 → Jan 1..Mar 31, Q2 → Apr 1..Jun 30, Q3 → Jul 1..Sep 30, Q4 → Oct 1..Dec 31.
2. Existing YEAR/MONTH rows unaffected (regression via existing tests).

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_quarter_period_bounds` | `tests/unit/test_periods.py` | Unit | All four quarters incl. label |
| `test_quarter_period_rejects_invalid_quarter` | `tests/unit/test_periods.py` | Unit | `ValueError` for 0 and 5 |
| `test_quarter_observation_round_trips_db` | `tests/unit/test_periods.py` | Integration | Upsert + `query_rows` preserves `"quarter"` |

## Success criteria

- [ ] No new migration added; `Database().schema_version()` unchanged.
- [ ] Tests pass; lint/format/mypy/pytest green.

## Constraints

- Append-only migrations rule respected (nothing to append here - state it in the PR).

## Out of scope

- Snapshot selection across mixed granularities (Milestone 0002 Task 03.0).

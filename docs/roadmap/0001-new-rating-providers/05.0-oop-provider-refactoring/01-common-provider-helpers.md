# Subtask 05.0/01 - Common provider helper methods & functions

**Task:** [05.0 - OOP Provider Refactoring](/docs/roadmap/0001-new-rating-providers/05.0-oop-provider-refactoring/README.md) ·
**Role:** Python Expert · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Extract duplicated algorithmic logic and validation helpers across providers into pure,
reusable functions in `src/langrank/providers/common.py`.

## Baseline

- `src/langrank/providers/common.py` provides `quarter_period`, `build_observation_hash`,
  `load_cached_payload`, `payload_from_content`, `build_observation`.
- `src/langrank/providers/github.py` and `src/langrank/providers/ieee_spectrum.py` duplicate
  window filtering logic (`_filter_window`).
- `src/langrank/providers/ieee_spectrum.py` (`_compute_ranks`) and `src/langrank/providers/github.py`
  (`_derive_ig_rank`) duplicate standard competition ranking (1, 2, 2, 4) calculation.
- Provider `validate()` methods repeat assertions for positive ranks, bounded percentages/ratings,
  and duplicate observation detection.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `src/langrank/providers/common.py` | Add `filter_records_by_window`, `compute_competition_ranks`, and validation helpers |
| Modify | `tests/unit/test_common_providers.py` or `tests/unit/test_common.py` | Add unit tests for the new helpers |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|--------|------|------------------|---------|-------|
| `filter_records_by_window` | function | `(records: Sequence[SourceRecord], *, since: date \| None = None, until: date \| None = None, years: int \| None = None, default_years: int = 10) -> list[SourceRecord]` | - | Window filter by `period_start` |
| `compute_competition_ranks` | function | `(items: Sequence[tuple[str, float]]) -> dict[str, int]` | - | Standard competition ranking (1, 2, 2, 4) with ties |
| `validate_positive_ranks` | function | `(observations: Sequence[Observation], report: ValidationReport, *, metric_id: str \| None = None) -> None` | - | Validates `rank > 0` |
| `validate_bounded_values` | function | `(observations: Sequence[Observation], report: ValidationReport, *, metric_id: str, code: str, min_value: float = 0.0, max_value: float = 100.0) -> None` | - | Validates `min_value <= value <= max_value` |
| `validate_unique_observations` | function | `(observations: Sequence[Observation], report: ValidationReport, *, code: str = "duplicate_language_period") -> None` | - | Checks uniqueness of `(language_id, period_start, metric_id)` |

## Success criteria

- [ ] New helpers are fully typed and covered with unit tests.
- [ ] Helpers are pure functions that do not perform I/O.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` green.

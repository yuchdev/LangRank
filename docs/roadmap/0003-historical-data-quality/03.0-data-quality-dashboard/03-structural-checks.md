# Subtask 03.0/03 - Structural checks (gaps, duplicates, unmapped names)

**Task:** [03.0 - Data Quality Dashboard](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/README.md) ·
**Role:** Python Expert · **Depends on:** 02 · **Status:** ⬜ Not started

## Goal

Implement `missing_periods`, `source_gaps`, `duplicate_ranks`, `unmapped_source_names`.

## Baseline

- `observations.granularity` is `month` or `year`; `period_start` ISO date.
- `language_aliases(rating_id, source_name_norm, valid_from, valid_to)`.

## Files

| Action | Path                                  | Purpose |
|--------|---------------------------------------|---------|
| Modify | `src/langrank/db/repository.py`       | four `quality_*` methods |
| Modify | `src/langrank/services/quality.py`    | four `CHECKS` entries |
| Create | `tests/unit/test_quality_structural.py` | tests |

## Symbols / fields

| Symbol                                   | Kind   | Type / signature                                           | Default | Notes |
|------------------------------------------|--------|------------------------------------------------------------|---------|-------|
| `Database.quality_series_periods`        | method | `(rating_id: str \| None) -> list[sqlite3.Row]` — distinct `(rating_id, metric_id, language_id, granularity, period_start)` | - | used by gap logic in Python |
| `Database.quality_duplicate_ranks`       | method | `(rating_id: str \| None, rank_metric_ids: set[str]) -> list[sqlite3.Row]` | - | |
| `Database.quality_unmapped_source_names` | method | `(rating_id: str \| None) -> list[sqlite3.Row]`            | -       | |
| `missing_periods`                        | check  | WARNING                                                    | -       | per series: expected periods between first and last observation (month or year step) minus present |
| `source_gaps`                            | check  | WARNING                                                    | -       | a period missing for **all** languages of a rating/metric between its first and last period |
| `duplicate_ranks`                        | check  | WARNING                                                    | -       | same rating/metric/period, same rank, >1 language (ties may be legitimate → WARNING) |
| `unmapped_source_names`                  | check  | WARNING                                                    | -       | `source_language_name` whose normalized key has no alias row (rating or global) valid on `period_start` and is not the canonical/display name |

## Behaviour & validators

1. Gaps are only computed *inside* a series' observed span — never before first observation (no pre-birth gaps; consistent with [Task 02.0](/docs/roadmap/0003-historical-data-quality/02.0-language-lifecycle-and-alias-validity/README.md)).
2. A `missing_periods` finding is suppressed when the same period is reported by `source_gaps` (report the coarser cause once).
3. Each finding's `detail` includes the missing/duplicated periods or ranks.
4. Normalized-key logic uses `normalization.resolution.normalize_alias_key` (Task 02.0/03); until that lands, `Database._normalize_alias`.

## Tests

| Test function                                    | File                                     | Type        | Asserts |
|--------------------------------------------------|------------------------------------------|-------------|---------|
| `test_missing_periods_flags_seeded_gap`          | `tests/unit/test_quality_structural.py`  | Integration | finding at seeded `AnomalyLocation` |
| `test_missing_periods_ignores_pre_first_observation` | `tests/unit/test_quality_structural.py` | Integration | late-born language → no finding |
| `test_source_gaps_suppresses_missing_periods`    | `tests/unit/test_quality_structural.py`  | Integration | one finding per gap |
| `test_duplicate_ranks_flags_tie`                 | `tests/unit/test_quality_structural.py`  | Integration | |
| `test_unmapped_source_names_flags_orphan_label`  | `tests/unit/test_quality_structural.py`  | Integration | |
| `test_structural_checks_silent_on_clean_baseline`| `tests/unit/test_quality_structural.py`  | Integration | zero findings |

## Success criteria

- [ ] All six tests pass.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Read-only connection; no data modification.

## Out of scope

- Value plausibility ([subtask 04](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/04-value-checks.md)).

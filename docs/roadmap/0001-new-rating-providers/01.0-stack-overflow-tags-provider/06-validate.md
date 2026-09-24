# Subtask 01.0/06 - Validate: named validation codes

**Task:** [01.0 - Stack Overflow Tags Provider](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 05 · **Status:** ⬜ Not started

## Goal

Implement `validate()` with named, test-covered `ValidationReport` codes specific to tag
activity.

## Baseline

`models.py:ValidationReport.add(severity, code, message)`; `FetchService` blocks the upsert
only on `Severity.ERROR`.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `src/langrank/providers/stackoverflow_tags.py` | `validate()` |
| Create | `tests/unit/test_stackoverflow_tags_validate.py` | One test per code |

## Symbols / fields

| Code | Severity | Condition |
|------|----------|-----------|
| `count_non_negative` | ERROR | `stackoverflow-tags-questions` value < 0 |
| `share_range` | ERROR | share value outside 0..100 |
| `rank_positive` | ERROR | rank ≤ 0 |
| `duplicate_language_period` | ERROR | same `(language_id, period_start, metric_id)` twice |
| `mixed_denominator` | ERROR | share observations in one batch carry >1 `denominator` |
| `share_not_derived` | ERROR | share/rank observation with `is_derived=False` |
| `unmapped_language` | WARNING | one per name in `last_unmapped` |
| `incomplete_month` | ERROR | a `period_start` in the current calendar month |

## Behaviour & validators

1. A report with only WARNINGs is `ok` and persists.
2. Messages include language, period label and metric.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_validate_flags_each_error_code` | `tests/unit/test_stackoverflow_tags_validate.py` | Unit | Parametrized over the 7 ERROR codes |
| `test_validate_unmapped_is_warning_only` | `tests/unit/test_stackoverflow_tags_validate.py` | Unit | `report.ok` stays True |
| `test_validate_clean_fixture_ok` | `tests/unit/test_stackoverflow_tags_validate.py` | Unit | No issues on valid data |

## Success criteria

- [ ] Every code in the table is emitted by `validate()` and covered by a test.
- [ ] Lint/format/mypy/pytest green.

## Constraints

- `validate()` never mutates or drops observations.

## Out of scope

- DB-wide checks in `ValidationService` (Milestone 0003 Task 03.0).

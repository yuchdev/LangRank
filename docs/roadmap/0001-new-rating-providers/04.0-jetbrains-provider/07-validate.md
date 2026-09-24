# Subtask 04.0/07 - Validate: named validation codes

**Task:** [04.0 - JetBrains Developer Ecosystem Provider](/docs/roadmap/0001-new-rating-providers/04.0-jetbrains-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 05, 06 · **Status:** ⬜ Not started

## Goal

Implement `validate()` for both families.

## Baseline

`ValidationReport`.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `src/langrank/providers/jetbrains.py` | `validate()` |
| Create | `tests/unit/test_jetbrains_validate.py` | Tests |

## Symbols / fields

| Code | Severity | Condition |
|------|----------|-----------|
| `percent_range` | ERROR | value ∉ 0..100 |
| `duplicate_language_period` | ERROR | duplicate `(language, year, metric)` |
| `missing_question_wording` | ERROR | observation without `question_wording` metadata |
| `raw_not_derived` | ERROR | `-raw` metric with `is_derived=False` |
| `published_marked_derived` | ERROR | published metric with `is_derived=True` |
| `missing_sample_size` | WARNING | `sample_size is None` |
| `unmapped_language` | WARNING | per `last_unmapped` |

## Behaviour & validators

1. Shares may sum > 100 % (multi-select) - not an error.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_jetbrains_validate_flags_each_code` | `tests/unit/test_jetbrains_validate.py` | Unit | Parametrized |
| `test_jetbrains_validate_bundled_dataset_ok` | `tests/unit/test_jetbrains_validate.py` | Unit | No ERROR on bundled CSV |

## Success criteria

- [ ] Every code emitted and tested.

## Constraints

- Never mutates observations.

## Out of scope

- -

# Subtask 03.0/06 - Validate: named validation codes

**Task:** [03.0 - IEEE Spectrum Provider](/docs/roadmap/0001-new-rating-providers/03.0-ieee-spectrum-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 05 · **Status:** ⬜ Not started

## Goal

Implement `validate()` for IEEE observations.

## Baseline

`ValidationReport`.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `src/langrank/providers/ieee_spectrum.py` | `validate()` |
| Create | `tests/unit/test_ieee_spectrum_validate.py` | Tests |

## Symbols / fields

| Code | Severity | Condition |
|------|----------|-----------|
| `rank_positive` | ERROR | rank ≤ 0 |
| `score_range` | ERROR | score ∉ 0..100 |
| `duplicate_language_period` | ERROR | duplicate `(language, year, metric)` |
| `duplicate_rank` | ERROR | two languages share a rank within one (year, profile) and scores differ |
| `top_score_not_100` | WARNING | max score in a (year, profile) ≠ 100 |
| `profile_not_in_edition` | ERROR | profile absent from the source-note edition table for that year |
| `unmapped_language` | WARNING | per `last_unmapped` |

## Behaviour & validators

1. Profile/edition membership read from a module constant `EDITION_PROFILES: dict[int, frozenset[IeeeProfile]]` mirroring the source note.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_ieee_validate_flags_each_code` | `tests/unit/test_ieee_spectrum_validate.py` | Unit | Parametrized |
| `test_ieee_validate_bundled_dataset_ok` | `tests/unit/test_ieee_spectrum_validate.py` | Unit | Real bundled CSV passes with no ERROR |

## Success criteria

- [ ] Every code emitted and tested.

## Constraints

- Never mutates observations.

## Out of scope

- Cross-provider checks.

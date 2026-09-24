# Subtask 04.0/08 - Fixtures, golden outputs & contract tests

**Task:** [04.0 - JetBrains Developer Ecosystem Provider](/docs/roadmap/0001-new-rating-providers/04.0-jetbrains-provider/README.md) ·
**Role:** Testing Expert · **Depends on:** 07, 01.0/07 · **Status:** ⬜ Not started

## Goal

Fixture + golden contract tests for both modes, and the "metrics never merged" guarantee.

## Baseline

`tests/contract/_golden.py`.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Create | `tests/fixtures/jetbrains/published_sample.csv` | 3 years × 2 metrics |
| Create | `tests/fixtures/jetbrains/raw_sample.csv` | ~20 synthetic respondents in real column layout |
| Create | `tests/fixtures/jetbrains/expected_published.json` | Golden |
| Create | `tests/fixtures/jetbrains/expected_raw.json` | Golden |
| Create | `tests/contract/test_jetbrains_provider.py` | Contract tests |

## Symbols / fields

N/A.

## Behaviour & validators

1. Raw fixture is synthetic (no real respondent rows).

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_jetbrains_published_matches_golden` | `tests/contract/test_jetbrains_provider.py` | Unit | Golden |
| `test_jetbrains_raw_matches_golden` | `tests/contract/test_jetbrains_provider.py` | Unit | Golden |
| `test_jetbrains_primary_and_used_are_distinct_metrics` | `tests/contract/test_jetbrains_provider.py` | Integration | Querying one never returns the other |

## Success criteria

- [ ] `uv run pytest -m "not integration"` green.

## Constraints

- No network.

## Out of scope

- -

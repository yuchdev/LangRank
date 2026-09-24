# Subtask 03.0/07 - Fixtures, golden outputs & contract tests

**Task:** [03.0 - IEEE Spectrum Provider](/docs/roadmap/0001-new-rating-providers/03.0-ieee-spectrum-provider/README.md) ·
**Role:** Testing Expert · **Depends on:** 06, 01.0/07 · **Status:** ⬜ Not started

## Goal

Fixture + golden contract tests, including the "profiles never mix" query guarantee.

## Baseline

`tests/contract/_golden.py`.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Create | `tests/fixtures/ieee-spectrum/sample.csv` | Two editions × three profiles × 5 languages |
| Create | `tests/fixtures/ieee-spectrum/expected_observations.json` | Golden |
| Create | `tests/contract/test_ieee_spectrum_provider.py` | Contract tests |

## Symbols / fields

N/A.

## Behaviour & validators

1. Fixture includes a missing score and an untracked label.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_ieee_spectrum_matches_golden` | `tests/contract/test_ieee_spectrum_provider.py` | Unit | Golden equality |
| `test_ieee_query_one_profile_excludes_others` | `tests/contract/test_ieee_spectrum_provider.py` | Integration | `QueryService` with `metric_id="ieee-spectrum-jobs-rank"` returns only jobs rows |
| `test_ieee_import_command_round_trip` | `tests/integration/test_cli.py` | E2E | `langrank import --rating ieee-spectrum` on fixture |

## Success criteria

- [ ] `uv run pytest -m "not integration"` green.

## Constraints

- No network.

## Out of scope

- Live tests (no live source).

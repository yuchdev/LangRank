# Subtask 02.0/09 - Fixtures, golden outputs & contract tests

**Task:** [02.0 - GitHub Provider](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/README.md) ·
**Role:** Testing Expert · **Depends on:** 08, 01.0/07 · **Status:** ⬜ Not started

## Goal

Fixture-driven contract tests for both variants using the shared golden helper.

## Baseline

`tests/contract/_golden.py:assert_matches_golden` (from 01.0/07).

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Create | `tests/fixtures/github/innovation_graph_languages.csv` | 2 quarters × 3 economies × 6 Linguist names incl. `Jupyter Notebook` |
| Create | `tests/fixtures/github/octoverse.csv` | Two editions with different bases |
| Create | `tests/fixtures/github/expected_innovation_graph.json` | Golden |
| Create | `tests/fixtures/github/expected_octoverse.json` | Golden |
| Create | `tests/contract/test_github_provider.py` | Contract tests |

## Symbols / fields

N/A (tests only).

## Behaviour & validators

1. Fixtures are real rows sampled from the CC0 CSV (commit SHA noted in a header comment
   file `tests/fixtures/github/SOURCE.md`).

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_github_innovation_graph_matches_golden` | `tests/contract/test_github_provider.py` | Unit | Golden equality |
| `test_github_octoverse_matches_golden` | `tests/contract/test_github_provider.py` | Unit | Golden equality |
| `test_github_variants_write_disjoint_metrics` | `tests/contract/test_github_provider.py` | Unit | Metric ID sets disjoint |
| `test_github_fetch_both_variants_and_query` | `tests/integration/test_fetch_and_query.py` | Integration | Both via `FetchService`, quarter rows queryable |

## Success criteria

- [ ] `uv run pytest -m "not integration"` green.

## Constraints

- No network outside `integration` tests.

## Out of scope

- Live tests (subtask 05).

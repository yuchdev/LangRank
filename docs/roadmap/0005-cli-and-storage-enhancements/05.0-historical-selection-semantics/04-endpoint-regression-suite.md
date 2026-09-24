# Subtask 05.0/04 - Regression suite pinning endpoint behaviour

**Task:** [05.0 - Historical Selection Semantics](/docs/roadmap/0005-cli-and-storage-enhancements/05.0-historical-selection-semantics/README.md) ·
**Role:** Testing Expert · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

End-to-end regression tests proving `query`, `export`, and `plot` return the same rows for the
same `--years` arguments, including the plan's named case: a source whose current calendar year
has no data yet.

## Baseline

- Subtasks 01-03 provide the resolver, service integration, and flags.

## Files

| Action | Path                                           | Purpose |
|--------|------------------------------------------------|---------|
| Create | `tests/integration/test_selection_semantics.py` | Tests below |
| Create | `tests/fixtures/selection/stale_annual.csv`     | Annual rating whose last edition is 2 years before a monthly one |

## Symbols / fields

| Symbol                 | Kind    | Type | Notes |
|------------------------|---------|------|-------|
| `seeded_db`            | fixture | `Database` | Seeds a monthly rating ending 2026-08 and an annual rating ending 2024 via `upsert_observations` (no network) |

## Behaviour & validators

1. "Stale current year": annual rating last published 2024, monthly rating current to 2026-08. With
   `--years 5`, the annual rating returns 2020-2024 (5 editions) both alone and inside a multi-rating
   `export --ratings` (default `per-source`) - never 2022-2024, which is what a single global endpoint
   of 2026 would give (today's behaviour whenever no single `--rating` scopes `resolve_year_bounds`).
2. Parity: for identical args, row keys from `query --format json`, `export json`, and the rows passed to
   `PlotService.build_figure` (spy) are equal.
3. Freezing "today" is unnecessary - the rule never reads the clock (asserted by a test that patches
   `date.today` to raise).

## Tests

| Test function                                  | File                                            | Type        | Asserts |
|------------------------------------------------|-------------------------------------------------|-------------|---------|
| `test_stale_current_year_not_truncated`        | `tests/integration/test_selection_semantics.py` | Integration | 5 editions returned |
| `test_query_export_plot_parity`                | `tests/integration/test_selection_semantics.py` | Integration | Same row keys across the three commands |
| `test_multi_rating_export_per_source_default`  | `tests/integration/test_selection_semantics.py` | Integration | Each rating uses its own endpoint |
| `test_until_overrides_endpoint`                | `tests/integration/test_selection_semantics.py` | Integration | `--until 2022 --years 3` → 2020-2022 |
| `test_rule_never_reads_clock`                  | `tests/integration/test_selection_semantics.py` | Integration | Patched `date.today` not called |

## Success criteria

- [ ] All five tests pass; suite runs with no network.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- `pytestmark = pytest.mark.integration`, matching existing integration tests.

## Out of scope

- Performance.

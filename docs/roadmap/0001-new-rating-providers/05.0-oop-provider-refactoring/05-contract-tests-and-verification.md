# Subtask 05.0/05 - Contract tests, golden outputs & regression verification

**Task:** [05.0 - OOP Provider Refactoring](/docs/roadmap/0001-new-rating-providers/05.0-oop-provider-refactoring/README.md) ·
**Role:** Testing Expert · **Depends on:** 03, 04 · **Status:** ⬜ Not started

## Goal

Verify that the refactoring introduced zero regressions across the contract test suite,
golden fixture comparisons, CLI workflows, and type checks.

## Baseline

- `tests/contract/`: Contains contract tests for all providers (`test_demo_provider.py`,
  `test_github_provider.py`, `test_ieee_spectrum_provider.py`, `test_jetbrains_provider.py`,
  `test_stackoverflow_tags_provider.py`, `test_bootstrap_providers.py`).
- Golden output files in `tests/fixtures/`.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `tests/contract/` | Ensure contract tests verify base provider contract and all provider instances |
| Verify | `tests/fixtures/` | Golden fixture outputs must remain byte-identical |

## Verification targets

1. Execute full contract test suite against all 9 provider implementations.
2. Verify golden observation outputs match without needing `LANGRANK_UPDATE_GOLDEN=1`.
3. Verify CLI commands (`langrank fetch all --offline`, `langrank validate --strict`, `langrank export`) work seamlessly.
4. Run static type checking and linting to ensure protocol compliance and no type errors.

## Success criteria

- [ ] All contract tests and golden fixture tests pass.
- [ ] No regression in CLI commands across all providers.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` green.

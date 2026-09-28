# Subtask 05.0/03 - Refactor bootstrap providers to BaseRatingProvider

**Task:** [05.0 - OOP Provider Refactoring](/docs/roadmap/0001-new-rating-providers/05.0-oop-provider-refactoring/README.md) ·
**Role:** Python Expert · **Depends on:** 02 · **Status:** ⬜ Not started

## Goal

Refactor the five bootstrap providers (`demo`, `pypl`, `redmonk`, `tiobe`,
`stackoverflow-survey`) to inherit from `BaseRatingProvider`, adopt common validation helpers,
and remove redundant boilerplate.

## Baseline

- `src/langrank/providers/demo.py:DemoProvider`
- `src/langrank/providers/pypl.py:PyplProvider`
- `src/langrank/providers/redmonk.py:RedMonkProvider`
- `src/langrank/providers/tiobe.py:TiobeProvider`
- `src/langrank/providers/stackoverflow_survey.py:StackOverflowSurveyProvider`
- All five define their own `__init__` and validate methods with repetitive checks.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `src/langrank/providers/demo.py` | Inherit from `BaseRatingProvider` |
| Modify | `src/langrank/providers/pypl.py` | Inherit from `BaseRatingProvider`, use common validation helpers |
| Modify | `src/langrank/providers/redmonk.py` | Inherit from `BaseRatingProvider`, use common validation helpers |
| Modify | `src/langrank/providers/tiobe.py` | Inherit from `BaseRatingProvider`, use common validation helpers |
| Modify | `src/langrank/providers/stackoverflow_survey.py` | Inherit from `BaseRatingProvider`, use common validation helpers |
| Modify | `tests/unit/test_providers.py` | Ensure all bootstrap provider unit tests pass |

## Behaviour & refactoring targets

1. Subclass `BaseRatingProvider` and call `super().__init__(cache_dir)`.
2. Replace duplicate validation loops with calls to `validate_positive_ranks`, `validate_bounded_values`, and `validate_unique_observations`.
3. Preserve all existing provider-specific behavior, errors, and metadata definitions.

## Success criteria

- [ ] All 5 bootstrap providers inherit from `BaseRatingProvider`.
- [ ] No regression in bootstrap provider unit and integration tests.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` green.

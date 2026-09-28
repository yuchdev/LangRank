# Subtask 05.0/04 - Refactor Milestone 0001 providers to BaseRatingProvider

**Task:** [05.0 - OOP Provider Refactoring](/docs/roadmap/0001-new-rating-providers/05.0-oop-provider-refactoring/README.md) ·
**Role:** Python Expert · **Depends on:** 02 · **Status:** ⬜ Not started

## Goal

Refactor the four Milestone 0001 providers (`github`, `ieee-spectrum`, `jetbrains`,
`stackoverflow-tags`) to inherit from `BaseRatingProvider`, eliminate duplicate `_filter_window`
implementations, unify competition rank derivation, and reuse shared validation routines.

## Baseline

- `src/langrank/providers/github.py:GitHubProvider`: Contains `_filter_window`, `_request_since/until/years`, `_derive_ig_rank` competition ranking.
- `src/langrank/providers/ieee_spectrum.py:IeeeSpectrumProvider`: Contains `_filter_window`, `_request_since/until/years`, `_compute_ranks` competition ranking.
- `src/langrank/providers/jetbrains.py:JetBrainsProvider`: Manages `last_unmapped` and survey-specific validation rules.
- `src/langrank/providers/stackoverflow_tags.py:StackOverflowTagsProvider`: Manages `last_unmapped` and tag-specific validation rules.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `src/langrank/providers/github.py` | Inherit from `BaseRatingProvider`, use base `_filter_window` and `compute_competition_ranks` |
| Modify | `src/langrank/providers/ieee_spectrum.py` | Inherit from `BaseRatingProvider`, use base `_filter_window` and `compute_competition_ranks` |
| Modify | `src/langrank/providers/jetbrains.py` | Inherit from `BaseRatingProvider`, use base state and validation helpers |
| Modify | `src/langrank/providers/stackoverflow_tags.py` | Inherit from `BaseRatingProvider`, use base state and validation helpers |

## Behaviour & refactoring targets

1. Remove duplicate `_filter_window` from `GitHubProvider` and `IeeeSpectrumProvider`, delegating to `BaseRatingProvider._filter_window`.
2. Replace local `_compute_ranks` / `_derive_ig_rank` tie-handling math with `compute_competition_ranks` from `common.py`.
3. Simplify `validate()` across all four providers using shared validation utilities while keeping provider-specific anomaly checks intact.
4. Ensure unmapped label recording uses standard `self.last_unmapped` lifecycle.

## Success criteria

- [ ] Complete removal of duplicate `_filter_window` methods.
- [ ] All four providers inherit from `BaseRatingProvider`.
- [ ] All provider unit and integration tests pass without regression.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` green.

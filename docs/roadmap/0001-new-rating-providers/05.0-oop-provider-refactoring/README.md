# Task 05.0 - OOP Provider Refactoring

**Milestone:** [0001 - New Rating Providers](/docs/roadmap/0001-new-rating-providers/plan.md) ·
**Spec source:** [plan.md § Task 05.0](/docs/roadmap/0001-new-rating-providers/plan.md#task-050---oop-provider-refactoring) ·
**Category:** refactoring / architecture · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask | Role | Depends on | Status |
|----|---------|------|------------|--------|
| 01 | [Common provider helper methods & functions](/docs/roadmap/0001-new-rating-providers/05.0-oop-provider-refactoring/01-common-provider-helpers.md) | Python Expert | - | ⬜ Not started |
| 02 | [Abstract Base Provider & shared state](/docs/roadmap/0001-new-rating-providers/05.0-oop-provider-refactoring/02-base-provider-class.md) | Python Expert | 01 | ⬜ Not started |
| 03 | [Refactor bootstrap providers to BaseRatingProvider](/docs/roadmap/0001-new-rating-providers/05.0-oop-provider-refactoring/03-refactor-bootstrap-providers.md) | Python Expert | 02 | ⬜ Not started |
| 04 | [Refactor Milestone 0001 providers to BaseRatingProvider](/docs/roadmap/0001-new-rating-providers/05.0-oop-provider-refactoring/04-refactor-new-providers.md) | Python Expert | 02 | ⬜ Not started |
| 05 | [Contract tests, golden outputs & regression verification](/docs/roadmap/0001-new-rating-providers/05.0-oop-provider-refactoring/05-contract-tests-and-verification.md) | Testing Expert | 03, 04 | ⬜ Not started |
| 06 | [Architecture & developer documentation updates](/docs/roadmap/0001-new-rating-providers/05.0-oop-provider-refactoring/06-docs.md) | Docs Writer | 05 | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

Refactor the entire set of 9 rating provider classes (`demo`, `tiobe`, `pypl`, `redmonk`,
`stackoverflow-survey`, `stackoverflow-tags`, `github`, `ieee-spectrum`, `jetbrains`) by
establishing an explicit base provider class (`BaseRatingProvider`), shared lifecycle state,
and shared helper functions. Eliminate duplicate logic such as `GitHubProvider._filter_window`
and `IeeeSpectrumProvider._filter_window`, duplicate competition ranking derivation, repeated
initialization boilerplate, and redundant validation checks while preserving the existing
`RatingProvider` protocol contract and byte-level golden compatibility.

## Baseline (what already exists)

- `src/langrank/providers/base.py`: Defines `RatingProvider(Protocol)` and
  `SupportsRawImport(Protocol)`.
- `src/langrank/providers/common.py`: Contains `quarter_period`, `build_observation_hash`,
  `load_cached_payload`, `payload_from_content`, `build_observation`.
- `src/langrank/providers/github.py` and `src/langrank/providers/ieee_spectrum.py`:
  Both implement duplicate `_filter_window` implementations and stashed date window fields.
- `src/langrank/providers/ieee_spectrum.py:192` and `src/langrank/providers/github.py:169`:
  Both implement standard competition ranking (1, 2, 2, 4) with tie handling.
- All 9 provider classes duplicate `__init__` state (`_cache_dir`, `_normalizer`,
  `_retrieved_at`, and unmapped tracker lists).
- Validation routines across providers repeat checks for positive ranks, 0..100 ranges,
  and duplicate `(language_id, period_start, metric_id)` observations.

## Design notes

- **Protocol + Base Class coexistence**: `RatingProvider` remains a `Protocol` in `base.py`
  for static type checking and structural subtyping. `BaseRatingProvider` is introduced as a
  reusable base class for concrete providers.
- **Shared helper functions (`common.py`)**:
  - `filter_records_by_window`: Filter `SourceRecord` sequences by `[since, until]` or `years`.
  - `compute_competition_ranks`: Standard competition ranking (1, 2, 2, 4).
  - Validation utilities for positive ranks, metric ranges, and observation uniqueness.
- **Base class responsibilities (`BaseRatingProvider`)**:
  - Shared constructor initializing `_cache_dir`, `_normalizer`, `_retrieved_at`, and `last_unmapped`.
  - Request window stashing (`_stash_request_window`) and filtering (`_filter_window`).
  - Helper methods for unmapped language recording during normalization.
- **Zero regressions**: All existing contract tests, golden fixtures, and CLI workflows
  must continue to pass unchanged.

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] `GitHubProvider._filter_window` and `IeeeSpectrumProvider._filter_window` are refactored
      to use shared base/helper implementation.
- [ ] All 9 provider classes inherit from `BaseRatingProvider`.
- [ ] Contract tests and golden outputs for all providers pass without modification.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` green.

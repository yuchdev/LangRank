# Subtask 05.0/06 - Architecture & developer documentation updates

**Task:** [05.0 - OOP Provider Refactoring](/docs/roadmap/0001-new-rating-providers/05.0-oop-provider-refactoring/README.md) ·
**Role:** Docs Writer · **Depends on:** 05 · **Status:** ⬜ Not started

## Goal

Document the OOP provider architecture, `BaseRatingProvider` extension patterns, and common
helpers in the developer documentation.

## Baseline

- `docs/dev/`: Developer documentation guides.
- `CLAUDE.md`: System overview and conventions.
- Provider docs in `docs/providers.md` and `docs/source-notes/`.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `docs/dev/` or `docs/providers.md` | Document `BaseRatingProvider` subclassing guide and helper usage |
| Modify | `CLAUDE.md` | Update provider architectural conventions if applicable |

## Content requirements

1. Document the distinction between the structural `RatingProvider(Protocol)` and the implementation `BaseRatingProvider`.
2. Guide for implementing new providers: subclassing `BaseRatingProvider`, using `_filter_window`, `compute_competition_ranks`, and validation helpers.
3. Update roadmap status and cross-references.

## Success criteria

- [ ] Documentation clearly explains provider inheritance and helper reuse.
- [ ] Internal links and formatting are valid.
- [ ] `uv run ruff check .`, `uv run ruff format --check .` green.

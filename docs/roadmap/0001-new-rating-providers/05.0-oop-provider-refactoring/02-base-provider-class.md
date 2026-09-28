# Subtask 05.0/02 - Abstract Base Provider & shared state

**Task:** [05.0 - OOP Provider Refactoring](/docs/roadmap/0001-new-rating-providers/05.0-oop-provider-refactoring/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Introduce `BaseRatingProvider` in `src/langrank/providers/base.py` to encapsulate common state
initialization, request window management, and helper methods, while preserving `RatingProvider`
as a structural typing `Protocol`.

## Baseline

- `src/langrank/providers/base.py` defines `RatingProvider(Protocol)` and `SupportsRawImport(Protocol)`.
- Every provider duplicates `self._cache_dir = cache_dir / self.provider_id`,
  `self._normalizer = LanguageNormalizer()`, `self._retrieved_at = datetime.now(UTC)`, and
  unmapped label lists.
- `GitHubProvider` and `IeeeSpectrumProvider` both define `_request_since`, `_request_until`,
  `_request_years` attributes and stashing logic.
- Implement `upstream_latest_period()` as part of contract logic, and find the way to get rid of the hardcode

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `src/langrank/providers/base.py` | Define `BaseRatingProvider` with common state & methods |
| Modify | `tests/unit/test_base_provider.py` | Unit tests for `BaseRatingProvider` behaviors |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|--------|------|------------------|---------|-------|
| `BaseRatingProvider` | class | `ABC` | - | Abstract base class for rating providers |
| `BaseRatingProvider.provider_id` | class attr | `str` | - | Subclasses must define |
| `BaseRatingProvider.__init__` | method | `(cache_dir: Path) -> None` | - | Initializes `_cache_dir`, `_normalizer`, `_retrieved_at`, `last_unmapped` |
| `BaseRatingProvider._stash_request_window` | method | `(request: FetchRequest) -> None` | - | Stashes `request.since`, `request.until`, `request.years` |
| `BaseRatingProvider._filter_window` | method | `(records: list[SourceRecord], *, default_years: int = 10) -> list[SourceRecord]` | - | Delegates to `common.filter_records_by_window` using stashed state |
| `BaseRatingProvider._record_unmapped` | method | `(label: str) -> None` | - | Records unmapped label into `last_unmapped` if not already present |

## Success criteria

- [ ] `BaseRatingProvider` is defined with type annotations and docstrings.
- [ ] `BaseRatingProvider` satisfies `RatingProvider` structural protocol where abstract methods are implemented.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` green.

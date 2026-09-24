# Subtask 01.0/02 - Language catalog expansion & rating-scoped aliases

**Task:** [01.0 - Stack Overflow Tags Provider](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/README.md) ·
**Role:** Python Expert · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Make `LanguageNormalizer` able to (a) resolve source names **per rating** (e.g. SO tag
`c#` vs PYPL `C/C++`), (b) cover the languages the four new providers publish, and
(c) resolve without raising, so one long-tail language never aborts a whole fetch. Shared by
Tasks 02.0-04.0.

## Baseline

- `src/langrank/normalization/languages.py:LanguageNormalizer` - 12 hard-coded languages,
  global aliases only, `resolve()` raises `UnknownLanguageError`.
- `Database.seed_languages` already writes `LanguageAlias.rating_id`, `valid_from`, `valid_to`
  into `language_aliases` (UNIQUE `(rating_id, source_name_norm)`); `Database.alias_to_language`
  already accepts `rating_id`.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `src/langrank/normalization/languages.py` | New languages, `RatingAlias`, `resolve(..., rating_id=)`, `try_resolve` |
| Modify | `tests/unit/test_normalization.py` | New tests |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|--------|------|------------------|---------|-------|
| `RatingAlias` | frozen dataclass | `rating_id: str, source_name: str, canonical_name: str, valid_from: date \| None, valid_to: date \| None, notes: str \| None` | dates `None` | Source-specific alias |
| `LanguageNormalizer._rating_aliases` | attr | `tuple[RatingAlias, ...]` | - | Declared in module constant `RATING_ALIASES` |
| `LanguageNormalizer.resolve` | method | `(value: str, *, rating_id: str \| None = None) -> str` | - | Rating-scoped lookup first, then global; still raises |
| `LanguageNormalizer.try_resolve` | method | `(value: str, *, rating_id: str \| None = None) -> str \| None` | - | Same lookup, returns `None` instead of raising |
| `LanguageNormalizer.aliases` | method | `() -> list[LanguageAlias]` | - | Now also emits rating-scoped aliases with their `rating_id`/validity |
| `CanonicalLanguage` entries | data | - | - | Add at least: `typescript`, `kotlin`, `swift`, `php`, `ruby`, `r`, `scala`, `dart`, `lua`, `perl`, `haskell`, `elixir`, `julia`, `matlab`, `sql`, `assembly`, `groovy`, `powershell`, `zig`, `fortran`, `cobol`, `ada`, `visual-basic`, `delphi` |

## Behaviour & validators

1. Lookup order: rating-scoped alias for `rating_id` → global alias → canonical/display name.
2. Existing global aliases and behaviour for the five bootstrap providers are unchanged
   (regression-tested).
3. Adding `r` must not make `resolve("R")` ambiguous with anything else; `sql` is a canonical
   entry but providers decide whether they track it.
4. Rating-scoped aliases with `valid_to` in the past remain resolvable (history is never
   rewritten) - the date range is metadata for
   [Milestone 0003 Task 02.0](/docs/roadmap/0003-historical-data-quality/plan.md#task-020---language-births-renames--alias-validity-ranges).
5. `Database.seed_languages` needs no change - verify with a test that a rating-scoped alias
   lands in `language_aliases` with the right `rating_id`.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_resolve_rating_scoped_alias_wins_over_global` | `tests/unit/test_normalization.py` | Unit | `resolve("c#", rating_id="stackoverflow-tags") == "c#"` and scoped alias precedence |
| `test_try_resolve_returns_none_for_unknown` | `tests/unit/test_normalization.py` | Unit | `try_resolve("brainfuck") is None`, no exception |
| `test_bootstrap_aliases_unchanged` | `tests/unit/test_normalization.py` | Unit | Every pre-existing alias resolves to the same canonical name |
| `test_seed_languages_persists_rating_scoped_alias` | `tests/unit/test_normalization.py` | Integration | Row in `language_aliases` with non-empty `rating_id` |

## Success criteria

- [ ] `try_resolve` and `resolve(..., rating_id=)` exist and are typed.
- [ ] Catalog covers every language in the tag table of subtask 03.
- [ ] All four tests pass; existing tests unchanged.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Normalization stays a pure, in-memory mapping; no DB access from `LanguageNormalizer`.
- Never map two distinct languages to one canonical ID (e.g. keep `c`, `c++` and PYPL's
  combined `c-cpp` separate).

## Out of scope

- Enforcing `valid_from`/`valid_to` at query time (Milestone 0003 Task 02.0).
- CLI alias commands (Milestone 0005 Task 04.0).

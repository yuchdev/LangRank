# Subtask 04.0/02 - `LanguageService.resolve` with normalizer cross-check

**Task:** [04.0 - Alias Management Commands](/docs/roadmap/0005-cli-and-storage-enhancements/04.0-alias-management-commands/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

A service method that explains a resolution: DB match (via `match_alias`), what the provider-side
`LanguageNormalizer` would return for the same input, whether they agree, and suggestions when
unresolved.

## Baseline

- `LanguageNormalizer.resolve` raises `UnknownLanguageError(value, suggestions)` on miss.
- `Database.language_suggestions(name)`; PYPL `c-cpp` hint lives inline in `cli.py:_language_ids`.

## Files

| Action | Path                                  | Purpose |
|--------|---------------------------------------|---------|
| Create | `src/langrank/services/languages.py`  | `LanguageResolution`, `LanguageService` |
| Modify | `src/langrank/cli.py`                 | Move PYPL hint into `LanguageService.combined_category_hint` and call it from `_language_ids` |
| Modify | `tests/unit/test_alias_resolution.py` | Tests below |

## Symbols / fields

| Symbol                                   | Kind     | Type / signature | Default | Notes |
|------------------------------------------|----------|------------------|---------|-------|
| `LanguageResolution`                     | frozen dataclass | `input`, `rating_id: str \| None`, `normalized: str`, `match: AliasMatch \| None`, `normalizer_language_id: str \| None`, `agrees: bool`, `suggestions: tuple[str, ...]`, `hint: str \| None` | - | |
| `LanguageService.__init__`               | method   | `(database: Database, normalizer: LanguageNormalizer) -> None` | - | |
| `LanguageService.resolve`                | method   | `(name: str, rating_id: str \| None = None) -> LanguageResolution` | - | Never raises for unknown input |
| `LanguageService.combined_category_hint` | method   | `(name: str, rating_id: str \| None) -> str \| None` | - | Returns the existing PYPL `c-cpp` message |

## Behaviour & validators

1. `agrees` is `True` iff DB `language_id` == normalizer result (both `None` counts as agreement).
2. Normalizer `UnknownLanguageError` is caught and recorded as `normalizer_language_id=None`.
3. Suggestions populated only when `match is None`.
4. `_language_ids` behaviour/messages are unchanged after moving the hint.

## Tests

| Test function                                  | File                                  | Type | Asserts |
|------------------------------------------------|---------------------------------------|------|---------|
| `test_resolve_known_alias_agrees`              | `tests/unit/test_alias_resolution.py` | Unit | `golang` → `go`, `agrees` |
| `test_resolve_detects_normalizer_db_disagreement` | `tests/unit/test_alias_resolution.py` | Unit | Insert a DB-only alias → `agrees is False` |
| `test_resolve_unknown_has_suggestions`         | `tests/unit/test_alias_resolution.py` | Unit | `pyton` → suggestions include `python` |
| `test_resolve_pypl_cpp_hint`                   | `tests/unit/test_alias_resolution.py` | Unit | `c++` + `pypl` → hint mentions `c-cpp` |

## Success criteria

- [ ] `LanguageService` has no SQL and no Typer imports.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Read-only; no writes to `language_aliases`.

## Out of scope

- CLI rendering (subtask 03).

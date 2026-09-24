# Subtask 04.0/01 - Single-path alias match in `Database`

**Task:** [04.0 - Alias Management Commands](/docs/roadmap/0005-cli-and-storage-enhancements/04.0-alias-management-commands/README.md) ·
**Role:** Python Expert · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Add `Database.match_alias()` returning the full matched alias row (scope, validity, notes) and
refactor `alias_to_language()` to delegate to it, so resolution and inspection share one SQL path.

## Baseline

- `Database.alias_to_language(source_name, rating_id=None) -> str | None` runs its own SQL and
  returns only `language_id`.

## Files

| Action | Path                                 | Purpose |
|--------|--------------------------------------|---------|
| Modify | `src/langrank/db/repository.py`      | `AliasMatch`, `match_alias`; `alias_to_language` delegates |
| Create | `tests/unit/test_alias_resolution.py` | Tests below |

## Symbols / fields

| Symbol                         | Kind     | Type / signature | Default | Notes |
|--------------------------------|----------|------------------|---------|-------|
| `AliasMatch`                   | frozen dataclass | `input: str`, `normalized: str`, `alias: LanguageAlias`, `scope: Literal["rating", "global"]` | - | In `db/repository.py` |
| `Database.match_alias`         | method   | `(source_name: str, rating_id: str \| None = None) -> AliasMatch \| None` | - | Same SQL/ordering as today's `alias_to_language` |
| `Database.alias_to_language`   | method   | unchanged signature | - | `m = self.match_alias(...); return None if m is None else m.alias.language_id` |
| `Database.normalize_alias_key` | staticmethod | `(value: str) -> str` | - | Public alias of `_normalize_alias` (kept for compatibility) |

## Behaviour & validators

1. Rating-specific alias wins over global (existing precedence preserved).
2. `alias_to_language` return values are unchanged for every existing input.
3. `normalized` in the result equals `_normalize_alias(input)`.

## Tests

| Test function                                       | File                                  | Type | Asserts |
|-----------------------------------------------------|---------------------------------------|------|---------|
| `test_match_alias_global_scope`                     | `tests/unit/test_alias_resolution.py` | Unit | `cpp` → `c++`, scope `global` |
| `test_match_alias_rating_specific_precedence`       | `tests/unit/test_alias_resolution.py` | Unit | Seed a `pypl` alias shadowing a global one → scope `rating` |
| `test_alias_to_language_delegates_to_match_alias`   | `tests/unit/test_alias_resolution.py` | Unit | Results equal for all seeded aliases |
| `test_match_alias_unknown_returns_none`             | `tests/unit/test_alias_resolution.py` | Unit | `None` |

## Success criteria

- [ ] Only one SQL statement in `repository.py` resolves aliases.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- `Database` remains the only SQL site; behaviour-preserving refactor.

## Out of scope

- Date-aware resolution via `valid_from`/`valid_to` (Milestone 0003 Task 02.0).

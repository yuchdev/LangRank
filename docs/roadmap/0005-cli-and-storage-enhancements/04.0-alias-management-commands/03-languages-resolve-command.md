# Subtask 04.0/03 - `langrank languages resolve` command

**Task:** [04.0 - Alias Management Commands](/docs/roadmap/0005-cli-and-storage-enhancements/04.0-alias-management-commands/README.md) ·
**Role:** Python Expert · **Depends on:** 02 · **Status:** ⬜ Not started

## Goal

`langrank languages resolve cpp [--rating pypl] [--format table|json] [--strict]` prints how
the input resolves, via `LanguageService.resolve`.

## Baseline

- `languages_app` Typer group with `show` and `aliases`.

## Files

| Action | Path                                         | Purpose |
|--------|----------------------------------------------|---------|
| Modify | `src/langrank/cli.py`                        | `languages_resolve` command |
| Create | `tests/integration/test_languages_cli.py`    | Tests below |

## Symbols / fields

| Symbol               | Kind        | Type / signature | Default | Notes |
|----------------------|-------------|------------------|---------|-------|
| `languages_resolve`  | CLI command | `name: str`, `--rating`, `--format {table,json}`, `--strict` | `table`, `False` | |

## Behaviour & validators

1. Table output rows: input, normalized key, rating scope used, matched alias (source label),
   scope (`rating`/`global`), canonical language, validity range, notes, normalizer result,
   agreement.
2. JSON output is `dataclasses.asdict(LanguageResolution)` (dates ISO).
3. Exit codes: 0 resolved; 1 unresolved (prints suggestions and hint); with `--strict`, 3 when
   resolved but `agrees is False`.
4. Unknown `--rating` → existing `ProviderError` path (exit 1/2 as elsewhere).

## Tests

| Test function                              | File                                      | Type        | Asserts |
|--------------------------------------------|-------------------------------------------|-------------|---------|
| `test_languages_resolve_known_alias`       | `tests/integration/test_languages_cli.py` | Integration | `resolve cpp` exit 0, output contains `c++` |
| `test_languages_resolve_json`              | `tests/integration/test_languages_cli.py` | Integration | Valid JSON with `match.alias.language_id == "c++"` |
| `test_languages_resolve_unknown_exit_1`    | `tests/integration/test_languages_cli.py` | Integration | Exit 1, "Did you mean" |
| `test_languages_resolve_strict_disagreement` | `tests/integration/test_languages_cli.py` | Integration | DB-only alias + `--strict` → exit 3 |

## Success criteria

- [ ] `langrank languages resolve cpp` documented in `--help` and README.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- `pytestmark = pytest.mark.integration` (matches `tests/integration/test_cli.py`).

## Out of scope

- Batch resolution from a file.

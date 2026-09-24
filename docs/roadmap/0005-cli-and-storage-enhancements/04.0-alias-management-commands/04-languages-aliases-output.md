# Subtask 04.0/04 - Richer `languages aliases` output

**Task:** [04.0 - Alias Management Commands](/docs/roadmap/0005-cli-and-storage-enhancements/04.0-alias-management-commands/README.md) ·
**Role:** Python Expert · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Extend the existing `languages aliases` command to show scope, validity range, notes and origin,
with a JSON format - so the plan's "source-defined vs user aliases stay distinguishable" rule is
visible in CLI output from day one.

## Baseline

- `cli.py:languages_aliases(ctx, rating=None)` prints Rating/Alias/Canonical; `--rating` filter
  (includes global aliases) already works via `Database.list_aliases(rating_id)`.

## Files

| Action | Path                                      | Purpose |
|--------|-------------------------------------------|---------|
| Modify | `src/langrank/cli.py`                     | Columns + `--format` |
| Modify | `tests/integration/test_languages_cli.py` | Tests below |

## Symbols / fields

| Symbol                | Kind        | Type | Default | Notes |
|-----------------------|-------------|------|---------|-------|
| `languages_aliases`   | CLI command | adds `--format {table,json}`, `--language <name>` | `table`, `None` | `--language` filters to one canonical language |
| column `Origin`       | output      | str  | `source-defined` | Constant today; the ADR (subtask 06) defines `user` |
| columns `Valid from` / `Valid to` / `Notes` | output | str | `-` | From `LanguageAlias` |

## Behaviour & validators

1. Existing columns and `--rating` semantics unchanged (additive only).
2. Rows sorted by canonical language then alias.
3. JSON emits a list of `LanguageAlias` dicts plus `origin`.

## Tests

| Test function                                 | File                                      | Type        | Asserts |
|-----------------------------------------------|-------------------------------------------|-------------|---------|
| `test_languages_aliases_shows_origin_column`  | `tests/integration/test_languages_cli.py` | Integration | `source-defined` in output |
| `test_languages_aliases_filter_by_language`   | `tests/integration/test_languages_cli.py` | Integration | `--language c++` lists `cpp`, `cplusplus` only |
| `test_languages_aliases_json`                 | `tests/integration/test_languages_cli.py` | Integration | Valid JSON with `origin` key |

## Success criteria

- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Read-only.

## Out of scope

- An `origin` DB column (only if the ADR accepts user aliases).

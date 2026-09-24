# Subtask 02.0/04 - Providers adopt dated resolution

**Task:** [02.0 - Language Births, Renames & Alias Validity Ranges](/docs/roadmap/0003-historical-data-quality/02.0-language-lifecycle-and-alias-validity/README.md) ·
**Role:** Python Expert · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

Every provider resolves source labels with its own `rating_id` and the record's
`period_start`, and CLI lookups pass the rating where one is known.

## Baseline

- `demo`, `tiobe`, `pypl`, `redmonk`, `stackoverflow_survey` call
  `self._normalizer.resolve(record.language)`.
- `cli.py:_language_ids(state, names, rating_id)` and `coverage` call `alias_to_language`.

## Files

| Action | Path                                              | Purpose |
|--------|---------------------------------------------------|---------|
| Modify | `src/langrank/providers/demo.py`                  | dated resolve |
| Modify | `src/langrank/providers/tiobe.py`                 | dated resolve |
| Modify | `src/langrank/providers/pypl.py`                  | dated resolve |
| Modify | `src/langrank/providers/redmonk.py`               | dated resolve |
| Modify | `src/langrank/providers/stackoverflow_survey.py`  | dated resolve |
| Modify | `src/langrank/cli.py`                             | `languages aliases` shows `valid_from`/`valid_to` columns |
| Modify | `tests/contract/test_production_providers.py`     | Contract tests |

## Symbols / fields

| Symbol                         | Kind   | Type / signature                                                                       | Default | Notes |
|--------------------------------|--------|----------------------------------------------------------------------------------------|---------|-------|
| `<Provider>.normalize`         | method | calls `resolve(record.language, rating_id=self.provider_id, on_date=record.period_start)` | -    | all five providers |

## Behaviour & validators

1. `Observation.source_language_name` equals `SourceRecord.language` verbatim (original label preserved).
2. Parsed output (`parse()`) is unchanged; only `normalize()` changes — `parser_version` unchanged.
3. `languages aliases` table gains `Valid from` / `Valid to` columns (`-` when open).

## Tests

| Test function                                           | File                                          | Type | Asserts |
|---------------------------------------------------------|-----------------------------------------------|------|---------|
| `test_providers_preserve_source_language_name`          | `tests/contract/test_production_providers.py` | Unit | parametrized over providers, fixture-driven |
| `test_providers_pass_rating_and_date_to_resolver`       | `tests/contract/test_production_providers.py` | Mock | spy normalizer receives `rating_id` and `on_date` |
| `test_cli_languages_aliases_shows_validity`             | `tests/integration/test_cli.py`               | E2E  | header contains `Valid from` |

## Success criteria

- [ ] No provider calls `resolve()` without `rating_id` and `on_date`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Providers stay DB-free and network-free outside `fetch()`.

## Out of scope

- New alias commands (0005 Task 04.0).

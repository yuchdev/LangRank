# Subtask 02.0/03 - Date- and rating-aware alias resolution

**Task:** [02.0 - Language Births, Renames & Alias Validity Ranges](/docs/roadmap/0003-historical-data-quality/02.0-language-lifecycle-and-alias-validity/README.md) ·
**Role:** Python Expert · **Depends on:** 02 · **Status:** ⬜ Not started

## Goal

Implement one pure resolution function honouring rating precedence and validity dates, used
by both `LanguageNormalizer.resolve` and `Database.alias_to_language`.

## Baseline

- `LanguageNormalizer.resolve(value: str) -> str` — global lookup only.
- `Database.alias_to_language(source_name, rating_id=None) -> str | None` — SQL lookup, no dates.
- Key normalization duplicated in two places.

## Files

| Action | Path                                      | Purpose |
|--------|-------------------------------------------|---------|
| Create | `src/langrank/normalization/resolution.py`| `normalize_alias_key`, `select_alias` |
| Modify | `src/langrank/normalization/languages.py` | `resolve(value, *, rating_id=None, on_date=None)` |
| Modify | `src/langrank/db/repository.py`           | `alias_to_language(source_name, rating_id=None, on_date=None)`; `_normalize_alias` delegates to `normalize_alias_key` |
| Create | `tests/unit/test_alias_resolution.py`     | Rule + parity tests |

## Symbols / fields

| Symbol                           | Kind     | Type / signature                                                                                      | Default | Notes |
|----------------------------------|----------|-------------------------------------------------------------------------------------------------------|---------|-------|
| `normalize_alias_key`            | function | `(value: str) -> str`                                                                                 | -       | the one key function |
| `select_alias`                   | function | `(candidates: Sequence[LanguageAlias], *, rating_id: str \| None, on_date: date \| None) -> LanguageAlias \| None` | - | pure precedence rule |
| `LanguageNormalizer.resolve`     | method   | `(value: str, *, rating_id: str \| None = None, on_date: date \| None = None) -> str`                  | -       | backwards compatible |
| `Database.alias_to_language`     | method   | `(source_name: str, rating_id: str \| None = None, on_date: date \| None = None) -> str \| None`         | -       | loads candidate rows, calls `select_alias` |

## Behaviour & validators

1. Candidate is valid when `(valid_from is None or valid_from <= on_date) and (valid_to is None or on_date <= valid_to)`; `on_date=None` treats every candidate as valid.
2. Precedence: rating-specific valid → global valid; ties impossible (catalog validation, subtask 02).
3. If only out-of-range candidates exist, `resolve` raises `UnknownLanguageError` with a message
   containing the candidate's validity range; `alias_to_language` returns `None`.
4. Existing call sites without the new kwargs behave exactly as before.

## Tests

| Test function                                     | File                                  | Type        | Asserts |
|---------------------------------------------------|---------------------------------------|-------------|---------|
| `test_rating_specific_alias_beats_global`         | `tests/unit/test_alias_resolution.py` | Unit        | precedence |
| `test_alias_outside_validity_not_selected`        | `tests/unit/test_alias_resolution.py` | Unit        | dated rule |
| `test_renamed_label_resolves_both_periods`        | `tests/unit/test_alias_resolution.py` | Unit        | old label before rename, new label after |
| `test_out_of_range_error_mentions_validity`       | `tests/unit/test_alias_resolution.py` | Unit        | `UnknownLanguageError` message |
| `test_resolver_parity_normalizer_vs_database`     | `tests/unit/test_alias_resolution.py` | Integration | for every catalog alias × sample dates, both paths agree |
| `test_existing_resolution_unchanged`              | `tests/unit/test_normalization.py`    | Unit        | existing parametrized cases still pass |

## Success criteria

- [ ] Single key-normalization function; `Database._normalize_alias` and `LanguageNormalizer._normalize_key` delegate to it.
- [ ] Parity test passes across all catalog aliases.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- `resolution.py` imports nothing from `db/` (keeps providers DB-free).

## Out of scope

- Changing provider call sites ([subtask 04](/docs/roadmap/0003-historical-data-quality/02.0-language-lifecycle-and-alias-validity/04-provider-adoption.md)).

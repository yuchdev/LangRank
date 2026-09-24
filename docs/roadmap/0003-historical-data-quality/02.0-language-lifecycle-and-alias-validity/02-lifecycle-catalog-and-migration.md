# Subtask 02.0/02 - Lifecycle catalog & schema migration

**Task:** [02.0 - Language Births, Renames & Alias Validity Ranges](/docs/roadmap/0003-historical-data-quality/02.0-language-lifecycle-and-alias-validity/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Extend the language catalog with birth/retirement dates and rating-specific, dated source
aliases, and persist both through a new append-only migration and `seed_languages`.

## Baseline

- `CanonicalLanguage(canonical_name, display_name, aliases)` in `normalization/languages.py`.
- `Database.seed_languages` upserts languages and global aliases on every `Database()` init.
- `languages` table: `id`, `canonical_name`, `display_name`.

## Files

| Action | Path                                      | Purpose |
|--------|-------------------------------------------|---------|
| Modify | `src/langrank/normalization/languages.py` | `introduced`/`retired` on `CanonicalLanguage`; `SourceAlias`; `SOURCE_ALIASES` |
| Modify | `src/langrank/models.py`                  | `Language.introduced`, `Language.retired` |
| Modify | `src/langrank/db/migrations.py`           | Append `(N, "ALTER TABLE languages ADD COLUMN introduced TEXT; ... retired TEXT;")` |
| Modify | `src/langrank/db/repository.py`           | `seed_languages` writes new columns and rating-specific dated aliases |
| Modify | `tests/unit/test_migrations.py`           | Migration test |
| Modify | `tests/unit/test_normalization.py`        | Catalog tests |

`N` = next unused migration version at merge time (see
[Task 01.0/02](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/02-break-kind-migration.md)).

## Symbols / fields

| Symbol                           | Kind      | Type / signature                                                                                 | Default | Notes |
|----------------------------------|-----------|--------------------------------------------------------------------------------------------------|---------|-------|
| `CanonicalLanguage.introduced`   | field     | `date \| None`                                                                                    | `None`  | first public release; cite in comment |
| `CanonicalLanguage.retired`      | field     | `date \| None`                                                                                    | `None`  | |
| `SourceAlias`                    | dataclass | frozen: `rating_id: str`, `source_name: str`, `language_id: str`, `valid_from: date \| None = None`, `valid_to: date \| None = None`, `notes: str \| None = None` | - | |
| `SOURCE_ALIASES`                 | const     | `tuple[SourceAlias, ...]`                                                                        | `()` + existing PYPL `c/c++` style entries moved here when rating-specific | |
| `Language.introduced` / `.retired` | field   | `date \| None`                                                                                    | `None`  | |
| `languages.introduced` / `.retired` | column | `TEXT` (ISO date)                                                                               | `NULL`  | |
| `LanguageNormalizer.aliases()`   | method    | `() -> list[LanguageAlias]`                                                                      | -       | now includes `SOURCE_ALIASES` with dates |

## Behaviour & validators

1. `LanguageNormalizer.__init__` raises `ConfigurationError` if a `SourceAlias` references an
   unknown `language_id`, or two aliases for the same `(rating_id, normalized name)` have
   overlapping validity.
2. `introduced` is set only where a citation exists (e.g. rust 2015-05-15, go 2012-03-28 for
   1.0 releases — verify); otherwise `None`.
3. `seed_languages` remains idempotent.
4. Existing `(rating_id, source_name_norm)` unique key allows only one row per label per
   rating; a renamed label is represented by *two different labels* (old + new) each with
   its own validity. Re-mapping the **same** label to different languages over time is not
   supported in this subtask (documented limitation; revisit if a real case appears).

## Tests

| Test function                                         | File                                | Type        | Asserts |
|-------------------------------------------------------|-------------------------------------|-------------|---------|
| `test_migration_adds_language_lifecycle_columns`      | `tests/unit/test_migrations.py`     | Integration | columns exist |
| `test_seed_writes_introduced_and_rating_aliases`      | `tests/unit/test_normalization.py`  | Integration | DB rows carry dates and rating_id |
| `test_catalog_rejects_unknown_alias_target`           | `tests/unit/test_normalization.py`  | Unit        | `ConfigurationError` |
| `test_catalog_rejects_overlapping_alias_validity`     | `tests/unit/test_normalization.py`  | Unit        | `ConfigurationError` |

## Success criteria

- [ ] New migration appended; old ones untouched.
- [ ] All four tests pass.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Append-only migrations; `Database` sole SQL owner; no guessed dates.

## Out of scope

- Using the dates during resolution ([subtask 03](/docs/roadmap/0003-historical-data-quality/02.0-language-lifecycle-and-alias-validity/03-date-aware-resolution.md)).

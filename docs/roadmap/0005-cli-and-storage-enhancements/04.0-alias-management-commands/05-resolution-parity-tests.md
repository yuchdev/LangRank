# Subtask 04.0/05 - Resolution parity test suite

**Task:** [04.0 - Alias Management Commands](/docs/roadmap/0005-cli-and-storage-enhancements/04.0-alias-management-commands/README.md) ·
**Role:** Testing Expert · **Depends on:** 02 · **Status:** ⬜ Not started

## Goal

Pin that the three resolution entry points - `LanguageNormalizer.resolve`,
`Database.alias_to_language`, and `languages resolve` - agree for every known name, and that the
two key-normalisation functions stay identical.

## Baseline

- `LanguageNormalizer._normalize_key` and `Database._normalize_alias` are duplicated code.
- `tests/unit/test_normalization.py` has 2 tests.

## Files

| Action | Path                                   | Purpose |
|--------|----------------------------------------|---------|
| Create | `tests/unit/test_resolution_parity.py` | Tests below |

## Symbols / fields

| Symbol              | Kind        | Type | Notes |
|---------------------|-------------|------|-------|
| `ALL_KNOWN_NAMES`   | test fixture | `list[str]` | Every canonical name, display name and alias from `LanguageNormalizer().languages()` / `.aliases()`, plus case/whitespace/punctuation variants (`" CPP "`, `"C#"`, `"c sharp"`) |

## Behaviour & validators

1. Parametrized over `ALL_KNOWN_NAMES` so a new alias in `normalization/languages.py` is covered
   automatically.
2. Uses a Hypothesis-free fixed variant generator (no new dependency).

## Tests

| Test function                                      | File                                   | Type | Asserts |
|----------------------------------------------------|----------------------------------------|------|---------|
| `test_normalizer_and_db_resolve_identically`       | `tests/unit/test_resolution_parity.py` | Unit | `normalizer.resolve(n) == database.alias_to_language(n)` |
| `test_language_service_matches_alias_to_language`  | `tests/unit/test_resolution_parity.py` | Unit | `service.resolve(n).match.alias.language_id == alias_to_language(n)` and `agrees` |
| `test_normalization_keys_identical`                | `tests/unit/test_resolution_parity.py` | Unit | `LanguageNormalizer._normalize_key(x) == Database._normalize_alias(x)` over names + punctuation samples |
| `test_every_seeded_alias_roundtrips`               | `tests/unit/test_resolution_parity.py` | Unit | Each `list_aliases()` row resolves to its own `language_id` |

## Success criteria

- [ ] Suite fails if either normalisation function changes alone.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- No production code change (if a discrepancy is found, file it and fix in a follow-up subtask).

## Out of scope

- Merging the two normalisation functions (possible follow-up once parity is pinned).

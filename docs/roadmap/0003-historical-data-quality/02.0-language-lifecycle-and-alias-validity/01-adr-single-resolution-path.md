# Subtask 02.0/01 - ADR: one alias-resolution rule set

**Task:** [02.0 - Language Births, Renames & Alias Validity Ranges](/docs/roadmap/0003-historical-data-quality/02.0-language-lifecycle-and-alias-validity/README.md) ·
**Role:** Architect · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Decide and record how the provider-side (`LanguageNormalizer.resolve`) and DB-side
(`Database.alias_to_language`) resolution paths share one rule set, including date validity
and rating precedence.

## Baseline

- Duplicated key normalization: `LanguageNormalizer._normalize_key` and `Database._normalize_alias`.
- `alias_to_language` orders rating-specific before global but ignores dates.

## Files

| Action | Path                                               | Purpose |
|--------|----------------------------------------------------|---------|
| Create | `docs/adr/0003-single-alias-resolution-rules.md`   | ADR (number = next free at merge time) |
| Modify | `docs/adr/README.md`                               | Index entry |

## Symbols / fields

| Symbol                 | Kind     | Type / signature | Default | Notes |
|------------------------|----------|------------------|---------|-------|
| Considered options     | section  | ≥ 3              | -       | (a) pure rule function in `normalization/` shared by both paths, (b) providers receive a DB-backed resolver via constructor, (c) DB is authoritative and providers emit unresolved names |
| Decision               | section  | option (a)       | -       | recommended; keeps providers DB-free |

## Behaviour & validators

1. ADR fixes precedence: rating-specific valid → global valid → canonical/display name.
2. ADR fixes validity semantics: inclusive bounds, `None` = open, evaluated against
   `period_start`.
3. ADR states that the catalog in `normalization/languages.py` is the only writer of
   `language_aliases`/`languages` (via `Database.seed_languages`), and that the future
   user-alias feature (0005 Task 04.0) must use a separate, distinguishable origin.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| - (docs only) | -    | -    | link check passes for `docs/adr` |

## Success criteria

- [ ] ADR Accepted and indexed.
- [ ] Subtasks 02-03 reference it.

## Constraints

- MADR template; absolute links.

## Out of scope

- Implementation (subtasks 02-04).

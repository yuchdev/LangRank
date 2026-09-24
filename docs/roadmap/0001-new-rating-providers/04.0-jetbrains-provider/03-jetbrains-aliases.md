# Subtask 04.0/03 - JetBrains language aliases

**Task:** [04.0 - JetBrains Developer Ecosystem Provider](/docs/roadmap/0001-new-rating-providers/04.0-jetbrains-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 01.0/02 · **Status:** ⬜ Not started

## Goal

Add `jetbrains`-scoped aliases for survey answer labels.

## Baseline

`RATING_ALIASES` / `try_resolve` from
[01.0/02](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/02-rating-scoped-aliases.md).

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `src/langrank/normalization/languages.py` | Aliases |
| Modify | `tests/unit/test_normalization.py` | Tests |

## Symbols / fields

Examples: `Shell scripting languages` → `shell`, `C/C++`-style combined answers (pre-split
years) → `c-cpp` **only** where the survey itself combined them, `Visual Basic` →
`visual-basic`, `Delphi` → `delphi`, `I don't use programming languages` / `Other` →
listed in `JETBRAINS_NON_LANGUAGE_ANSWERS`.

## Behaviour & validators

1. A combined answer is never split into two languages.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_jetbrains_aliases_resolve` | `tests/unit/test_normalization.py` | Unit | Mapped labels resolve |
| `test_jetbrains_non_language_answers_unmapped` | `tests/unit/test_normalization.py` | Unit | `try_resolve` → `None` |

## Success criteria

- [ ] Tests pass; lint/format/mypy/pytest green.

## Constraints

- No global alias changes.

## Out of scope

- -

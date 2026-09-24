# Subtask 02.0/03 - Linguist language aliases

**Task:** [02.0 - GitHub Provider](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/README.md) ·
**Role:** Python Expert · **Depends on:** 01.0/02 · **Status:** ⬜ Not started

## Goal

Add `github`-scoped aliases for GitHub Linguist language names used by both variants.

## Baseline

`normalization/languages.py` after [01.0/02](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/02-rating-scoped-aliases.md):
`RATING_ALIASES`, `try_resolve(..., rating_id=)`.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `src/langrank/normalization/languages.py` | `RatingAlias(rating_id="github", ...)` entries |
| Modify | `tests/unit/test_normalization.py` | Alias tests |

## Symbols / fields

| Linguist name | Canonical |
|---------------|-----------|
| `C++` | `c++` |
| `C#` | `c#` |
| `Shell` | `shell` |
| `PowerShell` | `powershell` |
| `Visual Basic .NET` | `vb.net` |
| `Objective-C` | `objective-c` |
| `Jupyter Notebook` | *(unmapped - not a language)* |
| `HCL`, `Dockerfile`, `Makefile`, `HTML`, `CSS` | *(unmapped - documented)* |

## Behaviour & validators

1. Non-language Linguist entries are deliberately **not** mapped; list them in a module
   constant `GITHUB_NON_LANGUAGES: frozenset[str]` so the warning is suppressed for known
   exclusions but raised for genuinely new names.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| `test_github_linguist_aliases_resolve` | `tests/unit/test_normalization.py` | Unit | Every mapped name resolves with `rating_id="github"` |
| `test_github_non_languages_not_mapped` | `tests/unit/test_normalization.py` | Unit | `try_resolve("Jupyter Notebook", rating_id="github") is None` |

## Success criteria

- [ ] Tests pass; lint/format/mypy/pytest green.

## Constraints

- No change to global aliases.

## Out of scope

- Mapping the full 379-language Linguist list.

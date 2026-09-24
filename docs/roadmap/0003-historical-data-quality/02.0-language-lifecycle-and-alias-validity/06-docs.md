# Subtask 02.0/06 - Document lifecycle & alias validity

**Task:** [02.0 - Language Births, Renames & Alias Validity Ranges](/docs/roadmap/0003-historical-data-quality/02.0-language-lifecycle-and-alias-validity/README.md) ·
**Role:** Docs Writer · **Depends on:** 04, 05 · **Status:** ⬜ Not started

## Goal

Explain alias validity, precedence, lifecycle dates, and the no-zero-fill rule for users and
provider authors.

## Baseline

- [docs/data-model.md](/docs/data-model.md) documents tables; [docs/providers.md](/docs/providers.md) documents the provider contract.

## Files

| Action | Path                   | Purpose |
|--------|------------------------|---------|
| Modify | `docs/data-model.md`   | `languages.introduced/retired`; alias validity + precedence |
| Modify | `docs/providers.md`    | "Adding a source alias / handling a rename" how-to with a `SourceAlias` example |
| Modify | `README.md`            | One sentence: missing history before a language exists is shown as a gap |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|--------|------|------------------|---------|-------|
| `## Alias validity` | heading | in `docs/data-model.md` | - | anchor referenced by 0005 Task 04.0 |

## Behaviour & validators

1. Examples use real catalog entries after subtask 02.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| - (docs only) | -    | -    | `python3 scripts/check_doc_links.py docs/` shows no new problems |

## Success criteria

- [ ] Three docs updated; link check clean for touched files.

## Constraints

- Absolute links per [docs/roadmap/README.md](/docs/roadmap/README.md#linking-convention).

## Out of scope

- CLI help text for 0005 alias commands.

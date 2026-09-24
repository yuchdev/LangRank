# Subtask 04.0/09 - Provider documentation

**Task:** [04.0 - JetBrains Developer Ecosystem Provider](/docs/roadmap/0001-new-rating-providers/04.0-jetbrains-provider/README.md) ·
**Role:** Docs Writer · **Depends on:** 08 · **Status:** ⬜ Not started

## Goal

User docs for `jetbrains`: metric families, weighting difference, raw-data import how-to.

## Baseline

`docs/providers.md`; `docs/source-notes/jetbrains.md`.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `docs/providers.md` | `## JetBrains Developer Ecosystem provider` section |
| Modify | `README.md` | Provider list |

## Symbols / fields

Section contains: 6-metric table (published vs `-raw`), weighting caveat, question-wording
note, raw-data import steps, example
`langrank plot --rating jetbrains --metric jetbrains-used-last-12-months --languages python,kotlin,java --years 8`.

## Behaviour & validators

1. States that `-raw` numbers will not match the published report.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| - (doc-only) | - | - | Link check clean |

## Success criteria

- [ ] All items present.

## Constraints

- Absolute-from-root links.

## Out of scope

- -

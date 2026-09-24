# Subtask 03.0/08 - Provider documentation

**Task:** [03.0 - IEEE Spectrum Provider](/docs/roadmap/0001-new-rating-providers/03.0-ieee-spectrum-provider/README.md) ·
**Role:** Docs Writer · **Depends on:** 07 · **Status:** ⬜ Not started

## Goal

User docs for `ieee-spectrum`, including how to add a new edition by import.

## Baseline

`docs/providers.md`; `docs/source-notes/ieee-spectrum.md`.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `docs/providers.md` | `## IEEE Spectrum provider` section |
| Modify | `README.md` | Provider list |

## Symbols / fields

Section contains: profile table, metric-ID scheme, "profiles are not one series" warning,
CSV header for `langrank import`, a new-edition checklist (update CSV, source-note edition
table, `EDITION_PROFILES`, methodology note), example
`langrank plot --rating ieee-spectrum --metric ieee-spectrum-spectrum-rank --languages python,java,c++ --years 10`.

## Behaviour & validators

1. Links to the source note's edition table.

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

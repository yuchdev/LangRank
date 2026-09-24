# Subtask 01.0/08 - Provider documentation

**Task:** [01.0 - Stack Overflow Tags Provider](/docs/roadmap/0001-new-rating-providers/01.0-stack-overflow-tags-provider/README.md) ·
**Role:** Docs Writer · **Depends on:** 07 · **Status:** ⬜ Not started

## Goal

Document `stackoverflow-tags` for users: what it measures, how it differs from
`stackoverflow-survey`, sources, denominators, quota and examples.

## Baseline

`docs/providers.md` describes the demo and bootstrap providers; `README.md` has the
methodological warning.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `docs/providers.md` | New `## Stack Overflow tags provider` section |
| Modify | `README.md` | Add provider to the provider list / examples |
| Modify | `docs/source-notes/stackoverflow-tags.md` | Final "Last verified date", parser version |

## Symbols / fields

Section must contain: metric table (3 IDs, unit, derived?), `--source api|sede`, the
denominator table, API-key env var `LANGRANK_STACKEXCHANGE_KEY`, quota arithmetic, a SEDE
query template producing `month,tag,questions,union_total`, and the example
`langrank plot --rating stackoverflow-tags --metric stackoverflow-tags-question-share --languages python,javascript,c++,rust --years 10`.

## Behaviour & validators

1. States explicitly: tag activity ≠ usage; shares may exceed 100 % in total; api and sede
   shares are different series.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| - (doc-only) | - | - | `python3 scripts/check_doc_links.py docs/` introduces no new problems |

## Success criteria

- [ ] Section present with every item above; link check clean.

## Constraints

- Absolute-from-root links.

## Out of scope

- Cross-rating comparison guidance (Milestone 0002).

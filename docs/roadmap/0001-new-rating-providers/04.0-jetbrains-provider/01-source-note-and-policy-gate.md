# Subtask 04.0/01 - Source note & legal/source-policy gate

**Task:** [04.0 - JetBrains Developer Ecosystem Provider](/docs/roadmap/0001-new-rating-providers/04.0-jetbrains-provider/README.md) ·
**Role:** Security Auditor · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Document the survey editions, their language questions, weighting, and raw-data terms; close
the [legal / source-policy review gate](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate).

## Baseline

`docs/source-notes/stackoverflow-survey.md` is the analogous note.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Create | `docs/source-notes/jetbrains.md` | Note + edition table + gate |

## Symbols / fields

Standard keys plus an edition table: `year`, `report_url`, `raw_data_url` (or "none"),
`raw_data_terms`, `respondents_after_cleaning` (e.g. 2025: 24,534; 2024: 23,262),
`weighting` description, `published_at`, and per-metric question wording.

## Behaviour & validators

1. Gate verdict for `published` (`manual-only` curation) and `raw-data` (`manual-only`
   import; download requires a browser/form - no automated download).
2. States whether raw data may be cached/redistributed.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| - (doc-only) | - | - | Link check clean |

## Success criteria

- [ ] Every year 2017+ has a row, even if "no language question comparable".

## Constraints

- Absolute-from-root links.

## Out of scope

- Non-language survey topics.

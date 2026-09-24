# Subtask 03.0/01 - Source note & legal/source-policy gate

**Task:** [03.0 - IEEE Spectrum Provider](/docs/roadmap/0001-new-rating-providers/03.0-ieee-spectrum-provider/README.md) ·
**Role:** Security Auditor · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Document IEEE Spectrum TPL editions, profiles and methodology per year, and close the
[legal / source-policy review gate](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate).

## Baseline

No IEEE note exists.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Create | `docs/source-notes/ieee-spectrum.md` | Source note + edition table + gate |

## Symbols / fields

Required: standard keys (What it measures - composite weighted index; Official source;
Historical availability; Acquisition - manual transcription; Metrics; Granularity - annual;
Known limitations; Terms; Parser version; Last verified) **plus an edition table**:

| Column | Meaning |
|--------|---------|
| `year` | Edition year |
| `url` | Article/app URL |
| `profiles` | Profiles published that year |
| `coverage` | Full list / top-N per profile |
| `methodology_version` | e.g. `ieee-2025-manual-7metrics` |
| `notes` | Metric/source changes |

## Behaviour & validators

1. Gate verdict: expected `manual-only` (no automated fetch; ranks/scores are facts, stored
   with attribution and URL; article text is never copied).

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| - (doc-only) | - | - | Link check clean |

## Success criteria

- [ ] Edition table covers every year subtask 04 imports.

## Constraints

- Absolute-from-root links.

## Out of scope

- Reproducing IEEE's weighting from raw metrics.

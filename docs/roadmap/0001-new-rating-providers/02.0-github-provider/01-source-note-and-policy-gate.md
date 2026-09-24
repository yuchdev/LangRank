# Subtask 02.0/01 - Source note & legal/source-policy gate

**Task:** [02.0 - GitHub Provider](/docs/roadmap/0001-new-rating-providers/02.0-github-provider/README.md) ·
**Role:** Security Auditor · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Document both GitHub variants and close the
[legal / source-policy review gate](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate).

## Baseline

Existing notes in `docs/source-notes/` use a flat bullet format.

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Create | `docs/source-notes/github.md` | One note, two `##` sections (Octoverse, Innovation Graph) |

## Symbols / fields

| Key | Octoverse | Innovation Graph |
|-----|-----------|------------------|
| What it measures | Annual published language ranking (basis varies by year) | Quarterly count of developers pushing code, per economy and Linguist language |
| Official source | github.blog Octoverse posts / octoverse.github.com | `github/innovationgraph` `data/languages.csv` |
| Historical availability | Per-edition; record which years expose a top-N list | 2020-Q1 onward |
| Licence / redistribution | GitHub content terms - store ranks (facts) + URL only | CC0-1.0 - raw CSV may be cached and redistributed |
| Automation | Manual curation only | Scheduled fetch of one raw file per quarter; GitHub raw rate limits noted |
| Known biases | Basis changes between editions | ≥100-developer suppression; IP-based geolocation |
| Gate verdict | `manual-only` | `approved-for-scheduled-fetch` (expected) |

## Behaviour & validators

1. Note lists the ranking basis for every Octoverse edition that subtask 07 imports.
2. Note states explicitly that neither variant equals RedMonk's GitHub component.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| - (doc-only) | - | - | Link check clean on the new note |

## Success criteria

- [ ] `docs/source-notes/github.md` exists with both sections and verdicts.

## Constraints

- Absolute-from-root links.

## Out of scope

- Chart-extraction legality (feature not built).

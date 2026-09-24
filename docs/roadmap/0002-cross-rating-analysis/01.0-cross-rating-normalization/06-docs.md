# Subtask 01.0/06 - Cross-Rating Analysis User Docs

**Task:** [01.0 - Cross-Rating Normalization & Comparison](/docs/roadmap/0002-cross-rating-analysis/01.0-cross-rating-normalization/README.md) ·
**Role:** Docs Writer · **Depends on:** 04 · **Status:** ⬜ Not started

## Goal

Create the user-facing reference for cross-rating comparison that Tasks 02.0 and 03.0 will
extend, so the semantics of `n`, top-N lists and derived labelling are documented, not implied.

## Baseline

- `README.md` § "Important methodological warning".
- `docs/architecture.md`, `docs/data-model.md` - no analysis layer yet.

## Files

| Action | Path                               | Purpose                                                      |
|--------|------------------------------------|--------------------------------------------------------------|
| Create | `docs/cross-rating-analysis.md`    | Methods, `n` resolution, top-N caveat, `plot compare` usage  |
| Modify | `docs/architecture.md`             | Add `analysis/` (pure) and `services/comparison.py` to the pipeline description |
| Modify | `README.md`                        | One-paragraph pointer + example `plot compare` command        |
| Modify | `docs/README.md`                   | Registry entry for the new doc                               |

## Symbols / fields

| Symbol (doc section)                               | Kind    | Notes |
|----------------------------------------------------|---------|-------|
| `## Why raw values are never shared on one axis`   | heading | |
| `## rank_percentile`                               | heading | Formula, ties, `n = 1` |
| `## How n is determined`                           | heading | The four `population_source` values in precedence order |
| `## Top-N sources and --common-top`                | heading | Worked example: TIOBE top-20 vs PYPL ~28 |
| `## plot compare`                                  | heading | Every option, exit codes |
| `## Known caveats`                                 | heading | PYPL `c-cpp`, provider-computed SO survey rank, bundled CSV subset → `max_rank` fallback |

## Behaviour & validators

1. Every CLI option documented matches `langrank plot compare --help` exactly (names, defaults).
2. Links use absolute-from-repo-root form; `python3 scripts/check_doc_links.py docs/` passes.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| (link check)  | `scripts/check_doc_links.py` | - | No dangling links/anchors in changed docs |

## Success criteria

- [ ] `docs/cross-rating-analysis.md` exists with the six headings above.
- [ ] `python3 scripts/check_doc_links.py docs/` reports no new problems.

## Constraints

- Docs never present a derived value as source data; examples show the derived label.

## Out of scope

- Composite and snapshot sections - added by
  [02.0/05](/docs/roadmap/0002-cross-rating-analysis/02.0-composite-index/05-docs.md) and
  [03.0/04](/docs/roadmap/0002-cross-rating-analysis/03.0-snapshot-comparison/04-docs.md).

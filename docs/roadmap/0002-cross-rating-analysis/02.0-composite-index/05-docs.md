# Subtask 02.0/05 - Composite Docs

**Task:** [02.0 - Composite Index](/docs/roadmap/0002-cross-rating-analysis/02.0-composite-index/README.md) ·
**Role:** Docs Writer · **Depends on:** 04 · **Status:** ⬜ Not started

## Goal

Document the composite so no reader can mistake it for a source rating, and so every
ingredient's effect (weights, policy, year alignment) is explained with a worked example.

## Baseline

- `docs/cross-rating-analysis.md` (from
  [01.0/06](/docs/roadmap/0002-cross-rating-analysis/01.0-cross-rating-normalization/06-docs.md)).

## Files

| Action | Path                              | Purpose                        |
|--------|-----------------------------------|--------------------------------|
| Modify | `docs/cross-rating-analysis.md`   | `## Composite index` section   |
| Modify | `README.md`                       | Example + "derived, opt-in" warning next to the methodological warning |

## Symbols / fields

| Symbol (doc section)                         | Kind    | Notes |
|----------------------------------------------|---------|-------|
| `## Composite index`                         | heading | "Not a popularity score" disclaimer first |
| `### Required ingredients`                   | heading | The five options, why none has a default |
| `### Missing-data policies`                  | heading | Three policies with a 2-language × 2-rating worked table |
| `### Year alignment`                         | heading | Latest-in-year, no monthly averaging |
| `### Reading the output`                     | heading | Contributions, effective weights, gaps, sidecar |

## Behaviour & validators

1. Options match `langrank composite --help`.
2. Worked example numbers are reproducible from the formula in 02.0/02.

## Tests

| Test function | File | Type | Asserts |
|---------------|------|------|---------|
| (link check)  | `scripts/check_doc_links.py` | - | No dangling links/anchors |

## Success criteria

- [ ] Section present; `python3 scripts/check_doc_links.py docs/` reports no new problems.

## Constraints

- Every composite number shown in docs is labelled `derived composite`.

## Out of scope

- Snapshot docs ([03.0/04](/docs/roadmap/0002-cross-rating-analysis/03.0-snapshot-comparison/04-docs.md)).

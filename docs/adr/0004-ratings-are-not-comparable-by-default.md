# 0004 - Ratings Are Not Comparable by Default; Cross-Rating Views Require Explicit Normalization

> **Status:** Accepted
>
> **Date:** 2026-09-29 _(recorded retroactively; the separation is in force today, the normalization half is planned in milestone 0002)_
>
> **Supersedes:** _(none)_
>
> **Superseded by:** _(none)_

## Context

The obvious feature request for a tool like LangRank is "one popularity score per language."
The sources cannot support that without a stated method, because they measure different
phenomena on different scales (see the methodological warning in [/README.md](/README.md)):

| Source                            | Measures                                                                | Native scale                 |
|-----------------------------------|-------------------------------------------------------------------------|------------------------------|
| TIOBE                             | search-engine visibility                                                | rank + % rating              |
| PYPL                              | tutorial-search interest                                                | rank + % share               |
| RedMonk                           | GitHub + Stack Overflow activity (tiered, ties)                         | rank                         |
| Stack Overflow Survey / JetBrains | self-reported usage (population, weighting, wording differ per edition) | % of respondents             |
| Stack Overflow tags               | question activity                                                       | counts, derived share / rank |
| GitHub                            | repository / pusher activity                                            | counts, derived share / rank |
| IEEE Spectrum                     | composite weighted index (edition-specific score scale)                 | rank + score                 |

A TIOBE rating of 10% and a JetBrains usage of 10% are not the same quantity; rank 5 among
20 RedMonk tiers is not rank 5 among 50 TIOBE entries. Plotting them on one axis would
produce a chart that looks authoritative and means nothing.

## Decision

1. **Every metric is scoped to exactly one rating.** Metric IDs are namespaced by provider
   (`tiobe-rank`, `stackoverflow-tags-question-share`, `github-innovation-graph-rank`, ...),
   and `rating_id` is part of the observation natural key
   ([ADR 0003](/docs/adr/0003-sqlite-storage-and-natural-key-upsert.md)). Raw values are never
   rescaled at ingest (e.g., IEEE Spectrum scores stay edition-specific).
2. **Single-metric plots only.** `langrank plot` selects one `metric_id`, so a chart shows a
   single rating's native axis. No feature may place raw values from different ratings on one
   shared axis.
3. **Cross-rating comparison is a separate, explicit, derived operation** (milestone 0002
   task 01.0): the user names the ratings and a normalization method; the first method is
   `rank_percentile` (`score = 1 - (r - 1) / max(n - 1, 1)`). Results are labeled derived
   ([ADR 0002](/docs/adr/0002-provenance-carrying-observations.md)) and computed on read, not
   persisted, unless a later ADR decides otherwise.
4. **No silent aggregation.** A composite index (milestone 0002 task 02.0) must take explicit
   sources, metric choice, normalization method, weights and missing-data handling - there is
   no default average.
5. **Granularity is not mixed silently either.** Month, quarter and year series are not
   combined without explicit resampling.

## Alternatives Considered

| Alternative                                                                                            | Pros                                                                  | Cons                                                                                                                | Reason rejected                                                                      |
|--------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|
| Normalize everything to a common 0-1 score at ingest                                                   | One comparable column; simple charts                                  | Bakes one method into stored data; destroys the raw published value; method changes require re-ingesting everything | Rejected - violates "store what the source published" and makes the method invisible |
| Allow multi-rating raw plots with a legend warning                                                     | Quick to build; users ask for it                                      | Warnings get ignored; screenshots travel without the caveat                                                         | Rejected - the chart itself must not be misleading                                   |
| Shared generic metric IDs (`rank`, `share`) across providers                                           | Shorter CLI flags; easy "all ranks" queries                           | Invites cross-rating queries and plots by accident                                                                  | Rejected - namespaced IDs make the separation structural                             |
| Per-rating native axes now; explicit, labelled, compute-on-read normalization for comparisons (chosen) | Honest charts; raw data preserved; normalization methods are additive | No single "score" out of the box; comparison features wait for milestone 0002                                       | **Accepted**                                                                         |

## Consequences

### Positive

- Every stored and plotted value keeps its source's meaning and scale.
- New normalization methods (`minmax`, `zscore`) can be added later without migrating data.
- Users who want a composite must state its assumptions, which then travel with the output.

### Negative

- The most-requested feature ("who is #1 overall") is intentionally not a one-liner.
- CLI metric names are longer because they are provider-namespaced.
- Compute-on-read normalization repeats work on every comparison query; acceptable at current
  data sizes.

## Validation / Rollout

- Milestone 0002 task 01.0 success criterion: `plot compare` refuses or clearly labels an
  unnormalized cross-rating request, and `rank_percentile` is unit-tested against known inputs.
- Review checklist: any plot/export path that accepts more than one `metric_id` onto a single
  value axis without a normalization method is a blocking finding.

## Links

- **Roadmap task:** [/docs/roadmap/0002-cross-rating-analysis/plan.md](/docs/roadmap/0002-cross-rating-analysis/plan.md)
- **Supporting specs:** [/README.md](/README.md) (methodological warning), [/docs/data-model.md#granularity](/docs/data-model.md#granularity)
- **Related ADRs:** [0002](/docs/adr/0002-provenance-carrying-observations.md), [0003](/docs/adr/0003-sqlite-storage-and-natural-key-upsert.md)

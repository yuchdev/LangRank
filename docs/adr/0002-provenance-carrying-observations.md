# 0002 - Provenance-Carrying Observations; Never Fabricate Values

> **Status:** Accepted
>
> **Date:** 2026-09-29 _(recorded retroactively; model in force since the core scaffold, `6d57d06`; derived-value flags exercised from task 01.0 onward)_
>
> **Supersedes:** _(none)_
>
> **Superseded by:** _(none)_

## Context

LangRank's output is only useful if a reader can answer, for any number it shows: *which
source published this, for which period, under which metric definition, parsed by which
parser version, acquired how, and mapped to this language by which rule?* The sources make
this hard:

- They publish different things: ranks, percentages, raw counts, scores on edition-specific
  scales, survey shares with question wording that changes between editions.
- Several useful metrics are **not published** and must be computed (Stack Overflow
  `question_share` and `rank`, GitHub Innovation Graph shares and ranks, IEEE Spectrum
  derived ranks). If computed values look like published ones, users will cite LangRank's
  arithmetic as TIOBE's or Stack Overflow's.
- Coverage has holes (a language absent from an edition, a month missing from an archive).
  Filling them makes charts prettier and data wrong.
- Sources silently revise history; re-fetching must reveal that a stored row changed.

## Decision

**The canonical unit is an immutable `Observation` that carries its own provenance, and
LangRank never invents a value.**

1. **Two record types, one boundary.** `SourceRecord` holds the provider's raw language string
   and values as parsed; `Observation` holds the canonical `language_id` plus provenance. Both
   are `frozen=True` dataclasses (`src/langrank/models.py`); stages build new objects rather
   than mutating.
2. **Mandatory provenance fields on every `Observation`:** `source_language_name`,
   `source_url`, `source_document_id`, `retrieved_at`, `source_published_at`,
   `parser_version`, `raw_record_hash`, plus `is_derived` / `derivation_method`. Raw payload
   bytes are cached and recorded as a `RawArtifact` with a `sha256`.
3. **Change detection by hash.** `build_observation_hash` (`providers/common.py`) hashes the
   raw `SourceRecord` deterministically; the stored `raw_record_hash` lets a re-fetch show that
   upstream data changed for an existing natural key.
4. **Derived values are labeled, never disguised.** Anything LangRank computes - shares,
   ranks via `compute_competition_ranks`, future cross-rating normalizations - sets
   `is_derived=True` and a machine-readable `derivation_method` naming the rule and its
   denominator (e.g. `rank_by_question_share:tracked_language_union`). Validators check that
   metrics registered as derived are flagged (e.g. `share_not_derived` in `stackoverflow-tags`).
5. **No fabrication.** Missing observations stay missing: no interpolation, no carry-forward,
   no default ranks, no values read off chart geometry, no guessing of unmapped language
   labels. Publisher-authored numbers in text, alt text or chart data files count as
   published; pixel positions do not.

## Alternatives Considered

| Alternative                                                                             | Pros                                                                | Cons                                                                                                   | Reason rejected                                                                                  |
|-----------------------------------------------------------------------------------------|---------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| Store only `(rating, language, period, value)` and keep provenance in logs / fetch runs | Smaller rows; simpler schema                                        | Row-level provenance lost once rows are updated or exported; exports cannot cite sources               | Rejected - the export and plot layers must be able to cite any single value                      |
| Separate tables for derived vs raw values                                               | Impossible to confuse the two in SQL                                | Every query, export and plot would union two shapes; derived metrics would need their own natural keys | Rejected - a flag + method on one shape is enforceable by validators and visible in every export |
| Interpolate or carry forward missing periods for smoother charts                        | Continuous lines; simpler plotting                                  | Presents values no source published; hides coverage gaps that matter methodologically                  | Rejected outright - violates the project's core claim of traceability                            |
| Mutable dataclasses / dicts between stages                                              | Convenient in-place fixes during normalize                          | Stage outputs can be changed after validation; hashes stop matching content                            | Rejected - frozen objects make "what was validated is what is stored" hold by construction       |
| Frozen provenance-carrying `Observation`, flagged derivations, no fabrication (chosen)  | Every value traceable; derived values visible; revisions detectable | Wide rows; providers must populate many fields; coverage gaps show up as gaps                          | **Accepted**                                                                                     |

## Consequences

### Positive

- Every exported CSV/JSON row can be traced to its source document, parser version and
  normalization rule without consulting logs.
- Upstream revisions are detectable by comparing `raw_record_hash` on re-fetch.
- Milestone 0002's cross-rating work can add normalized metrics without a schema change: they
  are simply derived observations with a documented `derivation_method`.

### Negative

- Providers carry more boilerplate per observation (mitigated by `build_observation`).
- Charts and tables show real gaps; users may read them as bugs. Documentation and caveats in
  `ProviderMetadata` must explain coverage.
- Bumping `parser_version` changes provenance for all re-fetched rows, which is intended but
  makes diffs between fetches noisier.

## Validation / Rollout

- Contract tests assert golden `Observation` outputs, including provenance fields and
  `is_derived` / `derivation_method`.
- Provider validators emit named codes for provenance violations (e.g. `share_not_derived`).
- Review checklist: any new code path that constructs an `Observation` without going through
  `build_observation`, or that fills a missing period, is a blocking finding.

## Links

- **Roadmap task:** [/docs/roadmap/0001-new-rating-providers/plan.md](/docs/roadmap/0001-new-rating-providers/plan.md); follow-up in [/docs/roadmap/0003-historical-data-quality/plan.md](/docs/roadmap/0003-historical-data-quality/plan.md)
- **Supporting specs:** [/docs/data-model.md#derived-observations](/docs/data-model.md#derived-observations)
- **Related ADRs:** [0001](/docs/adr/0001-linear-provider-pipeline.md), [0003](/docs/adr/0003-sqlite-storage-and-natural-key-upsert.md), [0004](/docs/adr/0004-ratings-are-not-comparable-by-default.md)

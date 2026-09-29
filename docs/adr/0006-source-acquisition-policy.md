# 0006 - Source Acquisition Policy: Policy Gate, Cache-First Fetch, Bundled Snapshots, Manual Import

> **Status:** Accepted
>
> **Date:** 2026-09-29 _(recorded retroactively; policy gate defined in the milestone 0001 plan, rulings recorded 2026-09-25/26 during milestone 0001)_
>
> **Supersedes:** _(none)_
>
> **Superseded by:** _(none)_

## Context

LangRank's sources are published by third parties under very different terms:

- some offer an official API with a key and a request budget (Stack Exchange API);
- some publish versioned data in a public repository (GitHub Innovation Graph);
- some publish only web pages, charts or PDFs per edition (TIOBE, IEEE Spectrum, RedMonk,
  Octoverse, JetBrains published percentages), sometimes behind robot rules;
- some offer raw data only as a manual download (JetBrains raw survey dumps, SEDE query
  results).

Unattended scraping of pages that forbid it, or re-hosting data whose redistribution terms
are unclear, is a legal and ethical risk. At the same time the project needs reproducible
builds, offline tests, and a working `langrank fetch all` for new users who have no API key.

## Decision

1. **Per-source policy gate before any unattended fetch.** Each provider documents, in its
   `docs/source-notes/<id>.md`, official API/download availability, robot policy, terms of
   use, a reasonable request rate, and whether raw redistribution is allowed. If
   redistribution is unclear the provider ships normalized derived data with documented
   provenance only. This gate also applies to future external plugins (milestone 0006).
2. **Every provider declares an acquisition mode**, selectable with `--source`, from a small
   set:
   - **API / download** - automated, rate-limited, through the shared hardened HTTP client
     (`util/http.py`: timeouts, bounded retries on transient errors only, byte caps, secrets
     scrubbed from errors, fixed `User-Agent`).
   - **Bundled curated snapshot** - a CSV committed under `src/langrank/providers/data/`,
     transcribed from publisher-authored numbers, read with zero network requests (default
     for TIOBE-style edition sources, IEEE Spectrum, JetBrains published, Octoverse).
   - **Manual import** - `langrank import --rating <id> <file>` for data the operator obtains
     themselves; large formats implement `SupportsRawImport` with explicit byte/row caps.
   Modes that are manual-only are rejected by `fetch` rather than silently falling back.
3. **Cache-first, provenance-recorded fetches.** Raw payload bytes are cached under
   `{cache_path}/{provider_id}/` with their `sha256` and recorded as a `RawArtifact`;
   `--offline` replays the cache, `--no-cache` skips writing it.
   `upstream_latest_period()` probes cache and bundled snapshot only - it never hits the
   network.
4. **Acceptable evidence for a value:** numbers the publisher authored in text, tables, alt
   text or chart data files (e.g., Flourish/JSON behind a chart). **Not acceptable:** values it
   read off chart geometry or pixels, or guessed. Reconstructions from third parties are
   marked in provenance (e.g., TIOBE `third_party_reconstruction`).
5. **Tests never need the network.** Contract tests run on committed fixtures; tests that do
   real requests carry the `live` marker and are skipped unless `LANGRANK_LIVE_TESTS=1`. CI
   runs plain `uv run pytest`. Live network during development is allowed for capturing
   fixtures; one-off, user-directed, low-volume retrieval against a robots-restricted page
   (IEEE edition pages) is permitted for curation but is never automated.

## Alternatives Considered

| Alternative                                                                                         | Pros                                                              | Cons                                                                                     | Reason rejected                                                                          |
|-----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| Scrape every source live on each fetch                                                              | Always current; no curation work                                  | Violates some terms/robots; brittle HTML parsing; non-reproducible; tests need network   | Rejected - legal risk and flakiness                                                      |
| Ship only code, require users to obtain all data                                                    | No redistribution questions at all                                | `fetch all` useless out of the box; every user repeats curation                          | Rejected - bundled snapshots of publisher-authored numbers are the pragmatic middle      |
| Extract values from chart images when no numbers are published                                      | More coverage (older editions)                                    | Numbers are estimates presented as data; unverifiable                                    | Rejected - conflicts with [ADR 0002](/docs/adr/0002-provenance-carrying-observations.md) |
| Silent fallback to bundled data when the API fails                                                  | Fetch "always works"                                              | User cannot tell which mode produced the data                                            | Rejected - modes are explicit and recorded in provenance                                 |
| Policy gate + explicit modes (API / bundled / manual import) + cache-first + offline tests (chosen) | Legally defensible; reproducible; works offline; clear provenance | Bundled data lags upstream until someone curates a new edition; per-source research cost | **Accepted**                                                                             |

## Consequences

### Positive

- A new user gets useful data from `langrank fetch all` without keys or scraping.
- The full test suite runs offline and deterministically in CI.
- Each value's acquisition mode is traceable, and raw bytes are reproducible from the cache.

### Negative

- Bundled sources need manual curation per edition (process in
  [/docs/providers.md#adding-a-future-edition](/docs/providers.md#adding-a-future-edition));
  milestone 0004 (freshness) and 0007 (source research tooling) exist to reduce that cost.
- Some historical editions remain uncovered because their numbers exist only in charts.
- The policy gate adds research work before a new source can be scheduled.

## Validation / Rollout

- Each provider's source note carries the gate verdict and a last-verified date; security
  threat models exist for providers with network or import paths: `/docs/security/`
- CI stays green with no network access; any new test performing requests without the `live`
  marker is a blocking review finding.

## Links

- **Roadmap task:** [/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate); follow-ups in [/docs/roadmap/0004-freshness-and-releases/plan.md](/docs/roadmap/0004-freshness-and-releases/plan.md) and [/docs/roadmap/0007-source-research-tooling/plan.md](/docs/roadmap/0007-source-research-tooling/plan.md)
- **Supporting specs:** `/docs/source-notes/`, [/docs/test/conventions.md](/docs/test/conventions.md), [/docs/architecture.md#manual-import-path](/docs/architecture.md#manual-import-path)
- **Related ADRs:** [0001](/docs/adr/0001-linear-provider-pipeline.md), [0002](/docs/adr/0002-provenance-carrying-observations.md)

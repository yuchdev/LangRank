# 0001 - Linear Provider Pipeline with Persistence-Free Providers

> **Status:** Accepted
>
> **Date:** 2026-09-29 _(recorded retroactively; decision in force since the core scaffold, `6d57d06`, and extended by task 05.0 OOP provider refactoring)_
>
> **Supersedes:** _(none)_
>
> **Superseded by:** _(none)_

## Context

LangRank ingests nine sources (`demo`, `tiobe`, `pypl`, `redmonk`, `stackoverflow-survey`,
`stackoverflow-tags`, `github`, `ieee-spectrum`, `jetbrains`) that differ in almost
everything: transport (REST API, CSV download, bundled curated CSV, manual import), payload
shape, granularity (month / quarter / year), and what they measure. The roadmap adds more
(milestone 0006 plans external provider plugins), so every source-specific quirk must be
contained in one place, while storage, validation bookkeeping, querying and presentation stay
source-agnostic.

Forces:

- Parsers must be testable from fixtures alone - no network, no database - so contract tests
  (`tests/contract/`) can pin golden outputs per provider.
- A failed or invalid fetch must never leave partially written observations behind, and every
  attempt must be auditable (`fetch_runs`).
- `--dry-run` must exercise the whole pipeline, including validation, without persisting.
- Nine handwritten providers had accumulated duplicated lifecycle code (cache directory,
  normalizer, window trimming, unmapped-label tracking) before task 05.0.

## Decision

**Every source is a provider that implements one fixed, linear pipeline, and providers never
persist anything themselves.**

```
fetch(request) -> FetchPayload
  -> parse(payload) -> list[SourceRecord]
  -> normalize(records) -> list[Observation]
  -> validate(observations) -> ValidationReport
  -> Database.upsert_observations()   (service layer only)
```

See [assets/0001-provider-pipeline.mmd](/docs/adr/assets/0001-provider-pipeline.mmd).

1. **Type contract:** `RatingProvider` (`src/langrank/providers/base.py`) is a
   `@runtime_checkable` `Protocol` with `metadata`, `fetch`, `parse`, `normalize`, `validate`
   and `upstream_latest_period`. Services and the CLI program only against this protocol.
2. **Implementation base:** all built-in providers inherit `BaseRatingProvider` (ABC), which
   owns the shared lifecycle state (`_cache_dir`, `_normalizer`, `_retrieved_at`,
   `last_unmapped`) and helpers (`_stash_request_window`, `_filter_window`,
   `_record_unmapped`, network-free `upstream_latest_period`). Subclasses implement only the
   five abstract stage methods. Stateless helpers live in `providers/common.py`.
3. **Only `fetch()` may perform I/O against the outside world.** `parse`, `normalize` and
   `validate` are pure functions of their inputs. No provider stage touches SQLite.
4. **Orchestration belongs to `FetchService`** (`services/fetch.py`): it records the
   `fetch_run`, stores the `RawArtifact`, runs the stages, and calls
   `upsert_observations` **only if** `report.ok` and the request is not a dry run. Exceptions
   close the run as `failed` and re-raise.
5. **Registration is explicit:** providers are hand-registered in `providers/registry.py`.
   Optional capabilities are separate protocols (e.g. `SupportsRawImport` for
   `langrank import`), checked with `isinstance`, rather than optional methods on the base.

## Alternatives Considered

| Alternative                                                                                | Pros                                                                           | Cons                                                                                                                                                           | Reason rejected                                                                                   |
|--------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| Providers write observations to the DB directly                                            | Fewer layers; provider can stream large sources                                | Every provider re-implements transactions, fetch-run bookkeeping and dry-run; parsers need a DB in tests; a validation failure can leave half a source written | Rejected - breaks fixture-only contract tests and the "invalid data is never persisted" guarantee |
| Protocol only, no shared base class (pre-05.0 state)                                       | Maximum freedom per provider                                                   | Same cache/normalizer/window/unmapped code copied nine times and drifting                                                                                      | Superseded by task 05.0 - the Protocol stays as the contract, the ABC removes duplication         |
| Base class only, no Protocol                                                               | One concept instead of two                                                     | Services would depend on an implementation class; future external plugins (milestone 0006) would be forced to inherit it                                       | Rejected - structural typing keeps the public contract smaller than the implementation base       |
| Entry-point / auto-discovery registry                                                      | Adding a provider needs no registry edit                                       | Import-time side effects; harder to see what ships; plugin trust questions unresolved                                                                          | Deferred to milestone 0006 task 02.0; the flat dict stays for built-ins                           |
| Linear stage pipeline, Protocol + `BaseRatingProvider`, service-owned persistence (chosen) | Fixture-testable stages; one place for transactions and audit; dry-run is free | Whole source is held in memory between stages; a provider cannot partially succeed                                                                             | **Accepted**                                                                                      |

## Consequences

### Positive

- `parse`/`normalize`/`validate` are exercised by the registry-driven contract suite from
  fixtures, with golden outputs, and without network or database.
- Validation errors block persistence uniformly; every attempt, including failures and dry
  runs, is recorded in `fetch_runs`.
- A new provider is a subclass plus a registry entry plus aliases
  ([/docs/providers.md#implementing-a-new-provider](/docs/providers.md#implementing-a-new-provider)).

### Negative

- Stages pass whole lists, so very large sources are memory-bound; milestone 0006 task 03.0
  (large-source performance) must revisit this without letting providers touch the DB.
- An all-or-nothing upsert means one invalid row rejects an entire fetch; providers must
  report data-quality problems as `WARNING` unless they truly invalidate the batch.
- Two concepts (Protocol and ABC) must be kept in sync when a pipeline method is added.

## Validation / Rollout

- `tests/contract/` runs the same suite over every registered provider; a provider that needs
  a DB or network to parse fails it.
- Code review (`feature-reviewer`) rejects any `Database` import under `src/langrank/providers/`.
- Already fully rolled out: all nine providers were migrated in task 05.0.

## Links

- **Roadmap task:** [/docs/roadmap/0001-new-rating-providers/05.0-oop-provider-refactoring/README.md](/docs/roadmap/0001-new-rating-providers/05.0-oop-provider-refactoring/README.md)
- **Supporting specs:** [/docs/architecture.md](/docs/architecture.md), [/docs/providers.md#provider-contract](/docs/providers.md#provider-contract)
- **Diagrams:** [assets/0001-provider-pipeline.mmd](/docs/adr/assets/0001-provider-pipeline.mmd)
- **Related ADRs:** [0002](/docs/adr/0002-provenance-carrying-observations.md), [0006](/docs/adr/0006-source-acquisition-policy.md)

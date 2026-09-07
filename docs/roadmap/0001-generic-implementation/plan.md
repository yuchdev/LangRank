# Milestone 0001 - Generic Implementation

**Package:** `langrank` | **Module root:** `src/langrank/`
**Depends on:** the already-merged core architecture — `RatingProvider` protocol
(`providers/base.py`), the five bootstrap providers (`demo`, `tiobe`, `pypl`,
`redmonk`, `stackoverflow-survey`), `Database`/migrations (`db/`), and the
`FetchService`/`QueryService`/`ValidationService`/`StatusService` layer
(`services/`). See [CLAUDE.md](/CLAUDE.md) for the pipeline and invariants
those pieces already establish.

This milestone grows `langrank` from that bootstrap core into a genuinely
**generic** implementation: more providers exercising the same contracts,
cross-rating comparison built on explicit normalization (never a raw shared
axis), operational tooling (freshness checks, scheduled updates, dataset
releases), data-quality reporting, and the schema/CLI extensions those
features need. It does **not** cover UI, hosting, or anything beyond the CLI +
SQLite architecture already in place.

> **Why providers come first.** Every later task in this milestone —
> cross-rating normalization (05.0), the composite index (06.0), snapshot
> comparison (07.0), multi-chart reports (13.0), and the release workflow
> (10.0) — needs more than one reliable provider history to be meaningful.
> Tasks 01.0-04.0 (new providers) are therefore the milestone's foundation,
> the same way `providers/demo.py` was the foundation of the pre-milestone
> bootstrap.

## Table of contents

- [Tasks](#tasks)
- [Shared contracts (authoritative)](#shared-contracts-authoritative)
- [Per-task specifications](#per-task-specifications)
- [Dependency graph](#dependency-graph)
- [Milestone exit criteria](#milestone-exit-criteria)

---

## Tasks

| Task | Name                                          | Category        | Output                                                                 |
|------|------------------------------------------------|-----------------|-------------------------------------------------------------------------|
| 01.0 | Stack Overflow Tags Provider                    | provider        | `providers/stackoverflow_tags.py`; monthly tag-activity + share metric  |
| 02.0 | GitHub Provider                                 | provider        | `providers/github.py`; Octoverse/Innovation-Graph rank & activity       |
| 03.0 | IEEE Spectrum Provider                          | provider        | `providers/ieee_spectrum.py`; annual rank/score, multi-profile support  |
| 04.0 | JetBrains Developer Ecosystem Provider          | provider        | `providers/jetbrains.py`; annual usage-survey metric                    |
| 05.0 | Cross-Rating Normalization & Comparison         | analysis        | `rank_percentile` normalization; `langrank plot compare`                |
| 06.0 | Composite Index                                 | analysis        | `langrank composite`; explicit sources/weights/normalization, no hidden averaging |
| 07.0 | Snapshot Comparison                             | cli             | `langrank snapshot {year\|latest}`; nearest-observation selection rules  |
| 08.0 | Methodology Break Tracking                      | data-model      | `rating_methodologies` table; plot annotation hooks                    |
| 09.0 | Source Freshness Monitoring & Scheduled Updates | ops             | `langrank status --json` freshness checks; `langrank update`           |
| 10.0 | Dataset Release Workflow                        | release         | `langrank release`; CSV/JSON/SQLite bundle + `metadata.json` + checksums |
| 11.0 | Database Inspection Views                       | storage         | `latest_observations`, `language_history`, `rating_coverage`, etc. SQL views |
| 12.0 | Improved Plotting Options                       | cli             | `--start/--end/--smooth/--annotate-methodology/--log-y/--facet`         |
| 13.0 | Multi-Chart Report Generation                   | cli             | `langrank report`; per-rating plots + coverage + Markdown summary       |
| 14.0 | Alias Management Commands                       | cli             | `langrank languages aliases`, `languages resolve`, `alias add`          |
| 15.0 | Provider Capabilities Metadata                  | provider-infra  | Structured `capabilities()` on `RatingProvider`; generic CLI behavior   |
| 16.0 | External Provider Plugin Loading                | provider-infra  | `langrank.providers` entry-point discovery                             |
| 17.0 | Large-Source Performance Hardening              | performance     | Streaming downloads, chunked CSV parsing, batched/transactional writes |
| 18.0 | Data Quality Dashboard                          | data-quality    | `langrank quality`; anomaly report (missing periods, gaps, stale sources) |
| 19.0 | Source Archival Strategy                        | governance      | Configurable raw-artifact retention (`all/latest/yearly/none`)         |
| 20.0 | Historical Selection Semantics                  | cli             | Precise `--years N` / `--until` endpoint rules across services         |
| 21.0 | Language Births, Renames & Alias Validity Ranges| data-model      | `valid_from`/`valid_to` on aliases; no zero-fill pre-existence history |

Tasks 01.0-04.0 may proceed **in parallel** once the recommended provider order
(Stack Overflow tags → GitHub → IEEE Spectrum → JetBrains, see
[Task 01.0](#task-010---stack-overflow-tags-provider)) is agreed, since each is
independent work in `providers/` plus `normalization/languages.py` aliases.
Tasks 05.0, 06.0, 09.0, 10.0, 13.0, 17.0, 18.0, 19.0 all assume at least the
provider set from 01.0-04.0 exists — see the [dependency graph](#dependency-graph).

---

## Shared contracts (authoritative)

These contracts are defined once here and apply to every task below. Changing
one means updating this section and every affected task.

### C1 - New provider IDs & metrics

| Provider ID           | Metrics                              | Granularity | Task |
|------------------------|---------------------------------------|-------------|------|
| `stackoverflow-tags`   | `questions`, `question_share`, `rank` | month       | 01.0 |
| `github`               | `rank`, `activity`, `share` (variants: `octoverse`, `innovation-graph`) | annual | 02.0 |
| `ieee-spectrum`        | `rank`, `score` (profiles: `default`, `jobs`, `trending`) | annual | 03.0 |
| `jetbrains`            | `used_last_12_months`, `primary_language`, `planned_adoption` | annual | 04.0 |

These IDs are registered in `providers/registry.py`'s `ProviderRegistry`
exactly like the five bootstrap providers; a provider ID is never reused for
an unrelated metric family.

### C2 - Derived-value labeling invariant

Every value produced by normalization, rank-percentile conversion, a
composite index, or any other computed transform **must** carry
`is_derived=True` and a `derivation_method` (per `models.py`'s `Observation`
provenance fields — see [CLAUDE.md](/CLAUDE.md)). No task in this milestone
may present a derived value as raw source data, and none may persist a
derived value to the database unless a task's spec explicitly says so (the
default is compute-on-read). Governs Tasks 05.0, 06.0, 08.0, 12.0, 21.0.

### C3 - No hidden averaging / no silent interpolation

Ranks and values are never fabricated or interpolated (established
project-wide in [CLAUDE.md](/CLAUDE.md)); this milestone extends that rule to
cross-rating combination: a composite or comparison feature must require
explicit sources, metric choice, normalization method, weights, and
missing-data handling rather than defaulting to a silent average. Visual
smoothing in plots must be opt-in and never mutate stored data. Governs Tasks
05.0, 06.0, 07.0, 12.0, 18.0.

### C4 - Legal / source-policy review gate

Before any provider task (01.0-04.0) or the plugin-loading task (16.0) enables
unattended, scheduled fetching for a new source, its task must document:
official API/download availability, robots policy where relevant, terms of
use, a reasonable request rate, and whether raw-artifact redistribution is
allowed. If redistribution is unclear, the provider ships normalized derived
data only, with provenance documented. This is a **closing gate** on each
provider task, not a separate task.

### C5 - Testing requirement

Every task in this milestone ships raw fixtures + golden normalized outputs +
parser contract tests where it adds a provider, migration tests where it
touches `db/migrations.py`, and CLI acceptance tests where it adds a command.
Live integration tests stay opt-in (`pytest -m "not integration"` must still
pass). Periodically re-verify the acceptance path: fresh DB → fetch/import
fixtures for all providers → validate → export → plot. `uv run ruff check .`,
`uv run ruff format --check .`, and `uv run mypy src` stay clean throughout
(the four CI checks in `CLAUDE.md`).

---

## Per-task specifications

### Task 01.0 - Stack Overflow Tags Provider

**Goal:** monthly tag-activity metrics as a `question_share`-preferring
alternative to the existing `stackoverflow-survey` provider (self-reported
usage vs. tag activity are different measures — never conflate them).

- Prefer an official/reproducible Stack Exchange data source.
- Retain absolute `questions` counts, but prefer `question_share` for
  long-term comparison since overall Stack Overflow activity changes over
  time. Define the denominator explicitly (recommended default: questions
  containing at least one tracked programming-language tag).
- A question may carry more than one language tag, so per-language shares may
  legitimately sum above 100% — document this explicitly rather than treating
  it as a bug.
- Maintain curated tag → canonical-language mappings in
  `normalization/languages.py` (e.g. `cpp → c++`, `golang → go`,
  `csharp → c#`), accounting for aliases and historical tag renames. Never
  double-count the same question for the same canonical language.

**Success criteria:** `langrank fetch stackoverflow-tags` produces
`question_share` observations that are traceable to a denominator definition
in the docs; contract tests cover multi-tag questions and tag rename aliases.

---

### Task 02.0 - GitHub Provider

**Goal:** code-hosting/development-activity signal, supporting two source
variants without conflating them with each other or with RedMonk's GitHub
component.

- Support `octoverse` and `innovation-graph` variants; metrics may include
  `rank`, `activity`, `share`.
- Prefer official machine-readable historical datasets; fall back to annual
  Octoverse rankings when machine-readable data isn't available. Store exact
  source-publication metadata for every observation.
- Do not derive numerical activity from chart pixel/geometry extraction by
  default. If experimental chart extraction is added later, gate it behind an
  explicit `--allow-chart-extraction` flag and mark resulting values
  derived/experimental (C2).
- GitHub's own metric is not interchangeable with RedMonk's GitHub-derived
  component — document the distinction in provider metadata.

**Success criteria:** both variants are independently selectable
(`--source octoverse|innovation-graph`); no chart-derived value reaches the DB
without the explicit flag and derived-value labeling.

---

### Task 03.0 - IEEE Spectrum Provider

**Goal:** annual composite-index ingestion with explicit multi-profile
support (IEEE publishes more than one ranking profile).

- Metrics where available: `rank`, `score`, at `annual` granularity.
- Discover historical annual editions; version parsers only when the source
  structure actually changes (don't pre-emptively version).
- Preserve distinct profiles (`default`, `jobs`, `trending`, …) as distinct
  metrics rather than merging them into one series, and never compare
  different profiles as one uninterrupted time series.

**Success criteria:** each profile round-trips through `fetch → parse →
normalize → validate` as its own metric; querying one profile never silently
mixes in another.

---

### Task 04.0 - JetBrains Developer Ecosystem Provider

**Goal:** additional survey-based usage metric, historical from 2017 onward
where available.

- Potential metrics: `used_last_12_months`, `primary_language`,
  `planned_adoption`. Start with the most consistently comparable usage
  metric across survey years.
- Never combine `primary_language` and `used_last_12_months` as if they were
  the same measure — they answer different survey questions.
- Preserve survey question wording/version as metadata alongside each
  observation, since question wording can change between years.

**Success criteria:** at least one metric has a validated multi-year history;
`primary_language` and `used_last_12_months` are stored and queryable as
distinct metrics, never merged.

---

### Task 05.0 - Cross-Rating Normalization & Comparison

**Goal:** make cross-provider comparison possible without ever plotting raw
values from different ratings on one shared axis (an existing project-wide
rule — see [CLAUDE.md](/CLAUDE.md)).

- Only implement after individual provider histories (Tasks 01.0-04.0, plus
  the existing bootstrap providers) are reliable.
- New CLI surface: `langrank plot compare --language python --ratings
  tiobe,pypl,redmonk --years 10`.
- Cross-rating comparison must require or default to explicit normalization.
  First method: `rank_percentile` — for rank `r` among `n` ranked languages,
  `score = 1 - (r - 1) / max(n - 1, 1)`, producing ~1.0 = best, ~0.0 = worst.
  Later methods (`minmax`, `zscore`) are additive, not replacements.
- Every normalized series is visibly labeled as derived (C2); normalized
  values are not persisted unless a clear user requirement emerges later
  (compute-on-read by default).

**Success criteria:** `plot compare` refuses (or clearly labels) an
unnormalized cross-rating request; `rank_percentile` output is covered by
unit tests against known rank/n inputs.

---

### Task 06.0 - Composite Index

**Goal:** an opt-in, fully-explicit composite score — never a hidden average,
never presented as "the true popularity rating."

- New command: `langrank composite --ratings tiobe,pypl,redmonk,github,
  stackoverflow-survey --normalize rank-percentile --weights 1,1,1,2,2`.
- Required, non-defaulted inputs: included sources, metric choice,
  normalization method, weights, missing-data handling.
- Every result is labeled `derived composite` in output and docs.

**Success criteria:** omitting any required input (sources/metric/
normalization/weights/missing-data policy) is a CLI usage error, not a
silent default; output rows carry the `derived composite` label.

---

### Task 07.0 - Snapshot Comparison

**Goal:** a same-point-in-time cross-source table without silent
interpolation.

- Commands: `langrank snapshot 2020`, `langrank snapshot latest`. Example
  output shape: one row per language, one column per rating
  (TIOBE/PYPL/RedMonk/GitHub/SO Survey rank).
- Define selection rules for the closest observation when a source is
  monthly, snapshot-based, or annual, and show the actual source observation
  date wherever ambiguity matters. Do not interpolate missing cells.

**Success criteria:** a snapshot cell is always either a real observation
(with its true date shown) or explicitly blank — never a computed fill-in.

---

### Task 08.0 - Methodology Break Tracking

**Goal:** record when a historical index's methodology changed, so later
analysis doesn't silently span a break.

- New/extended table `rating_methodologies`: `rating_id`, `version`,
  `valid_from`, `valid_to`, `description`, `source_url`.
- Later plotting (Task 12.0) may mark methodology boundaries with vertical
  lines/annotations via `--annotate-methodology`.
- Do not statistically "correct" methodology breaks automatically — this task
  records the break; it never adjusts values across it.

**Success criteria:** a migration adds `rating_methodologies` with a new
integer version per `db/migrations.py` convention; `ValidationService` can
report which observations fall within a given methodology version.

---

### Task 09.0 - Source Freshness Monitoring & Scheduled Updates

**Goal:** know whether new source data exists without a full re-download, and
optionally automate fetching only stale providers.

- Enhance `langrank status` (and `--json` output) to determine freshness per
  provider using cheap, provider-specific mechanisms: HTTP `Last-Modified`,
  `ETag`, archive-index discovery, latest-survey-year page, or release feed.
- New optional command `langrank update`: (1) check provider freshness,
  (2) fetch only stale providers, (3) validate new observations,
  (4) report methodology changes, (5) generate an update summary. Suitable
  for cron/GitHub Actions, but hosted scraping automation must not be the
  default where a source's terms discourage it (C4).

**Success criteria:** `langrank status --json` exposes a per-provider
freshness signal cheaply (no full fetch); `langrank update` is idempotent and
skips providers already fresh.

---

### Task 10.0 - Dataset Release Workflow

**Goal:** reproducible public dataset releases with full provenance metadata.

- New command: `langrank release --since 2016 --output dist/`, generating
  `langrank-history.csv`, `langrank-history.json`, `langrank.sqlite`,
  `metadata.json`, `checksums.txt`.
- `metadata.json` must contain: app version, schema version, generated
  timestamp, source coverage, parser versions, source acquisition modes,
  known warnings, methodology changes (Task 08.0).

**Success criteria:** a release bundle's `metadata.json` alone is sufficient
to explain how every value in the bundle was produced (source, parser
version, acquisition mode) without inspecting the DB.

---

### Task 11.0 - Database Inspection Views

**Goal:** keep the DB inspectable with plain `sqlite3`, not exclusively via
JSON metadata blobs.

- Useful SQL views: `latest_observations`, `latest_language_ranks`,
  `language_history`, `rating_coverage`, `provider_health`.
- Add as versioned entries in `db/migrations.py`, same convention as tables.

**Success criteria:** each view is queryable directly via `sqlite3
<db-path> "select * from view_name limit 5"` with no application code
running.

---

### Task 12.0 - Improved Plotting Options

**Goal:** incrementally extend `langrank plot`, but only as justified by
actual use (avoid speculative plotting complexity).

- Potential flags: `--start`, `--end`, `--smooth` (visual only),
  `--annotate-methodology` (consumes Task 08.0 data), `--legend-position`,
  `--log-y`, `--facet`.
- Rules that must remain true regardless of which flags land: missing values
  are never rendered as zero; stored data is never interpolated; visual
  smoothing/interpolation is opt-in only and never mutates stored data; the
  rank axis is inverted by default (rank 1 at the top); source observation
  dates stay truthful in tooltips/labels.

**Success criteria:** each new flag ships with a test asserting the
above-listed rules still hold with that flag active.

---

### Task 13.0 - Multi-Chart Report Generation

**Goal:** a single `report` command bundling plots, coverage, and a
Markdown summary — built only after provider completeness (depends on
Tasks 01.0-04.0), not before.

- Command: `langrank report --languages python,c++,rust --years 10 --output
  report/`, generating: plots per rating, a coverage table, latest ranks,
  methodological notes (Task 08.0), a CSV data subset, and a Markdown
  summary.

**Success criteria:** the report directory is self-contained (openable
without the CLI) and its Markdown summary references the same methodology
notes stored in Task 08.0's table.

---

### Task 14.0 - Alias Management Commands

**Goal:** make the existing alias system (`normalization/languages.py`,
`Database.alias_to_language`) inspectable and resolvable from the CLI, ahead
of any user-defined-mapping feature.

- New commands: `langrank languages aliases`, `langrank languages aliases
  --rating pypl`, `langrank languages resolve cpp`.
- A future `langrank languages alias add ...` admin/import mechanism must be
  approached cautiously — user-defined mappings could change historical
  semantics. Keep source-defined aliases (used for parsing) and any future
  user lookup aliases clearly distinguishable in the schema and the CLI
  output.

**Success criteria:** `languages resolve <alias>` reproduces exactly what
`Database.alias_to_language`/`_normalize_alias` already do internally — the
command is a read-only window onto existing normalization, not a new
resolution path.

---

### Task 15.0 - Provider Capabilities Metadata

**Goal:** let generic CLI behavior (status, fetch, capability-gated flags)
work from provider-declared capabilities instead of provider-specific
special-casing.

- Structured capabilities per provider: `supports_historical`,
  `supports_incremental`, `supports_manual_import`, `supports_status_check`,
  `supports_raw_cache`, `supports_rank`, `supports_value`,
  `native_granularity`.
- This is groundwork for Task 16.0 (external plugins), not a heavyweight
  plugin framework by itself — don't over-build it ahead of an actual
  external-provider need.

**Success criteria:** at least one generic CLI code path (e.g. `status`)
reads capabilities off the `RatingProvider` instance rather than an
`if provider_id == ...` branch.

---

### Task 16.0 - External Provider Plugin Loading

**Goal:** allow third-party providers to register via a Python entry point,
once the built-in provider architecture (contracts, error semantics,
metadata — Task 15.0) is mature enough to expose safely.

- Candidate entry-point group: `langrank.providers`.
- Do not prematurely stabilize a third-party-facing API. Stabilize first, in
  this order: domain objects (`models.py`), the fetch/parse/normalize
  contracts (`providers/base.py`), error semantics (`errors.py`), and
  provider metadata (Task 15.0).
- Subject to the legal/source-policy gate (C4) for any plugin that ships with
  default network access.

**Success criteria:** an out-of-tree package can register a
`RatingProvider` via the entry point and appear in `ProviderRegistry` without
any change to `langrank` core.

---

### Task 17.0 - Large-Source Performance Hardening

**Goal:** keep large historical sources tractable without reaching for
infrastructure this project doesn't need.

- Stream downloads where practical; process CSVs in chunks; avoid
  unnecessary pandas copies; batch SQLite writes inside transactions; cache
  intermediate downloads (reuses the existing `RawArtifact`/sha256 caching in
  `providers/common.py`).
- Do not introduce Spark, DuckDB, or distributed systems unless actual
  workloads justify them. DuckDB may later help analytical exports, but
  SQLite stays canonical unless requirements change.

**Success criteria:** a benchmark fixture exercising the largest known source
size completes within a documented time/memory budget, using only the
techniques above.

---

### Task 18.0 - Data Quality Dashboard

**Goal:** surface data-quality anomalies without ever silently modifying
data (C3).

- New command: `langrank quality`. Possible checks: missing periods,
  duplicate ranks, abrupt discontinuities, source gaps, unmapped aliases,
  latest-source mismatch, methodology-boundary crossings (Task 08.0),
  suspicious percentages, stale providers (Task 09.0).

**Success criteria:** every check in the report is a flag with a pointer to
the affected rows — the command never edits or deletes data itself.

---

### Task 19.0 - Source Archival Strategy

**Goal:** balance reproducibility against disk usage and licensing risk for
retained raw artifacts.

- Configurable retention policy: `all`, `latest`, `yearly`, `none`. For huge
  survey ZIPs, retaining one official artifact per year is a reasonable
  default.
- Never commit large copyrighted/raw datasets into the Git repository without
  clear permission (ties into C4).

**Success criteria:** the retention policy is configurable per provider (or
globally with a per-provider override) and defaults to something disk-safe
out of the box.

---

### Task 20.0 - Historical Selection Semantics

**Goal:** define precise, documented behavior for `--years N` so it doesn't
surprise-truncate when a source hasn't published in the current calendar
year.

- Recommended semantics: use the latest available observation date for the
  selected rating/metric as the endpoint, then include observations newer
  than endpoint minus N years.
- For multi-rating commands, explicitly define whether the endpoint is
  latest-per-source, a single global-latest, or an explicit `--until` value —
  and document the choice in the command's `--help` text.

**Success criteria:** `QueryService`/`export`/`plot` all resolve `--years N`
identically per the documented rule; a regression test pins the endpoint
behavior for a source with a stale current year.

---

### Task 21.0 - Language Births, Renames & Alias Validity Ranges

**Goal:** handle languages that don't exist for the entire selected range,
and source category names that change over time, without fabricating
history.

- A language may not exist for the entire selected range — this is normal;
  never fill pre-existence history with zero (ties into C3).
- Source category names can change; add `valid_from`/`valid_to` to alias
  records where needed, while preserving the original source label for
  historical aliases (don't rewrite history to the current name).

**Success criteria:** a language added mid-range shows a real gap (no
observations) before its birth date, not a zero-value series; an alias
rename is queryable both under its old and new label for the periods each
was actually in effect.

---

## Dependency graph

```
Tasks 01.0-04.0 (new providers)              ← foundation, parallelizable
   │
   ├──► Task 05.0 (Cross-rating normalization)
   │        └──► Task 06.0 (Composite index)
   │
   ├──► Task 07.0 (Snapshot comparison)
   ├──► Task 09.0 (Freshness monitoring / scheduled updates)
   ├──► Task 13.0 (Multi-chart report)            ← also needs Task 12.0
   ├──► Task 17.0 (Large-source performance)      ← real workloads to size against
   └──► Task 19.0 (Archival strategy)              ← real raw artifacts to retain

Task 08.0 (Methodology break tracking)  ─────┬──► Task 10.0 (Dataset release)
                                              ├──► Task 12.0 (--annotate-methodology)
                                              └──► Task 18.0 (Quality dashboard)

Task 14.0 (Alias management CLI) ────────────► Task 21.0 (Births/renames/alias validity)

Task 11.0 (DB inspection views)     — independent, storage-layer only
Task 15.0 (Capabilities metadata)   ─────────► Task 16.0 (External plugins)
Task 20.0 (Selection semantics)     — independent, query/export/plot layer
```

**Minimum viable increment:** any one of Tasks 01.0-04.0 landed end-to-end
(fetch → parse → normalize → validate → query → export → plot), matching how
`providers/demo.py` proved the pre-milestone architecture.
**Full milestone:** all 21 tasks, with the provenance invariant (below) intact
throughout.

---

## Milestone exit criteria

There is no fixed target provider count for this milestone to be "complete."
The mature application should support at least
`tiobe, pypl, redmonk, github, stackoverflow-survey, stackoverflow-tags,
ieee-spectrum, jetbrains` under `langrank fetch all --years 10` and
`langrank validate --strict`, with plots such as:

```bash
langrank plot --rating tiobe --languages python,c,c++,java,rust --years 10
langrank plot --rating stackoverflow-tags --metric question_share \
    --languages python,javascript,c++,rust --years 10
langrank plot --rating redmonk --metric rank \
    --languages python,c++,java,rust --years 10
```

The invariant that actually gates completion is that **every value remains
traceable** to a source, a date, a metric definition, a parser version, an
acquisition mode, and a normalization rule (C2) — and that this trail
survives query, export, plotting, and every derived analysis this milestone
adds (Tasks 05.0, 06.0, 07.0, 10.0, 18.0). A task that adds a feature at the
cost of that trail is not done, regardless of how much of the Tasks table it
checks off.

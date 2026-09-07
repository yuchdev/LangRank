# Milestone 0001 - New Rating Providers

**Package:** `langrank` | **Module root:** `src/langrank/providers/`
**Depends on:** the already-merged core architecture — the `RatingProvider`
protocol (`providers/base.py`), the five bootstrap providers (`demo`, `tiobe`,
`pypl`, `redmonk`, `stackoverflow-survey`), `Database`/migrations (`db/`), and
the `FetchService`/`ValidationService` layer (`services/`). See
[CLAUDE.md](/CLAUDE.md) for the pipeline and invariants those pieces already
establish.

This milestone adds four new rating providers, each exercising the same
`fetch → parse → normalize → validate` contract as the bootstrap providers.
It is the **foundation** every other new milestone in this roadmap builds on:
[Milestone 0002](/docs/roadmap/0002-cross-rating-analysis/plan.md) (cross-rating
comparison), [Milestone 0004](/docs/roadmap/0004-freshness-and-releases/plan.md)
(dataset releases), and [Milestone 0005](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md)
(multi-chart reports) all assume more than the five bootstrap provider
histories exist to be meaningful.

## Table of contents

- [Tasks](#tasks)
- [Shared conventions](#shared-conventions)
- [Per-task specifications](#per-task-specifications)
- [Milestone exit criteria](#milestone-exit-criteria)

---

## Tasks

| Task | Name                                    | Category | Output                                                                |
|------|-------------------------------------------|----------|--------------------------------------------------------------------|
| 01.0 | Stack Overflow Tags Provider               | provider | `providers/stackoverflow_tags.py`; monthly tag-activity + share metric |
| 02.0 | GitHub Provider                            | provider | `providers/github.py`; Octoverse/Innovation-Graph rank & activity    |
| 03.0 | IEEE Spectrum Provider                     | provider | `providers/ieee_spectrum.py`; annual rank/score, multi-profile support |
| 04.0 | JetBrains Developer Ecosystem Provider     | provider | `providers/jetbrains.py`; annual usage-survey metric                 |

Recommended order: Stack Overflow tags → GitHub → IEEE Spectrum → JetBrains —
this progressively introduces monthly activity-derived metrics, then
code-hosting/development activity, then composite-index ingestion, then
additional survey-based usage. The order is a recommendation, not a hard
dependency: each task is independent implementation work in `providers/` plus
`normalization/languages.py` aliases, and all four **may proceed in
parallel**.

---

## Shared conventions

### Provider IDs & metrics

| Provider ID           | Metrics                              | Granularity | Task |
|-------------------------|---------------------------------------|-------------|------|
| `stackoverflow-tags`    | `questions`, `question_share`, `rank` | month       | 01.0 |
| `github`                | `rank`, `activity`, `share` (variants: `octoverse`, `innovation-graph`) | annual | 02.0 |
| `ieee-spectrum`         | `rank`, `score` (profiles: `default`, `jobs`, `trending`) | annual | 03.0 |
| `jetbrains`             | `used_last_12_months`, `primary_language`, `planned_adoption` | annual | 04.0 |

Each ID is registered in `providers/registry.py`'s `ProviderRegistry` exactly
like the five bootstrap providers; a provider ID is never reused for an
unrelated metric family.

### Legal / source-policy review gate

Before any task in this milestone enables unattended, scheduled fetching for
its source, it must document: official API/download availability, robots
policy where relevant, terms of use, a reasonable request rate, and whether
raw-artifact redistribution is allowed. If redistribution is unclear, the
provider ships normalized derived data only, with provenance documented. This
is a **closing gate** on each task below, not a separate task — it also
applies to [Milestone 0006's external-plugin
task](/docs/roadmap/0006-provider-extensibility/plan.md#task-020---external-provider-plugin-loading)
for any plugin that ships with default network access.

### Testing

Every task ships raw fixtures + golden normalized outputs + parser contract
tests (`tests/contract/`), per [CLAUDE.md](/CLAUDE.md). Live integration
tests stay opt-in (`pytest -m "not integration"` must still pass). `uv run
ruff check .`, `uv run ruff format --check .`, and `uv run mypy src` stay
clean throughout.

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
  derived/experimental.
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

## Milestone exit criteria

`langrank fetch all --years 10` and `langrank validate --strict` succeed with
all four new providers registered alongside the five bootstrap providers,
with plots such as:

```bash
langrank plot --rating stackoverflow-tags --metric question_share \
    --languages python,javascript,c++,rust --years 10
```

Every value stays traceable to a source, a date, a metric definition, a
parser version, an acquisition mode, and a normalization rule (the project's
core invariant — see [CLAUDE.md](/CLAUDE.md)). A task that adds a provider at
the cost of that trail is not done.

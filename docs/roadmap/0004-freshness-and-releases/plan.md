# Milestone 0004 - Freshness & Releases

**Package:** `langrank` | **Module root:** `src/langrank/services/`, `src/langrank/cli.py`
**Depends on:** `FetchService`/`StatusService` (`services/`) for freshness
checks and scheduled fetching; benefits from (but does not strictly require)
[Milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md)'s
additional providers and
[Milestone 0003](/docs/roadmap/0003-historical-data-quality/plan.md)'s
methodology metadata for richer release manifests.

This milestone covers the operational lifecycle around already-ingested
data: knowing when a source has new data without a full re-fetch,
automating fetch-only-what's-stale, and packaging a reproducible dataset
release with full provenance metadata. It does not add any new rating
provider or analysis feature — it operationalizes what the existing pipeline
already produces.

## Table of contents

- [Tasks](#tasks)
- [Shared conventions](#shared-conventions)
- [Per-task specifications](#per-task-specifications)
- [Milestone exit criteria](#milestone-exit-criteria)

---

## Tasks

| Task | Name                                              | Category | Output                                                                  |
|------|------------------------------------------------------|----------|----------------------------------------------------------------------------|
| 01.0 | Source Freshness Monitoring & Scheduled Updates       | ops      | `langrank status --json` freshness checks; `langrank update`             |
| 02.0 | Dataset Release Workflow                              | release  | `langrank release`; CSV/JSON/SQLite bundle + `metadata.json` + checksums |
| 03.0 | Source Archival Strategy                              | governance | Configurable raw-artifact retention (`all/latest/yearly/none`)         |

Task 02.0 (Dataset Release Workflow) benefits from Task 01.0's freshness data
and Task 03.0's archival policy (which artifacts are actually available to
bundle), but is independently buildable — a release can ship without
`langrank update` existing yet. Task 03.0 is independent of 01.0/02.0.

---

## Shared conventions

### Automation must respect source terms

Hosted scraping automation (Task 01.0's `langrank update`, run via cron or
CI) must not be the default where a source's terms discourage it — this
mirrors the legal/source-policy gate each provider task in
[Milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate)
already documents.

### Testing

Task 01.0 needs tests that a freshness check makes no full-download network
call; Task 02.0 needs a fixture-driven test asserting `metadata.json`
actually reflects the bundle's contents; Task 03.0 needs tests for each
retention policy value. `uv run ruff check .`, `uv run ruff format --check
.`, and `uv run mypy src` stay clean throughout.

---

## Per-task specifications

### Task 01.0 - Source Freshness Monitoring & Scheduled Updates

**Goal:** know whether new source data exists without a full re-download, and
optionally automate fetching only stale providers.

- Enhance `langrank status` (and `--json` output) to determine freshness per
  provider using cheap, provider-specific mechanisms: HTTP `Last-Modified`,
  `ETag`, archive-index discovery, latest-survey-year page, or release feed.
- New optional command `langrank update`: (1) check provider freshness,
  (2) fetch only stale providers, (3) validate new observations,
  (4) report methodology changes, (5) generate an update summary. Suitable
  for cron/GitHub Actions, but hosted scraping automation must not be the
  default where a source's terms discourage it.

**Success criteria:** `langrank status --json` exposes a per-provider
freshness signal cheaply (no full fetch); `langrank update` is idempotent and
skips providers already fresh.

---

### Task 02.0 - Dataset Release Workflow

**Goal:** reproducible public dataset releases with full provenance metadata.

- New command: `langrank release --since 2016 --output dist/`, generating
  `langrank-history.csv`, `langrank-history.json`, `langrank.sqlite`,
  `metadata.json`, `checksums.txt`.
- `metadata.json` must contain: app version, schema version, generated
  timestamp, source coverage, parser versions, source acquisition modes,
  known warnings, methodology changes (see
  [Milestone 0003 Task 01.0](/docs/roadmap/0003-historical-data-quality/plan.md#task-010---methodology-break-tracking)).

**Success criteria:** a release bundle's `metadata.json` alone is sufficient
to explain how every value in the bundle was produced (source, parser
version, acquisition mode) without inspecting the DB.

---

### Task 03.0 - Source Archival Strategy

**Goal:** balance reproducibility against disk usage and licensing risk for
retained raw artifacts.

- Configurable retention policy: `all`, `latest`, `yearly`, `none`. For huge
  survey ZIPs, retaining one official artifact per year is a reasonable
  default.
- Never commit large copyrighted/raw datasets into the Git repository without
  clear permission — ties into the legal/source-policy gate in
  [Milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate).

**Success criteria:** the retention policy is configurable per provider (or
globally with a per-provider override) and defaults to something disk-safe
out of the box.

---

## Milestone exit criteria

`langrank status --json` reports freshness for every registered provider
without a full fetch; `langrank update` and `langrank release` both run
end-to-end against a populated DB and produce output whose provenance
metadata is complete enough to audit independently of the database itself.

# Milestone 0006 - Provider Extensibility

**Package:** `langrank` | **Module root:** `src/langrank/providers/`
**Depends on:** the `RatingProvider` protocol (`providers/base.py`) and
`ProviderRegistry` (`providers/registry.py`). Independent of every other new
milestone in this roadmap — it hardens the provider *contract* itself rather
than adding a provider or a feature on top of it.

This milestone prepares the provider architecture for growth beyond
hand-registered, in-tree providers: structured capabilities so generic CLI
code stops special-casing provider IDs, an external-plugin loading mechanism
for third-party providers, and performance hardening for large historical
sources. It stabilizes contracts rather than adding provider-facing features.

## Table of contents

- [Tasks](#tasks)
- [Shared conventions](#shared-conventions)
- [Per-task specifications](#per-task-specifications)
- [Milestone exit criteria](#milestone-exit-criteria)

---

## Tasks

| Task | Name                                    | Category       | Output                                                                |
|------|--------------------------------------------|----------------|--------------------------------------------------------------------|
| 01.0 | Provider Capabilities Metadata               | provider-infra | Structured `capabilities()` on `RatingProvider`; generic CLI behavior |
| 02.0 | External Provider Plugin Loading             | provider-infra | `langrank.providers` entry-point discovery                          |
| 03.0 | Large-Source Performance Hardening           | performance    | Streaming downloads, chunked CSV parsing, batched/transactional writes |

Task 02.0 depends on Task 01.0 (a third-party provider needs the same
capabilities metadata a built-in one exposes, and the contracts it stabilizes
need to exist first). Task 03.0 is independent of 01.0/02.0.

---

## Shared conventions

### Stabilize contracts before exposing them externally

Do not prematurely stabilize a third-party-facing API. Stabilize first, in
this order: domain objects (`models.py`), the fetch/parse/normalize
contracts (`providers/base.py`), error semantics (`errors.py`), and provider
metadata (Task 01.0). Task 02.0 only proceeds once these are settled.

### Legal / source-policy review gate

Any plugin loaded via Task 02.0 that ships with default network access is
subject to the same legal/source-policy gate as every built-in provider — see
[Milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md#legal--source-policy-review-gate).

### No premature infrastructure

Do not turn Task 01.0's capabilities metadata into a heavyweight plugin
framework unless Task 02.0's external-provider need is genuine. Do not
introduce Spark, DuckDB, or distributed systems for Task 03.0 unless actual
workloads justify them — SQLite stays canonical unless requirements change.

### Testing

Task 01.0 needs a test that at least one generic CLI path reads capabilities
instead of branching on provider ID; Task 02.0 needs an out-of-tree fixture
package proving entry-point discovery; Task 03.0 needs a benchmark fixture
against the largest known source size. `uv run ruff check .`, `uv run ruff
format --check .`, and `uv run mypy src` stay clean throughout.

---

## Per-task specifications

### Task 01.0 - Provider Capabilities Metadata

**Goal:** let generic CLI behavior (status, fetch, capability-gated flags)
work from provider-declared capabilities instead of provider-specific
special-casing.

- Structured capabilities per provider: `supports_historical`,
  `supports_incremental`, `supports_manual_import`, `supports_status_check`,
  `supports_raw_cache`, `supports_rank`, `supports_value`,
  `native_granularity`.
- This is groundwork for Task 02.0, not a heavyweight plugin framework by
  itself — don't over-build it ahead of an actual external-provider need.

**Success criteria:** at least one generic CLI code path (e.g. `status`)
reads capabilities off the `RatingProvider` instance rather than an
`if provider_id == ...` branch.

---

### Task 02.0 - External Provider Plugin Loading

**Goal:** allow third-party providers to register via a Python entry point,
once the built-in provider architecture (contracts, error semantics,
metadata — Task 01.0) is mature enough to expose safely.

- Candidate entry-point group: `langrank.providers`.
- Do not prematurely stabilize a third-party-facing API — see
  [Shared conventions § Stabilize contracts before exposing them
  externally](#stabilize-contracts-before-exposing-them-externally).
- Subject to the legal/source-policy gate for any plugin that ships with
  default network access.

**Success criteria:** an out-of-tree package can register a
`RatingProvider` via the entry point and appear in `ProviderRegistry` without
any change to `langrank` core.

---

### Task 03.0 - Large-Source Performance Hardening

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

## Milestone exit criteria

A generic CLI code path resolves provider behavior from `capabilities()`
rather than special-cased provider IDs; an out-of-tree fixture package
registers successfully via the `langrank.providers` entry point with no core
code change; and the largest known source's fixture-scale benchmark completes
within its documented budget using only streaming/chunking/batching, without
adding a new runtime dependency beyond what's already in `pyproject.toml`.

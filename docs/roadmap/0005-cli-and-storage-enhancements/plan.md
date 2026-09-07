# Milestone 0005 - CLI & Storage Enhancements

**Package:** `langrank` | **Module root:** `src/langrank/cli.py`, `src/langrank/db/`
**Depends on:** the existing `QueryService`/`export`/`plot` CLI surface.
Task 03.0 (Multi-Chart Report Generation) additionally depends on provider
completeness from [Milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md) —
see that task's spec.

This milestone extends the existing CLI and storage surface incrementally:
better plots, a bundled report command, read-only alias inspection, SQL views
for direct DB inspection, and precise semantics for `--years`/`--until`. None
of these tasks add a new provider or a new analysis method — they make the
existing pipeline easier to use and inspect.

## Table of contents

- [Tasks](#tasks)
- [Shared conventions](#shared-conventions)
- [Per-task specifications](#per-task-specifications)
- [Milestone exit criteria](#milestone-exit-criteria)

---

## Tasks

| Task | Name                                     | Category | Output                                                                |
|------|---------------------------------------------|----------|--------------------------------------------------------------------|
| 01.0 | Database Inspection Views                    | storage  | `latest_observations`, `language_history`, `rating_coverage`, etc. SQL views |
| 02.0 | Improved Plotting Options                    | cli      | `--start/--end/--smooth/--annotate-methodology/--log-y/--facet`     |
| 03.0 | Multi-Chart Report Generation                | cli      | `langrank report`; per-rating plots + coverage + Markdown summary   |
| 04.0 | Alias Management Commands                    | cli      | `langrank languages aliases`, `languages resolve`, `alias add`      |
| 05.0 | Historical Selection Semantics               | cli      | Precise `--years N` / `--until` endpoint rules across services      |

These five tasks are independent of each other and may proceed in any order,
with one exception: Task 03.0 depends on Task 02.0 landing first (the report
command reuses the plotting flags) and on provider completeness (see
Task 03.0's spec below).

---

## Shared conventions

### Plotting invariants

Regardless of which flags Task 02.0 adds, these rules must remain true:
missing values are never rendered as zero; stored data is never
interpolated; visual smoothing/interpolation is opt-in only and never
mutates stored data; the rank axis is inverted by default (rank 1 at the
top); source observation dates stay truthful in tooltips/labels. Avoid adding
plotting complexity until justified by actual use.

### Read-only alias inspection

Task 04.0's alias commands are a read-only window onto the *existing*
`normalization/languages.py` / `Database.alias_to_language` normalization —
they do not introduce a new resolution path. A future user-defined-mapping
admin command must be approached cautiously, since it could change
historical semantics; source-defined aliases (used for parsing) and any
future user lookup aliases must stay clearly distinguishable.

### Testing

Task 01.0's views need a smoke test that plain `sqlite3` can query them; Task
02.0/05.0 need a regression test per flag/rule; Task 03.0 needs a
fixture-driven acceptance test of the report directory; Task 04.0 needs
parity tests against `Database.alias_to_language`. `uv run ruff check .`, `uv
run ruff format --check .`, and `uv run mypy src` stay clean throughout.

---

## Per-task specifications

### Task 01.0 - Database Inspection Views

**Goal:** keep the DB inspectable with plain `sqlite3`, not exclusively via
JSON metadata blobs.

- Useful SQL views: `latest_observations`, `latest_language_ranks`,
  `language_history`, `rating_coverage`, `provider_health`.
- Add as versioned entries in `db/migrations.py`, same convention as tables.

**Success criteria:** each view is queryable directly via `sqlite3
<db-path> "select * from view_name limit 5"` with no application code
running.

---

### Task 02.0 - Improved Plotting Options

**Goal:** incrementally extend `langrank plot`, but only as justified by
actual use (avoid speculative plotting complexity).

- Potential flags: `--start`, `--end`, `--smooth` (visual only),
  `--annotate-methodology` (consumes
  [Milestone 0003 Task 01.0](/docs/roadmap/0003-historical-data-quality/plan.md#task-010---methodology-break-tracking)),
  `--legend-position`, `--log-y`, `--facet`.
- Rules that must remain true regardless of which flags land: see
  [Shared conventions § Plotting invariants](#plotting-invariants).

**Success criteria:** each new flag ships with a test asserting the
plotting invariants still hold with that flag active.

---

### Task 03.0 - Multi-Chart Report Generation

**Goal:** a single `report` command bundling plots, coverage, and a
Markdown summary — built only after provider completeness (depends on
[Milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md)), not
before.

- Command: `langrank report --languages python,c++,rust --years 10 --output
  report/`, generating: plots per rating, a coverage table, latest ranks,
  methodological notes (see
  [Milestone 0003 Task 01.0](/docs/roadmap/0003-historical-data-quality/plan.md#task-010---methodology-break-tracking)),
  a CSV data subset, and a Markdown summary.

**Success criteria:** the report directory is self-contained (openable
without the CLI) and its Markdown summary references the same methodology
notes stored in Milestone 0003's table.

---

### Task 04.0 - Alias Management Commands

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

### Task 05.0 - Historical Selection Semantics

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

## Milestone exit criteria

`langrank quality`-adjacent inspection needs (Task 01.0's views), the
plotting surface (Task 02.0), the bundled report (Task 03.0), alias
inspection (Task 04.0), and `--years`/`--until` semantics (Task 05.0) are all
documented in `--help` text and covered by regression tests pinning the
invariants each task's spec lists — no task in this milestone trades away
the project's missing-data-stays-missing / no-silent-interpolation rule (see
[CLAUDE.md](/CLAUDE.md)) for convenience.

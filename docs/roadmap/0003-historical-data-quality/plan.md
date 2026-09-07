# Milestone 0003 - Historical Data Quality

**Package:** `langrank` | **Module root:** `src/langrank/db/`, `src/langrank/services/`
**Depends on:** `Database`/migrations (`db/migrations.py`) and
`ValidationService` (`services/validation.py`). Independent of
[Milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md) for its
schema work, though its quality checks become more useful as more providers
exist.

This milestone records the historical facts that keep provenance honest once
a rating series spans years: when a source's methodology changed, when a
language didn't exist yet, when a source's category name was renamed — and
surfaces anomalies without ever silently correcting them. It extends the
project's core invariant (see [CLAUDE.md](/CLAUDE.md)): don't fabricate or
interpolate; make what's actually known explicit instead.

## Table of contents

- [Tasks](#tasks)
- [Shared conventions](#shared-conventions)
- [Per-task specifications](#per-task-specifications)
- [Milestone exit criteria](#milestone-exit-criteria)

---

## Tasks

| Task | Name                                              | Category    | Output                                                         |
|------|------------------------------------------------------|-------------|-------------------------------------------------------------------|
| 01.0 | Methodology Break Tracking                            | data-model  | `rating_methodologies` table; plot annotation hooks             |
| 02.0 | Language Births, Renames & Alias Validity Ranges      | data-model  | `valid_from`/`valid_to` on aliases; no zero-fill pre-existence history |
| 03.0 | Data Quality Dashboard                                | data-quality| `langrank quality`; anomaly report (missing periods, gaps, stale sources) |

Task 03.0 (the quality dashboard) consumes Task 01.0's methodology-boundary
data and checks for unmapped aliases from Task 02.0's alias-validity model, so
it should land last. Tasks 01.0 and 02.0 are independent of each other and can
proceed in parallel.

---

## Shared conventions

### No silent correction

Do not statistically "correct" a methodology break automatically — Task 01.0
records the break; it never adjusts values across it. Do not fill
pre-existence history with zero when a language doesn't exist for the entire
selected range (Task 02.0) — this is normal, not missing data. The quality
dashboard (Task 03.0) only flags anomalies; it never edits or deletes data
itself.

### Testing

Task 01.0 and 02.0 both add migrations to `db/migrations.py` and need
migration tests (append-only version, per [CLAUDE.md](/CLAUDE.md)). Task 03.0
needs fixture data with deliberately-seeded anomalies (a gap, a duplicate
rank, an unmapped alias) to assert each check fires. `uv run ruff check .`,
`uv run ruff format --check .`, and `uv run mypy src` stay clean throughout.

---

## Per-task specifications

### Task 01.0 - Methodology Break Tracking

**Goal:** record when a historical index's methodology changed, so later
analysis doesn't silently span a break.

- New/extended table `rating_methodologies`: `rating_id`, `version`,
  `valid_from`, `valid_to`, `description`, `source_url`.
- Later plotting (see
  [Milestone 0005 Task 02.0](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#task-020---improved-plotting-options))
  may mark methodology boundaries with vertical lines/annotations via
  `--annotate-methodology`.
- Do not statistically "correct" methodology breaks automatically — this task
  records the break; it never adjusts values across it.

**Success criteria:** a migration adds `rating_methodologies` with a new
integer version per `db/migrations.py` convention; `ValidationService` can
report which observations fall within a given methodology version.

---

### Task 02.0 - Language Births, Renames & Alias Validity Ranges

**Goal:** handle languages that don't exist for the entire selected range,
and source category names that change over time, without fabricating
history.

- A language may not exist for the entire selected range — this is normal;
  never fill pre-existence history with zero.
- Source category names can change; add `valid_from`/`valid_to` to alias
  records where needed, while preserving the original source label for
  historical aliases (don't rewrite history to the current name).

**Success criteria:** a language added mid-range shows a real gap (no
observations) before its birth date, not a zero-value series; an alias
rename is queryable both under its old and new label for the periods each
was actually in effect.

---

### Task 03.0 - Data Quality Dashboard

**Goal:** surface data-quality anomalies without ever silently modifying
data.

- New command: `langrank quality`. Possible checks: missing periods,
  duplicate ranks, abrupt discontinuities, source gaps, unmapped aliases,
  latest-source mismatch, methodology-boundary crossings (Task 01.0),
  suspicious percentages, stale providers (see
  [Milestone 0004 Task 01.0](/docs/roadmap/0004-freshness-and-releases/plan.md#task-010---source-freshness-monitoring--scheduled-updates)).

**Success criteria:** every check in the report is a flag with a pointer to
the affected rows — the command never edits or deletes data itself.

---

## Milestone exit criteria

`langrank quality` reports every seeded anomaly class in a test fixture
without modifying the underlying data; `rating_methodologies` and alias
validity ranges are populated for at least one rating with a known
methodology change or renamed category, and both are queryable via
`ValidationService`.

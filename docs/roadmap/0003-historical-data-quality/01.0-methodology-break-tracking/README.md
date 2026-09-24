# Task 01.0 - Methodology Break Tracking

**Milestone:** [0003 - Historical Data Quality](/docs/roadmap/0003-historical-data-quality/plan.md) ·
**Spec source:** [plan.md § Task 01.0](/docs/roadmap/0003-historical-data-quality/plan.md#task-010---methodology-break-tracking) ·
**Category:** data-model · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                                   | Role          | Depends on | Status         |
|----|-------------------------------------------------------------------------------------------------------------------------------------------|---------------|------------|----------------|
| 01 | [ADR: `methodology_notes` is the canonical break table](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/01-adr-methodology-notes-canonical.md) | Architect     | -          | ⬜ Not started |
| 02 | [Break-kind schema migration & model fields](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/02-break-kind-migration.md)                   | Python Expert | 01         | ⬜ Not started |
| 03 | [Methodology-note sync semantics in `upsert_provider_metadata`](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/03-methodology-note-sync.md)  | Python Expert | 02         | ⬜ Not started |
| 04 | [Observation ↔ methodology segment queries & validation](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/04-methodology-segment-queries.md)  | Python Expert | 03         | ⬜ Not started |
| 05 | [Record verified breaks for bootstrap providers](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/05-record-verified-breaks.md)             | Python Expert | 02         | ⬜ Not started |
| 06 | [CLI surfacing & plot-annotation hook](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/06-cli-and-plot-hook.md)                            | Python Expert | 04         | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

Make every known methodology change of a rating an explicit, dated, queryable fact, so that
analysis, plots ([Milestone 0005 Task 02.0](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#task-020---improved-plotting-options))
and the quality dashboard ([Task 03.0](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/README.md))
can tell when a series spans a break. Values are never adjusted across a break.

## Baseline (what already exists)

- `src/langrank/db/migrations.py` migration **2** already creates `methodology_notes`
  (`rating_id`, `methodology_version`, `valid_from`, `valid_to`, `description`, `source_url`,
  `UNIQUE(rating_id, methodology_version, valid_from, valid_to)`). Open-ended bounds are
  stored as `''`, not `NULL`.
- `src/langrank/models.py:MethodologyNote` mirrors that row; `ProviderMetadata.methodology_notes`
  carries a list of them.
- `src/langrank/db/repository.py:Database.upsert_provider_metadata` inserts notes with
  `ON CONFLICT(...) DO UPDATE` on the four-column key; `Database.list_methodology_notes(rating_id)`
  reads them back.
- Every bootstrap provider emits exactly one placeholder note (e.g. `tiobe` → `2026-v1`,
  valid from 2016-01-01, open-ended) that describes the import, not a real upstream methodology.
- Nothing reads notes outside of `list_methodology_notes`; `ratings show` does not display them.
- **Latent defect:** because `valid_from`/`valid_to` are part of the unique key, editing a
  note's `valid_to` in provider metadata inserts a *second* row instead of updating — see
  subtask 03.

## Design notes

- **No new `rating_methodologies` table.** The plan's proposed table duplicates
  `methodology_notes` column-for-column. This task extends the existing table through a new
  append-only migration and records that decision in an ADR (subtask 01). The plan's name is
  kept only as a historical alias in docs.
- **A "break" is a note boundary.** Each note is a segment `[valid_from, valid_to]`; a
  methodology break is the date where one segment ends and the next begins. `break_kind`
  describes *why* the segment starts (`initial`, `method_change`, `source_change`,
  `coverage_change`, `wording_change`).
- **Metric-scoped breaks.** A survey wording change may affect one metric only;
  `affects_metrics` (empty = all metrics of the rating) keeps annotations precise.
- **Record, never correct.** No code path in this task alters `observations.value/rank`.
- **Facts must be cited.** A break is only recorded with a `source_url` and a matching entry in
  the rating's `docs/source-notes/*.md` file; unverifiable breaks are not added.

### Open questions

- Should overlapping segments for the same metric be an ERROR or WARNING? *Default: ERROR
  (`methodology_overlap`) — overlap makes "which version applies" ambiguous.*
- Should an `announced_at` date (when the source announced the change) be stored separately
  from `valid_from`? *Default: yes, optional column, useful for release notes in
  [Milestone 0004 Task 02.0](/docs/roadmap/0004-freshness-and-releases/plan.md#task-020---dataset-release-workflow).*

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] A new migration extends `methodology_notes` with a new integer version per the
      append-only convention; no existing migration tuple is edited.
- [ ] `ValidationService` can report which observations fall within each methodology version
      of a rating (plan.md success criterion).
- [ ] At least one bootstrap rating carries a real, cited methodology break.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- [docs/data-model.md](/docs/data-model.md), [docs/source-notes/tiobe.md](/docs/source-notes/tiobe.md),
  [docs/source-notes/stackoverflow-survey.md](/docs/source-notes/stackoverflow-survey.md)
- [ADR template](/docs/adr/template.md)

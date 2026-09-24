# Milestone 0003 - Historical Data Quality - Status

Tracks progress against [plan.md](/docs/roadmap/0003-historical-data-quality/plan.md).
Updated as each task lands.

## Current status

| Task | Name                                              | Status         | Tests |
|------|------------------------------------------------------|----------------|-------|
| 01.0 | Methodology Break Tracking                            | ⬜ Not started | -     |
| 02.0 | Language Births, Renames & Alias Validity Ranges      | ⬜ Not started | -     |
| 03.0 | Data Quality Dashboard                                | ⬜ Not started | -     |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

**Current gate status:** No task started yet.

## Notes & decisions

- **This milestone was split out of the original `0001-generic-implementation`
  umbrella document** (see [docs/roadmap/README.md](/docs/roadmap/README.md)
  for the full set of sibling milestones).
- **Task 03.0 depends on Tasks 01.0 and 02.0** landing first (the quality
  dashboard checks methodology boundaries and unmapped aliases those tasks
  introduce). 01.0 and 02.0 are independent of each other.
- **Cross-milestone reference:** Task 03.0 also checks provider staleness,
  which is introduced by
  [Milestone 0004 Task 01.0](/docs/roadmap/0004-freshness-and-releases/plan.md#task-010---source-freshness-monitoring--scheduled-updates) —
  a soft dependency, not a hard block.

## Decomposition tree

Every task is decomposed into a folder with a `README.md` (`## Subtasks` table) and one
spec file per subtask, per [docs/roadmap/README.md](/docs/roadmap/README.md). All subtasks
are ⬜ Not started.

```
docs/roadmap/0003-historical-data-quality/
├── plan.md
├── status.md
├── 01.0-methodology-break-tracking/            (6 subtasks)
│   ├── README.md
│   ├── 01-adr-methodology-notes-canonical.md
│   ├── 02-break-kind-migration.md
│   ├── 03-methodology-note-sync.md
│   ├── 04-methodology-segment-queries.md
│   ├── 05-record-verified-breaks.md
│   └── 06-cli-and-plot-hook.md
├── 02.0-language-lifecycle-and-alias-validity/ (6 subtasks)
│   ├── README.md
│   ├── 01-adr-single-resolution-path.md
│   ├── 02-lifecycle-catalog-and-migration.md
│   ├── 03-date-aware-resolution.md
│   ├── 04-provider-adoption.md
│   ├── 05-no-zero-fill-guarantee.md
│   └── 06-docs.md
└── 03.0-data-quality-dashboard/                (7 subtasks)
    ├── README.md
    ├── 01-quality-framework.md
    ├── 02-seeded-anomaly-fixture.md
    ├── 03-structural-checks.md
    ├── 04-value-checks.md
    ├── 05-temporal-and-provenance-checks.md
    ├── 06-quality-cli.md
    └── 07-docs.md
```

Key reconciliations with the existing code (details in each task README's *Baseline*):

- Task 01.0 extends the existing `methodology_notes` table (migration 2) instead of adding
  `rating_methodologies`, and fixes a stale-duplicate-row defect in
  `Database.upsert_provider_metadata`.
- Task 02.0 unifies the two alias-resolution paths (`LanguageNormalizer.resolve` vs
  `Database.alias_to_language`) behind one pure rule function; the validity columns
  already exist in `language_aliases`.
- Task 03.0 uses an interim `Database.rank_metric_ids()` helper because rank checks keyed on
  `metric_id = 'rank'` only match `demo`; the proper fix belongs to
  [Milestone 0006 Task 01.0](/docs/roadmap/0006-provider-extensibility/plan.md#task-010---provider-capabilities-metadata).

## Per-task detail

_Empty until a task lands. Once a task starts, add a `### Task NN.0 - Name
(status, date)` subsection per task with a **Delivered** list and a
**Tests / gate** summary._

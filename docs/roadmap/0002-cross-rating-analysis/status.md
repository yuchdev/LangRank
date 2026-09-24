# Milestone 0002 - Cross-Rating Analysis - Status

Tracks progress against [plan.md](/docs/roadmap/0002-cross-rating-analysis/plan.md).
Updated as each task lands.

## Current status

| Task | Name                                     | Status         | Tests |
|------|---------------------------------------------|----------------|-------|
| 01.0 | Cross-Rating Normalization & Comparison      | ⬜ Not started | -     |
| 02.0 | Composite Index                              | ⬜ Not started | -     |
| 03.0 | Snapshot Comparison                          | ⬜ Not started | -     |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

**Current gate status:** No task started yet.

## Notes & decisions

- **This milestone was split out of the original `0001-generic-implementation`
  umbrella document** (see [docs/roadmap/README.md](/docs/roadmap/README.md)
  for the full set of sibling milestones).
- **Soft dependency, not a hard gate:** this milestone does not strictly
  require [Milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md)
  to finish first — the existing `tiobe`/`pypl`/`redmonk`/
  `stackoverflow-survey` histories already qualify as "more than one reliable
  provider history." It does benefit from 0001's additional providers once
  they land.
- **Task 02.0 (Composite Index) depends on Task 01.0** within this milestone
  (shares the same normalization methods).

## Decomposition tree

Each task is decomposed into a task folder with a `README.md` (`## Subtasks` table) and one spec
per subtask, per [docs/roadmap/README.md](/docs/roadmap/README.md). All subtasks are ⬜ Not started.

```
docs/roadmap/0002-cross-rating-analysis/
├── plan.md
├── status.md
├── 01.0-cross-rating-normalization/      (6 subtasks; 05 deferrable)
│   ├── README.md
│   ├── 01-analysis-data-access.md
│   ├── 02-rank-percentile.md
│   ├── 03-comparison-service.md
│   ├── 04-plot-compare-cli.md
│   ├── 05-minmax-zscore.md
│   └── 06-docs.md
├── 02.0-composite-index/                 (5 subtasks)
│   ├── README.md
│   ├── 01-composite-spec.md
│   ├── 02-composite-math.md
│   ├── 03-composite-service.md
│   ├── 04-composite-cli.md
│   └── 05-docs.md
└── 03.0-snapshot-comparison/             (4 subtasks)
    ├── README.md
    ├── 01-selection-rules.md
    ├── 02-snapshot-service.md
    ├── 03-snapshot-cli.md
    └── 04-docs.md
```

Cross-task subtask dependencies: `03.0/01 → 01.0/01`; `02.0/01 → 01.0/02`;
`02.0/03 → 01.0/03, 03.0/01`. Recommended order: 01.0/01-04 → 03.0/01-03 → 02.0/01-04 →
docs subtasks (01.0/06, 03.0/04, 02.0/05) → 01.0/05 (deferrable).

## Per-task detail

_Empty until a task lands. Once a task starts, add a `### Task NN.0 - Name
(status, date)` subsection per task with a **Delivered** list and a
**Tests / gate** summary._

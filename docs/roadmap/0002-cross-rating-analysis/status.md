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

## Per-task detail

_Empty until a task lands. Once a task starts, add a `### Task NN.0 - Name
(status, date)` subsection per task with a **Delivered** list and a
**Tests / gate** summary._

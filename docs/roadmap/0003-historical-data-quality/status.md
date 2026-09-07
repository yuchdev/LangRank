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

## Per-task detail

_Empty until a task lands. Once a task starts, add a `### Task NN.0 - Name
(status, date)` subsection per task with a **Delivered** list and a
**Tests / gate** summary._

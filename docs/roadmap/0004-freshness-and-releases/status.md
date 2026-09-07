# Milestone 0004 - Freshness & Releases - Status

Tracks progress against [plan.md](/docs/roadmap/0004-freshness-and-releases/plan.md).
Updated as each task lands.

## Current status

| Task | Name                                              | Status         | Tests |
|------|------------------------------------------------------|----------------|-------|
| 01.0 | Source Freshness Monitoring & Scheduled Updates       | ⬜ Not started | -     |
| 02.0 | Dataset Release Workflow                              | ⬜ Not started | -     |
| 03.0 | Source Archival Strategy                              | ⬜ Not started | -     |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

**Current gate status:** No task started yet.

## Notes & decisions

- **This milestone was split out of the original `0001-generic-implementation`
  umbrella document** (see [docs/roadmap/README.md](/docs/roadmap/README.md)
  for the full set of sibling milestones).
- **Task 02.0 (release) is independently buildable** — it does not hard-block
  on Task 01.0 (`langrank update`) existing, though a richer release benefits
  from freshness data once 01.0 lands.
- **Automation must respect source terms:** `langrank update`'s scheduled
  fetching must not default to on where a source's terms discourage
  automation — same gate as each provider task in
  [Milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md).

## Per-task detail

_Empty until a task lands. Once a task starts, add a `### Task NN.0 - Name
(status, date)` subsection per task with a **Delivered** list and a
**Tests / gate** summary._

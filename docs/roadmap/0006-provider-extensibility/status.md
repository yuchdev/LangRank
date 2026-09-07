# Milestone 0006 - Provider Extensibility - Status

Tracks progress against [plan.md](/docs/roadmap/0006-provider-extensibility/plan.md).
Updated as each task lands.

## Current status

| Task | Name                                    | Status         | Tests |
|------|--------------------------------------------|----------------|-------|
| 01.0 | Provider Capabilities Metadata               | ⬜ Not started | -     |
| 02.0 | External Provider Plugin Loading             | ⬜ Not started | -     |
| 03.0 | Large-Source Performance Hardening           | ⬜ Not started | -     |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

**Current gate status:** No task started yet.

## Notes & decisions

- **This milestone was split out of the original `0001-generic-implementation`
  umbrella document** (see [docs/roadmap/README.md](/docs/roadmap/README.md)
  for the full set of sibling milestones).
- **Task 02.0 depends on Task 01.0** — an external plugin needs the same
  capabilities metadata and stabilized contracts a built-in provider exposes.
  Task 03.0 is independent of both.
- **Don't over-build ahead of need:** Task 01.0 is groundwork, not a
  plugin framework in itself; Task 02.0 only proceeds once contracts are
  genuinely stable (see plan.md's stabilization order).

## Per-task detail

_Empty until a task lands. Once a task starts, add a `### Task NN.0 - Name
(status, date)` subsection per task with a **Delivered** list and a
**Tests / gate** summary._

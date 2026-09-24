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

## Decomposition tree

All three tasks are decomposed into subtask specs (20 subtasks total, all ⬜ Not started).

```
docs/roadmap/0004-freshness-and-releases/
├── plan.md
├── status.md
├── 01.0-source-freshness-and-updates/      (8 subtasks)
│   ├── README.md
│   ├── 01-freshness-model.md
│   ├── 02-conditional-http-probe.md
│   ├── 03-provider-freshness-probes.md
│   ├── 04-status-json.md
│   ├── 05-scheduled-fetch-policy.md
│   ├── 06-update-service.md
│   ├── 07-update-cli.md
│   └── 08-scheduled-update-docs.md
├── 02.0-dataset-release-workflow/          (6 subtasks)
│   ├── README.md
│   ├── 01-release-manifest-model.md
│   ├── 02-release-data-queries.md
│   ├── 03-bundle-writers.md
│   ├── 04-release-service.md
│   ├── 05-release-cli.md
│   └── 06-release-docs.md
└── 03.0-source-archival-strategy/          (6 subtasks)
    ├── README.md
    ├── 01-retention-policy-config.md
    ├── 02-raw-artifact-retention-schema.md
    ├── 03-retention-planner.md
    ├── 04-archival-service.md
    ├── 05-cache-cli-and-fetch-hook.md
    └── 06-retention-docs-and-repo-guard.md
```

Task READMEs: [01.0](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/README.md) ·
[02.0](/docs/roadmap/0004-freshness-and-releases/02.0-dataset-release-workflow/README.md) ·
[03.0](/docs/roadmap/0004-freshness-and-releases/03.0-source-archival-strategy/README.md).

## Per-task detail

_Empty until a task lands. Once a task starts, add a `### Task NN.0 - Name
(status, date)` subsection per task with a **Delivered** list and a
**Tests / gate** summary._

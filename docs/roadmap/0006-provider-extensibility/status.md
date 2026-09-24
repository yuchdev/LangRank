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

## Decomposition tree

18 subtasks across 3 tasks (all ⬜ Not started).

```
docs/roadmap/0006-provider-extensibility/
├── plan.md
├── status.md
├── 01.0-provider-capabilities-metadata/        (7 subtasks)
│   ├── README.md
│   ├── 01-metric-kind-metadata.md
│   ├── 02-metric-role-lookups.md                ← fixes bare-"rank" metric-ID bug
│   ├── 03-provider-capabilities-model.md
│   ├── 04-status-service-capabilities.md
│   ├── 05-ratings-show-capabilities.md
│   ├── 06-capabilities-contract-test.md
│   └── 07-derived-rank-provenance.md
├── 02.0-external-provider-plugins/             (6 subtasks)
│   ├── README.md
│   ├── 01-provider-api-stability-adr.md         ← Architect; gates all loader code
│   ├── 02-entry-point-discovery.md
│   ├── 03-conflicts-isolation-opt-out.md
│   ├── 04-fixture-plugin-package.md
│   ├── 05-plugin-trust-model.md                 ← Security Auditor
│   └── 06-plugin-author-guide.md
└── 03.0-large-source-performance/              (5 subtasks)
    ├── README.md
    ├── 01-benchmark-fixture-harness.md
    ├── 02-batched-upsert.md
    ├── 03-streaming-download.md
    ├── 04-chunked-csv-parsing.md
    └── 05-performance-budget.md
```

**Cross-milestone note:** 01.0/02 (metric-role lookups) fixes a latent bug that other
milestones depend on: `--top`, the `invalid_ranks` validation, and rank-axis inversion
currently match only the `demo` provider's bare `rank` metric ID. Consider scheduling it
early, independently of the rest of this milestone.

## Per-task detail

_Empty until a task lands. Once a task starts, add a `### Task NN.0 - Name
(status, date)` subsection per task with a **Delivered** list and a
**Tests / gate** summary._

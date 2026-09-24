# Milestone 0005 - CLI & Storage Enhancements - Status

Tracks progress against [plan.md](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md).
Updated as each task lands.

## Current status

| Task | Name                                     | Status         | Tests |
|------|---------------------------------------------|----------------|-------|
| 01.0 | Database Inspection Views                    | ⬜ Not started | -     |
| 02.0 | Improved Plotting Options                    | ⬜ Not started | -     |
| 03.0 | Multi-Chart Report Generation                | ⬜ Not started | -     |
| 04.0 | Alias Management Commands                    | ⬜ Not started | -     |
| 05.0 | Historical Selection Semantics               | ⬜ Not started | -     |
| 06.0 | Test Coverage Baseline                       | ⬜ Not started | -     |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

**Current gate status:** No task started yet.

## Notes & decisions

- **This milestone was split out of the original `0001-generic-implementation`
  umbrella document** (see [docs/roadmap/README.md](/docs/roadmap/README.md)
  for the full set of sibling milestones).
- **Task 03.0 depends on Task 02.0** (reuses its plotting flags) and on
  provider completeness from
  [Milestone 0001](/docs/roadmap/0001-new-rating-providers/plan.md) — do not
  build the report command before both are in place. Tasks 01.0, 04.0, and
  05.0 are independent of everything else in this milestone.

## Decomposition tree

Every task is decomposed into a `{TT.t}-{task-slug}/` folder with a `README.md` (`## Subtasks`
table) and `{NN}-{subtask-slug}.md` specs, per [docs/roadmap/README.md](/docs/roadmap/README.md).
All subtasks are ⬜ Not started. 34 subtasks total (28 across 01.0-05.0, plus 6 in 06.0 Test Coverage Baseline, added 2026-09-25).

```
docs/roadmap/0005-cli-and-storage-enhancements/
├── plan.md
├── status.md
├── 01.0-database-inspection-views/          (5 subtasks)
│   ├── README.md
│   ├── 01-latest-language-ranks-view.md
│   ├── 02-provider-health-view.md
│   ├── 03-language-history-provenance.md
│   ├── 04-view-smoke-tests.md
│   └── 05-view-documentation.md
├── 02.0-improved-plotting-options/          (7 subtasks)
│   ├── README.md
│   ├── 01-plotting-invariant-harness.md
│   ├── 02-rank-metric-resolution-fix.md
│   ├── 03-gap-aware-segments.md
│   ├── 04-annotate-methodology.md
│   ├── 05-log-y-and-legend-position.md
│   ├── 06-visual-smoothing.md
│   └── 07-facet-by-language.md
├── 03.0-multi-chart-report/                 (5 subtasks)
│   ├── README.md
│   ├── 01-report-service-skeleton.md
│   ├── 02-per-rating-charts.md
│   ├── 03-coverage-latest-ranks-csv.md
│   ├── 04-markdown-summary-and-provenance.md
│   └── 05-report-cli-and-acceptance.md
├── 04.0-alias-management-commands/          (6 subtasks)
│   ├── README.md
│   ├── 01-alias-match-repository.md
│   ├── 02-language-resolve-service.md
│   ├── 03-languages-resolve-command.md
│   ├── 04-languages-aliases-output.md
│   ├── 05-resolution-parity-tests.md
│   └── 06-alias-add-adr.md
├── 05.0-historical-selection-semantics/     (5 subtasks)
│   ├── README.md
│   ├── 01-selection-window-resolver.md
│   ├── 02-query-service-integration.md
│   ├── 03-cli-endpoint-flags.md
│   ├── 04-endpoint-regression-suite.md
│   └── 05-selection-semantics-docs.md
└── 06.0-test-coverage-baseline/             (6 subtasks)
    ├── README.md
    ├── 01-coverage-config.md
    ├── 02-http-client-tests.md
    ├── 03-status-registry-tests.md
    ├── 04-cli-command-tests.md
    ├── 05-repository-export-tests.md
    └── 06-coverage-gate-ci.md
```

Task READMEs: [01.0](/docs/roadmap/0005-cli-and-storage-enhancements/01.0-database-inspection-views/README.md) ·
[02.0](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/README.md) ·
[03.0](/docs/roadmap/0005-cli-and-storage-enhancements/03.0-multi-chart-report/README.md) ·
[04.0](/docs/roadmap/0005-cli-and-storage-enhancements/04.0-alias-management-commands/README.md) ·
[05.0](/docs/roadmap/0005-cli-and-storage-enhancements/05.0-historical-selection-semantics/README.md)

**Baseline findings recorded during decomposition:** `latest_observations`, `language_history`,
`rating_coverage` views and `languages aliases` already exist (01.0/04.0 scope reduced to the
deltas); `plot --metric rank` and `--top/--top-current` select nothing for provider-prefixed rank
metrics (fixed in 02.0/02); `--years` counts calendar years from a rating-level (or global) latest
year (replaced in 05.0).

## Per-task detail

_Empty until a task lands. Once a task starts, add a `### Task NN.0 - Name
(status, date)` subsection per task with a **Delivered** list and a
**Tests / gate** summary._

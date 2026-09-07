# Milestone 0001 - Generic Implementation - Status

Tracks progress against [plan.md](/docs/roadmap/0001-generic-implementation/plan.md).
Updated as each task lands.

## Current status

| Task | Name                                             | Status         | Tests |
|------|---------------------------------------------------|----------------|-------|
| 01.0 | Stack Overflow Tags Provider                       | ⬜ Not started | -     |
| 02.0 | GitHub Provider                                    | ⬜ Not started | -     |
| 03.0 | IEEE Spectrum Provider                             | ⬜ Not started | -     |
| 04.0 | JetBrains Developer Ecosystem Provider              | ⬜ Not started | -     |
| 05.0 | Cross-Rating Normalization & Comparison            | ⬜ Not started | -     |
| 06.0 | Composite Index                                    | ⬜ Not started | -     |
| 07.0 | Snapshot Comparison                                | ⬜ Not started | -     |
| 08.0 | Methodology Break Tracking                         | ⬜ Not started | -     |
| 09.0 | Source Freshness Monitoring & Scheduled Updates    | ⬜ Not started | -     |
| 10.0 | Dataset Release Workflow                           | ⬜ Not started | -     |
| 11.0 | Database Inspection Views                          | ⬜ Not started | -     |
| 12.0 | Improved Plotting Options                          | ⬜ Not started | -     |
| 13.0 | Multi-Chart Report Generation                      | ⬜ Not started | -     |
| 14.0 | Alias Management Commands                          | ⬜ Not started | -     |
| 15.0 | Provider Capabilities Metadata                     | ⬜ Not started | -     |
| 16.0 | External Provider Plugin Loading                   | ⬜ Not started | -     |
| 17.0 | Large-Source Performance Hardening                 | ⬜ Not started | -     |
| 18.0 | Data Quality Dashboard                             | ⬜ Not started | -     |
| 19.0 | Source Archival Strategy                           | ⬜ Not started | -     |
| 20.0 | Historical Selection Semantics                     | ⬜ Not started | -     |
| 21.0 | Language Births, Renames & Alias Validity Ranges   | ⬜ Not started | -     |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

**Current gate status:** No task started yet. Baseline this milestone builds
on is already merged: the `RatingProvider` protocol, `ProviderRegistry`, five
bootstrap providers (`demo`, `tiobe`, `pypl`, `redmonk`,
`stackoverflow-survey`), `Database`/migrations, and the
`FetchService`/`QueryService`/`ValidationService`/`StatusService` layer (PR #3,
`be77d0d` "feat: add first production provider implementations"). CI (ruff
check, ruff format --check, mypy, pytest) is green on that baseline.

## Notes & decisions

- **Recommended provider order (Tasks 01.0-04.0):** Stack Overflow tags →
  GitHub → IEEE Spectrum → JetBrains. This order progressively adds
  monthly activity-derived metrics, then code-hosting/development activity,
  then composite-index ingestion, then additional survey-based usage — see
  plan.md's intro callout. The four tasks are independent implementation
  work and may be picked up out of order or in parallel if priorities
  change; the order is a recommendation, not a hard dependency.
- **Cross-rating work (05.0/06.0) is gated on provider reliability, not a
  task count.** plan.md is explicit that comparison/composite features
  should wait until individual provider histories are reliable — "reliable"
  is a judgment call for whoever picks up 05.0, not a fixed N-providers
  threshold.
- **Legal/source-policy review (C4 in plan.md) is a per-task closing gate,**
  not a standalone task in this milestone's table — it must be documented
  before any of Tasks 01.0-04.0 or 16.0 enables unattended scheduled
  fetching for its source.
- **Testing requirement (C5 in plan.md) applies to every task** — this
  milestone does not track test counts per task until a task actually lands;
  the `Tests` column above will be filled in with the full-suite pass count
  at that point (matching the 0002 milestone's status.md convention in
  AegisSwr).

## Decomposition tree (as planned)

Unlike Milestone 0002 in other projects, this milestone's tasks are specified
directly in `plan.md`'s "Per-task specifications" section rather than broken
out into per-task subfolders — no `{TT.t}-{task-slug}/README.md` subtask
breakdowns exist yet. A task graduates to its own subfolder (with a
`README.md` and `{NN}-{subtask-slug}.md` files, per
[docs/roadmap/README.md](/docs/roadmap/README.md)'s convention) when someone
starts implementing it and the work needs subtask-level tracking.

```
docs/roadmap/0001-generic-implementation/
├── plan.md      ← milestone spec (## Tasks table, contracts C1-C5, per-task specs)
└── status.md    ← this tracker
```

## Per-task detail

_Empty until a task lands. Once a task starts, mirror the 0002-forensic-agents
`status.md` convention in AegisSwr: a `### Task NN.0 - Name (status, date)`
subsection per task with a **Delivered** list and a **Tests / gate** summary._

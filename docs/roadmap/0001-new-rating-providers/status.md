# Milestone 0001 - New Rating Providers - Status

Tracks progress against [plan.md](/docs/roadmap/0001-new-rating-providers/plan.md).
Updated as each task lands.

## Current status

| Task | Name                                    | Status         | Tests |
|------|--------------------------------------------|----------------|-------|
| 01.0 | Stack Overflow Tags Provider                | ⬜ Not started | -     |
| 02.0 | GitHub Provider                             | ⬜ Not started | -     |
| 03.0 | IEEE Spectrum Provider                      | ⬜ Not started | -     |
| 04.0 | JetBrains Developer Ecosystem Provider      | ⬜ Not started | -     |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

**Current gate status:** No task started yet. Baseline this milestone builds
on is already merged: the `RatingProvider` protocol, `ProviderRegistry`, five
bootstrap providers (`demo`, `tiobe`, `pypl`, `redmonk`,
`stackoverflow-survey`), `Database`/migrations, and the
`FetchService`/`QueryService`/`ValidationService`/`StatusService` layer (PR #3,
`be77d0d` "feat: add first production provider implementations"). CI (ruff
check, ruff format --check, mypy, pytest) is green on that baseline.

## Notes & decisions

- **This milestone was split out of the original `0001-generic-implementation`
  umbrella document** (see
  [docs/roadmap/README.md](/docs/roadmap/README.md) for the full set of
  sibling milestones it was split into). It keeps the `0001` slot because
  it's the foundation the other five build on.
- **Recommended order:** Stack Overflow tags → GitHub → IEEE Spectrum →
  JetBrains, but the four tasks are independent and may be picked up in any
  order or in parallel.
- **Legal/source-policy review is a per-task closing gate,** not a standalone
  task — it must be documented before any task enables unattended scheduled
  fetching for its source.

## Decomposition tree (as planned)

This milestone's tasks are specified directly in `plan.md`'s "Per-task
specifications" section rather than broken out into per-task subfolders — no
`{TT.t}-{task-slug}/README.md` subtask breakdowns exist yet. A task graduates
to its own subfolder (with a `README.md` and `{NN}-{subtask-slug}.md` files,
per [docs/roadmap/README.md](/docs/roadmap/README.md)'s convention) when
someone starts implementing it and the work needs subtask-level tracking.

```
docs/roadmap/0001-new-rating-providers/
├── plan.md      ← milestone spec (## Tasks table, per-task specs)
└── status.md    ← this tracker
```

## Per-task detail

_Empty until a task lands. Once a task starts, add a `### Task NN.0 - Name
(status, date)` subsection per task with a **Delivered** list and a
**Tests / gate** summary._

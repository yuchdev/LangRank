# Milestone 0001 - New Rating Providers - Status

Tracks progress against [plan.md](/docs/roadmap/0001-new-rating-providers/plan.md).
Updated as each task lands.

## Current status

| Task | Name                                    | Status         | Tests |
|------|--------------------------------------------|----------------|-------|
| 01.0 | Stack Overflow Tags Provider                | 🔶 In progress (5/8 subtasks) | -     |
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
- **2026-09-25 - Phase R audit (implement-milestone run):** all 35 subtask specs present, no
  decomposition gaps; as-built probe found all four tasks absent (no divergence); schema stays at
  version 2, no migration required. Execution order 01.0 → 02.0 → 03.0 → 04.0 (01.0 lands the
  shared helpers the others reuse).
- **2026-09-25 - Ruling (user):** IEEE `HTML`, `Arduino`, `Verilog`, `VHDL` go into
  `IEEE_UNTRACKED_LABELS` (not added to the canonical catalog) - resolves the open choice in
  03.0/02.
- **2026-09-25 - Ruling (user):** live network calls are allowed during development to capture
  real fixtures (small, rate-limited, unauthenticated); live tests remain opt-in via the
  `integration` marker.
- **2026-09-25 - Coverage floor:** repo-root `.coveragerc` repointed from the carried-over
  `src/aegis_swr` to `src/langrank`, `fail_under` set to the measured baseline (73%) as a
  regression guard; raising it to 85% remains Milestone 0005 Task 06.0.
- **2026-09-25 - 01.0/02 deviation (verify-subtask PARTIAL):** `visual-basic` was not added to
  the canonical catalog. `_normalize_key` strips hyphens/spaces, so `visual-basic` collides with
  the pre-existing global alias `"visual basic" → vb.net` (the new collision guard raises).
  Classic VB vs VB.NET separation is open: it needs either a distinct canonical key or an
  explicit re-mapping of the bootstrap `"visual basic"` alias (a source-interpretation change for
  TIOBE). Not needed by any 0001 task.

## Decomposition tree (as planned)

Every task is decomposed into a task `README.md` (with a `## Subtasks` table) and one spec
file per subtask, per [docs/roadmap/README.md](/docs/roadmap/README.md)'s convention. All
subtasks are ⬜ Not started.

```
docs/roadmap/0001-new-rating-providers/
├── plan.md
├── status.md
├── 01.0-stack-overflow-tags-provider/   (8 subtasks)
│   ├── README.md
│   ├── 01-source-note-and-policy-gate.md
│   ├── 02-rating-scoped-aliases.md          ← shared: try_resolve / rating-scoped aliases
│   ├── 03-metadata-and-registry.md
│   ├── 04-fetch-api-and-offline-cache.md    ← shared: load_cached_payload, get_json
│   ├── 05-parse-and-normalize.md
│   ├── 06-validate.md
│   ├── 07-fixtures-and-contract-tests.md    ← shared: tests/contract/_golden.py
│   └── 08-docs.md
├── 02.0-github-provider/                (10 subtasks)
│   ├── README.md
│   ├── 01-source-note-and-policy-gate.md
│   ├── 02-quarterly-granularity.md          ← Granularity.QUARTER (no migration)
│   ├── 03-linguist-aliases.md
│   ├── 04-metadata-variants-and-registry.md
│   ├── 05-innovation-graph-fetch-and-parse.md
│   ├── 06-innovation-graph-normalize.md
│   ├── 07-octoverse-annual-rankings.md
│   ├── 08-validate.md
│   ├── 09-fixtures-and-contract-tests.md
│   └── 10-docs.md
├── 03.0-ieee-spectrum-provider/         (8 subtasks)
│   ├── README.md
│   ├── 01-source-note-and-policy-gate.md
│   ├── 02-ieee-aliases.md
│   ├── 03-metadata-profiles-and-registry.md
│   ├── 04-curated-dataset-and-fetch.md
│   ├── 05-parse-and-normalize.md
│   ├── 06-validate.md
│   ├── 07-fixtures-and-contract-tests.md
│   └── 08-docs.md
└── 04.0-jetbrains-provider/             (9 subtasks)
    ├── README.md
    ├── 01-source-note-and-policy-gate.md
    ├── 02-survey-question-registry.md
    ├── 03-jetbrains-aliases.md
    ├── 04-metadata-and-registry.md
    ├── 05-published-percentages.md
    ├── 06-raw-data-import.md
    ├── 07-validate.md
    ├── 08-fixtures-and-contract-tests.md
    └── 09-docs.md
```

**Cross-task subtask dependencies:** Tasks 02.0-04.0 reuse three helpers specified in Task
01.0 (subtasks 02, 04, 07). Whichever task starts first lands them per the 01.0 spec; the
tasks otherwise remain parallelizable.

## Per-task detail

_Empty until a task lands. Once a task starts, add a `### Task NN.0 - Name
(status, date)` subsection per task with a **Delivered** list and a
**Tests / gate** summary._

# Task 02.0 - Composite Index

**Milestone:** [0002 - Cross-Rating Analysis](/docs/roadmap/0002-cross-rating-analysis/plan.md) ·
**Spec source:** [plan.md § Task 02.0](/docs/roadmap/0002-cross-rating-analysis/plan.md#task-020---composite-index) ·
**Category:** analysis · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                   | Role          | Depends on       | Status         |
|----|---------------------------------------------------------------------------------------------------------------------------|---------------|------------------|----------------|
| 01 | [Composite spec & validation](/docs/roadmap/0002-cross-rating-analysis/02.0-composite-index/01-composite-spec.md)          | Python Expert | 01.0/02          | ⬜ Not started |
| 02 | [Composite math](/docs/roadmap/0002-cross-rating-analysis/02.0-composite-index/02-composite-math.md)                      | Python Expert | 01               | ⬜ Not started |
| 03 | [`CompositeService` & year alignment](/docs/roadmap/0002-cross-rating-analysis/02.0-composite-index/03-composite-service.md) | Python Expert | 02, 01.0/03, 03.0/01 | ⬜ Not started |
| 04 | [`langrank composite` CLI](/docs/roadmap/0002-cross-rating-analysis/02.0-composite-index/04-composite-cli.md)              | Python Expert | 03               | ⬜ Not started |
| 05 | [Composite docs](/docs/roadmap/0002-cross-rating-analysis/02.0-composite-index/05-docs.md)                                | Docs Writer   | 04               | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

An opt-in `langrank composite` that combines several ratings into one **derived** score per
language and year, where the user must state every ingredient - sources, metric, normalization,
weights, missing-data policy - and every output row shows its contributions and carries the
`derived composite` label. Never a hidden average; never "the true popularity rating".

## Baseline (what already exists)

- Nothing composite-related exists. Builds on Task 01.0: `NormalizationMethod` registry,
  `ComparisonService`-style per-rating normalization, `resolve_rank_metric`.
- Ratings have different native cadences (TIOBE/PYPL monthly, RedMonk semi-annual stored as
  `month`, Stack Overflow survey annual), so combining requires an explicit common period grid.

## Design notes

- **Normalize first, then align.** Each rating is normalized on its own native periods (so `n`
  is that publication's population), then one normalized point per rating per year is picked with
  Task 03.0's `select_reference_period` (latest period within the year). Monthly values are
  **not averaged** into a year - averaging would be exactly the hidden aggregation the plan
  forbids. This adds a dependency on
  [03.0/01](/docs/roadmap/0002-cross-rating-analysis/03.0-snapshot-comparison/01-selection-rules.md).
- **Grid:** `year` only in this task (`--granularity` is not offered; the output states
  "annual grid, latest observation in year per source").
- **Missing-data policies** (enum, required, no default):
  - `require-all` - a language/year gets a score only if every included rating has a point;
    otherwise the cell is a reported gap.
  - `renormalize-weights` - weighted mean over the ratings present, weights rescaled to the
    present subset; requires `--min-sources K` (1 ≤ K ≤ m) and cells below K are gaps. Output
    shows `sources_present/sources_total`.
  - `drop-language` - a language missing in any rating for any year of the window is removed
    from the whole result and listed in `dropped_languages`.
  None of them imputes a value.
- **Composite rank** is itself derived (competition ranking "1, 2, 2, 4": ties share a rank) and
  labelled as such.
- **Metric choice** is required: `--metric rank` (each rating's rank metric via
  `resolve_rank_metric`) or an explicit `--metric tiobe=tiobe-rank,pypl=pypl-rank,...` map covering
  every rating. The method must accept the metric kind (`rank-percentile` → rank metrics).

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] Omitting any of `--ratings`, `--metric`, `--normalize`, `--weights`, `--missing` is a CLI
      usage error (exit 2), not a silent default.
- [ ] Every output row (table, JSON, CSV) carries `derived composite` and its contributions.
- [ ] Nothing composite-related is persisted to SQLite.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- [plan.md § No hidden averaging / no silent interpolation](/docs/roadmap/0002-cross-rating-analysis/plan.md#no-hidden-averaging--no-silent-interpolation)
- [Task 01.0 README](/docs/roadmap/0002-cross-rating-analysis/01.0-cross-rating-normalization/README.md) (definition of `n`)

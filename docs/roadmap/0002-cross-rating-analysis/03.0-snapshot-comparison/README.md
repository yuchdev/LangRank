# Task 03.0 - Snapshot Comparison

**Milestone:** [0002 - Cross-Rating Analysis](/docs/roadmap/0002-cross-rating-analysis/plan.md) ·
**Spec source:** [plan.md § Task 03.0](/docs/roadmap/0002-cross-rating-analysis/plan.md#task-030---snapshot-comparison) ·
**Category:** cli · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                         | Role          | Depends on | Status         |
|----|---------------------------------------------------------------------------------------------------------------------------------|---------------|------------|----------------|
| 01 | [Snapshot selection rules](/docs/roadmap/0002-cross-rating-analysis/03.0-snapshot-comparison/01-selection-rules.md)             | Python Expert | 01.0/01    | ⬜ Not started |
| 02 | [`SnapshotService`](/docs/roadmap/0002-cross-rating-analysis/03.0-snapshot-comparison/02-snapshot-service.md)                    | Python Expert | 01         | ⬜ Not started |
| 03 | [`langrank snapshot` CLI](/docs/roadmap/0002-cross-rating-analysis/03.0-snapshot-comparison/03-snapshot-cli.md)                  | Python Expert | 02         | ⬜ Not started |
| 04 | [Snapshot docs](/docs/roadmap/0002-cross-rating-analysis/03.0-snapshot-comparison/04-docs.md)                                   | Docs Writer   | 03         | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

`langrank snapshot 2020` / `langrank snapshot latest` print one row per language and one column
per rating, each cell a **real stored rank with its true observation date**, or explicitly
blank. No normalization and no combination - ranks sit side by side in a table, so the
no-shared-axis rule is respected without any derived value.

## Baseline (what already exists)

- No snapshot command. `langrank query` already prints raw rows for a single rating.
- `AnalysisRow`, `Database.query_analysis_rows`, `resolve_rank_metric`, `parse_metric_map` from
  [Task 01.0 subtask 01](/docs/roadmap/0002-cross-rating-analysis/01.0-cross-rating-normalization/01-analysis-data-access.md) -
  the **only** dependency on Task 01.0 (not on normalization). This refines plan.md's "03.0 is
  independent of 01.0/02.0": it is independent of the normalization and composite work.
- Stored granularities are only `year` and `month` (`models.py:Granularity`). RedMonk is
  semi-annual but stored as `month` rows (`2016-01-01`, `2016-06-01`, ...); PYPL/TIOBE are monthly;
  Stack Overflow survey is `year`.
- `stackoverflow-survey-rank` is provider-computed but stored `is_derived=False` (see Task 01.0
  README); the snapshot shows what is stored and documents the caveat.

## Design notes

- **One reference period per column.** Selection picks a period per `(rating, metric)` first,
  then reads every language's rank *at that period*. A language missing at the reference period
  is blank - it is **never** filled from an earlier month. This keeps every column internally
  consistent (one publication), which is what a reader of a snapshot assumes.
- **Year target Y:** reference period = the latest `period_start` within `[Y-01-01, Y-12-31]`
  for that rating/metric. Works identically for annual and sub-annual sources, so the rule needs
  no granularity branching. No borrowing from `Y-1` / `Y+1`.
- **`latest` target:** reference period = the rating's latest `period_start` overall
  (latest-per-source, not a single global date). Columns may therefore have different dates;
  the output always prints them.
- **Date shown when ambiguous:** a column is flagged when (a) a sub-annual source's reference
  period is not December of `Y` (data ends mid-year or is semi-annual), or (b) in `latest`
  mode the columns' reference dates are not all in the same calendar year.
- **The snapshot composite consumer.** Task 02.0's year alignment reuses `select_reference_period`
  from subtask 01, so it lands before Task 02.0 subtask 03.

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] A snapshot cell is always a real observation (true date available in every output format)
      or explicitly blank - never computed.
- [ ] `langrank snapshot 2020` and `langrank snapshot latest` run against fetched bundled data.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- [plan.md § No hidden averaging / no silent interpolation](/docs/roadmap/0002-cross-rating-analysis/plan.md#no-hidden-averaging--no-silent-interpolation)
- [docs/source-notes/redmonk.md](/docs/source-notes/redmonk.md),
  [docs/source-notes/stackoverflow-survey.md](/docs/source-notes/stackoverflow-survey.md)

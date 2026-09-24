# Task 05.0 - Historical Selection Semantics

**Milestone:** [0005 - CLI & Storage Enhancements](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md) ·
**Spec source:** [plan.md § Task 05.0](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#task-050---historical-selection-semantics) ·
**Category:** cli · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                                   | Role           | Depends on | Status         |
|----|-------------------------------------------------------------------------------------------------------------------------------------------|----------------|------------|----------------|
| 01 | [Selection window model and resolver](/docs/roadmap/0005-cli-and-storage-enhancements/05.0-historical-selection-semantics/01-selection-window-resolver.md)           | Python Expert  | -          | ⬜ Not started |
| 02 | [Wire the resolver into `QueryService`](/docs/roadmap/0005-cli-and-storage-enhancements/05.0-historical-selection-semantics/02-query-service-integration.md)          | Python Expert  | 01         | ⬜ Not started |
| 03 | [Uniform CLI flags across query/export/plot](/docs/roadmap/0005-cli-and-storage-enhancements/05.0-historical-selection-semantics/03-cli-endpoint-flags.md)             | Python Expert  | 02         | ⬜ Not started |
| 04 | [Regression suite pinning endpoint behaviour](/docs/roadmap/0005-cli-and-storage-enhancements/05.0-historical-selection-semantics/04-endpoint-regression-suite.md)     | Testing Expert | 03         | ⬜ Not started |
| 05 | [Document selection semantics](/docs/roadmap/0005-cli-and-storage-enhancements/05.0-historical-selection-semantics/05-selection-semantics-docs.md)                    | Docs Writer    | 03         | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

Give `--years N` one precise, documented meaning - "N years back from the latest available
observation of the selected rating/metric, or from `--until` if given" - resolved in one place
and applied identically by `query`, `export csv|json`, and `plot`, with an explicit policy for
multi-rating commands.

## Baseline (what already exists)

- `QueryService.resolve_filters`: when `years` is set and `since` is not, calls
  `Database.resolve_year_bounds(rating_id)` (calendar **years** only) and sets
  `since = date(latest_year - years + 1, 1, 1)`, `until = until or date(latest_year, 12, 31)`.
  Consequences:
  - Granularity is a whole calendar year: with monthly data ending 2025-03, `--years 1` returns
    Jan-Mar 2025 only (3 months, not 12).
  - The endpoint is per **rating**, not per rating+metric; `resolve_year_bounds(None)` (no
    `--rating`) takes the global max across all ratings.
  - `--until` combined with `--years` is ignored for the start (start still counts back from the
    DB's latest year, not from `--until`).
- `export csv|json --ratings a,b` already loops per provider calling `_build_filters` → endpoint is
  implicitly per-source; `query`/`plot` accept a single `--rating`.
- `cli.py:_parse_date` maps `YYYY` to Jan 1 / Dec 31.
- `Database.query_rows` filters `period_start >= since AND period_end <= until`.

## Design notes

- **Endpoint rule (normative):** `E = until if --until given else max(period_start)` over rows
  matching `(rating_id, metric_id)` (metric omitted → all metrics of the rating). Window =
  observations with `period_start > E − N years` and `period_start ≤ E` (and `period_end ≤ until`
  when `--until` is explicit). `E − N years` subtracts calendar years on the same month/day,
  clamping Feb 29 → Feb 28. For annual data (`period_start = YYYY-01-01`) `--years 10` yields
  exactly 10 editions; for monthly, exactly 120 months (if all published).
- **Multi-rating policy (`EndpointPolicy`)**: `per-source` (default - each rating uses its own
  latest, so a source that has not published this year is not truncated), `global` (one E = max
  across the selected ratings, useful for aligned snapshots), and implicit `explicit` whenever
  `--until` is given. The resolved policy and per-rating windows are recorded in export sidecars.
- **`--year`/`--since` keep current meaning.** `--year Y` = that calendar year; `--since` +
  `--years` is a usage error (ambiguous), rather than silently preferring one.
- **Semantics change is intentional and documented** in CHANGELOG/README, since `--years N` on
  monthly data will now return more rows than before.

### Open questions

- Should `global` be the default for Milestone 0002 `snapshot`? **Default: that command chooses;**
  this task only provides the enum.

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] `QueryService`/`export`/`plot` all resolve `--years N` identically per the documented rule.
- [ ] A regression test pins the endpoint behaviour for a source with a stale current year.
- [ ] Rule and policy documented in each command's `--help`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- [Milestone 0002 Task 03.0](/docs/roadmap/0002-cross-rating-analysis/plan.md#task-030---snapshot-comparison) (consumer of `EndpointPolicy`)

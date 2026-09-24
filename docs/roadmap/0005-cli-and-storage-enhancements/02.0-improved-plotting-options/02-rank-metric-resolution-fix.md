# Subtask 02.0/02 - Fix rank-metric resolution in `plot` and top filters

**Task:** [02.0 - Improved Plotting Options](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started


> **Coordination - one rank-metric helper.** Three subtasks touch "which metrics are ranks":
> [0005 02.0/02](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/02-rank-metric-resolution-fix.md),
> [0003 03.0/01](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/01-quality-framework.md) and
> [0006 01.0/02](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/02-metric-role-lookups.md).
> There is exactly one helper, `Database.rank_metric_ids() -> set[str]`. Whichever of the first
> two lands first creates it (interim rule: `metrics.unit = 'rank' AND higher_is_better = 0`);
> the other reuses it. 0006 01.0/02 then re-implements its body on `metrics.kind = 'rank'`
> without changing callers. No other module may compare a metric ID with `"rank"`.

## Goal

Make `langrank plot`, `--top`, and `--top-current` work for provider-prefixed metric IDs
(`tiobe-rank`, `redmonk-rank`, …) by using the resolved metric ID and the existing `unit`
metadata instead of comparing against the bare string `"rank"`.

## Baseline

- `cli.py:plot`: `rows = [row for row in … if row.metric_id == metric]` where `metric` is the raw
  CLI value, while `filters.metric_id` holds the resolved ID → empty result for production
  providers.
- `PlotService` inverts only when `metric_id == "rank"`.
- `QueryService._apply_top_filters`: `row.metric_id == "rank"` in both `top_current` and `top`
  branches. `resolve_filters` sets `metric_id=None` for the selector query when top filters are
  used, so rows of all metrics arrive; the rank rows must be picked by unit.
- `QueryRow.unit` is already selected by `Database.query_rows`.
- `tests/unit/test_query_service.py::test_top_current_filters_latest_snapshot` uses demo `rank`.

## Files

| Action | Path                                   | Purpose |
|--------|----------------------------------------|---------|
| Modify | `src/langrank/cli.py`                  | `plot` filters by `filters.metric_id`; passes resolved metric + `MetricDefinition` to `PlotOptions` |
| Modify | `src/langrank/plotting/service.py`     | Inversion from `PlotOptions.rank_metric` instead of ID string |
| Modify | `src/langrank/services/query.py`       | `_apply_top_filters` selects rank rows by `row.unit == "rank"` |
| Modify | `tests/unit/test_plot_invariants.py`   | Tests below |
| Modify | `tests/unit/test_query_service.py`     | Tests below |

## Symbols / fields

| Symbol                         | Kind     | Type / signature | Default | Notes |
|--------------------------------|----------|------------------|---------|-------|
| `PlotOptions.rank_metric`      | field    | `bool`           | `False` | True when the metric's `unit == "rank"` and `higher_is_better is False` |
| `is_rank_metric`               | function | `(definition: MetricDefinition) -> bool` | - | In `src/langrank/plotting/service.py`; single place encoding the rule |
| `QueryService._is_rank_row`    | staticmethod | `(row: QueryRow) -> bool` | - | `row.unit == "rank"` |

## Behaviour & validators

1. `plot` uses the resolved `filters.metric_id` for both the post-query filter and the axis label.
2. Axis inverted iff `options.rank_metric and options.invert_rank`; `--no-invert-rank` still wins.
3. `--top N` / `--top-current N` pick languages from rows where `unit == "rank"`; if the rating has
   no rank-unit metric, raise `LangRankError` ("rating X has no rank metric; --top requires one")
   rather than silently plotting nothing.
4. Demo behaviour (bare `rank`) is unchanged.
5. No new field on `MetricDefinition`/`ProviderMetadata` (reserved for Milestone 0006 Task 01.0).

## Tests

| Test function                                         | File                                 | Type        | Asserts |
|-------------------------------------------------------|--------------------------------------|-------------|---------|
| `test_rank_axis_inverted_for_prefixed_rank_metric`    | `tests/unit/test_plot_invariants.py` | Unit        | `redmonk-rank` rows → inverted y-axis |
| `test_value_metric_axis_not_inverted`                 | `tests/unit/test_plot_invariants.py` | Unit        | `pypl-share` → not inverted |
| `test_no_invert_rank_flag_respected`                  | `tests/unit/test_plot_invariants.py` | Unit        | `invert_rank=False` → not inverted |
| `test_top_current_with_prefixed_rank_metric`          | `tests/unit/test_query_service.py`   | Unit        | Seeded `tiobe-rank` rows; `top_current=1` selects rank-1 language |
| `test_top_with_prefixed_rank_metric`                  | `tests/unit/test_query_service.py`   | Unit        | `top=2` selects languages ranked ≤2 in any period |
| `test_top_without_rank_metric_raises`                 | `tests/unit/test_query_service.py`   | Unit        | Value-only rating → `LangRankError` |
| `test_cli_plot_redmonk_rank_draws_lines`              | `tests/integration/test_cli.py`      | Integration | `fetch redmonk` then `plot --rating redmonk --metric rank --languages python --output x.png` exits 0 and file exists; builder sees ≥1 line |

## Success criteria

- [ ] The milestone example `plot --rating redmonk --metric rank --languages python,c++,rust --years 10` plots three lines on an inverted axis.
- [ ] Existing `test_top_current_filters_latest_snapshot` still passes.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Do not special-case provider IDs (`if rating == "redmonk"`) - use metadata.
- Plotting invariants still hold (`assert_plot_invariants` in each new plot test).

## Out of scope

- Declared metric roles / capabilities ([Milestone 0006 Task 01.0](/docs/roadmap/0006-provider-extensibility/plan.md#task-010---provider-capabilities-metadata)).
- The same bare-`'rank'` bug in `Database.validation_queries()["invalid_ranks"]` - validation belongs to [Milestone 0003](/docs/roadmap/0003-historical-data-quality/plan.md); note it there.

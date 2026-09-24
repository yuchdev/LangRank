# Subtask 01.0/02 - Metric-Role Lookups Replace Bare `"rank"`

**Task:** [01.0 - Provider Capabilities Metadata](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/README.md) ·
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

Every place that decides "is this a rank metric?" by comparing a metric ID to the literal
`"rank"` instead asks the stored `MetricKind`. This fixes `--top`/`--top-current`, the
`invalid_ranks` validation, and rank-axis inversion for all production providers, and makes
`plot`'s default metric come from the rating's declared `default_metric`.

## Baseline

- `src/langrank/services/query.py:QueryService._apply_top_filters` (static) - three
  `row.metric_id == "rank"` comparisons.
- `src/langrank/db/repository.py:Database.validation_queries` - `invalid_ranks` query uses
  `WHERE metric_id = 'rank' AND rank <= 0`.
- `src/langrank/plotting/service.py:PlotService.plot` - `if metric_id == "rank" and invert_rank`.
- `src/langrank/cli.py:plot` - `metric: str = typer.Option("rating", "--metric")`; rows are then
  filtered by `row.metric_id == metric`, so the default only works for `demo`.
- `Database.metric_ids_by_kind` from [subtask 01](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/01-metric-kind-metadata.md).

## Files

| Action | Path                                   | Purpose                                                    |
|--------|----------------------------------------|------------------------------------------------------------|
| Modify | `src/langrank/services/query.py`       | `_apply_top_filters` takes the set of rank metric IDs; add `default_metric_id` |
| Modify | `src/langrank/db/repository.py`        | `invalid_ranks` joins `metrics` on `kind = 'rank'`; add `metric_kind(metric_id)` |
| Modify | `src/langrank/plotting/service.py`     | Replace `metric_id == "rank"` with a `metric_kind: MetricKind` parameter |
| Modify | `src/langrank/cli.py`                  | `plot --metric` default `None` → resolve via `QueryService.default_metric_id`; pass kind to `PlotService` |
| Create | `tests/unit/test_metric_role_lookups.py` | Regression tests on production-provider fixtures        |

## Symbols / fields

| Symbol                                  | Kind     | Type / signature                                                          | Default | Notes |
|-----------------------------------------|----------|---------------------------------------------------------------------------|---------|-------|
| `QueryService._apply_top_filters`       | method   | `(rows: list[QueryRow], filters: QueryFilters, rank_metric_ids: set[str]) -> list[str]` | - | Still static; caller supplies IDs from `metric_ids_by_kind(MetricKind.RANK, filters.rating_id)` |
| `QueryService.default_metric_id`        | method   | `(rating_id: str) -> str`                                                 | -       | Reads `ratings.default_metric`; raises `ProviderError` for unknown rating |
| `Database.metric_kind`                  | method   | `(metric_id: str) -> MetricKind \| None`                                  | -       | `None` if metric unknown |
| `PlotService.plot(metric_kind=...)`     | kw param | `metric_kind: MetricKind`                                                 | required | Replaces the string check |
| `cli.plot --metric`                     | option   | `str \| None`                                                             | `None`  | `None` → rating's `default_metric` |

## Behaviour & validators

1. No bare `"rank"`/`'rank'` string compared against a **metric ID** remains in
   `src/langrank/services/`, `src/langrank/db/repository.py`, `src/langrank/plotting/`,
   `src/langrank/cli.py`. (`unit = 'rank'` comparisons in the migration backfill are fine.)
2. `invalid_ranks` becomes:
   `SELECT o.rating_id, o.language_id, o.period_start, o.rank FROM observations o JOIN metrics m ON m.id = o.metric_id WHERE m.kind = 'rank' AND o.rank <= 0`.
3. `--top N` / `--top-current N` select languages from the rating's RANK-kind metric rows;
   if a rating declares no RANK metric, the CLI exits with a `LangRankError` message
   ("rating X has no rank metric; --top unavailable") instead of silently returning nothing.
4. Rank axis is inverted iff `metric_kind is MetricKind.RANK and invert_rank`.
5. Multi-rating paths still never share an axis across ratings (unchanged invariant).

## Tests

| Test function                                         | File                                     | Type        | Asserts |
|-------------------------------------------------------|------------------------------------------|-------------|---------|
| `test_top_filter_selects_languages_for_tiobe`         | `tests/unit/test_metric_role_lookups.py` | Integration | Import `tests/fixtures/tiobe/sample.csv` into a tmp DB; `QueryService.query(QueryFilters(rating_id="tiobe", metric_id="tiobe-rating", top=3))` returns only languages ranked ≤3 |
| `test_top_current_uses_latest_rank_period_for_redmonk`| `tests/unit/test_metric_role_lookups.py` | Integration | Same with `redmonk` fixture and `top_current` |
| `test_invalid_ranks_fires_for_prefixed_rank_metric`   | `tests/unit/test_metric_role_lookups.py` | Integration | Insert a `pypl-rank` observation with `rank=0`; `ValidationService.validate()` reports code `invalid_ranks` |
| `test_plot_inverts_axis_for_rank_kind`                | `tests/unit/test_metric_role_lookups.py` | Unit        | Patch `matplotlib.axes.Axes.invert_yaxis`; called for `MetricKind.RANK`, not for `SHARE` |
| `test_plot_default_metric_is_rating_default`          | `tests/unit/test_metric_role_lookups.py` | E2E         | `CliRunner` `plot --rating pypl --languages python --output x.png` without `--metric` succeeds and uses `pypl-share` |
| `test_top_without_rank_metric_is_usage_error`         | `tests/unit/test_metric_role_lookups.py` | Unit        | Rating with only a SHARE metric + `--top` raises `LangRankError` |
| `test_demo_provider_behaviour_unchanged`              | `tests/unit/test_metric_role_lookups.py` | Integration | Existing demo `--top` result identical before/after |

## Success criteria

- [ ] `grep -rnE "metric_id *(==|=) *['\"]rank['\"]" src/langrank` returns nothing.
- [ ] Existing tests in `tests/unit/test_query_service.py` and `tests/integration/` still pass unmodified (or are updated only to add `kind`).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Lookups happen in services/repository, not in providers (providers stay DB-free).
- No fallback that "guesses" rank-ness from the ID suffix - the stored kind is the only source.
- Coding standard: [docs/dev/python_coding_standard.md](/docs/dev/python_coding_standard.md).

## Out of scope

- New plotting flags ([Milestone 0005 Task 02.0](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#task-020---improved-plotting-options)).
- `--years` endpoint semantics ([Milestone 0005 Task 05.0](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#task-050---historical-selection-semantics)).

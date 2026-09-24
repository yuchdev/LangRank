# Task 01.0 - Cross-Rating Normalization & Comparison

**Milestone:** [0002 - Cross-Rating Analysis](/docs/roadmap/0002-cross-rating-analysis/plan.md) ·
**Spec source:** [plan.md § Task 01.0](/docs/roadmap/0002-cross-rating-analysis/plan.md#task-010---cross-rating-normalization--comparison) ·
**Category:** analysis · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                                              | Role          | Depends on | Status         |
|----|------------------------------------------------------------------------------------------------------------------------------------------------------|---------------|------------|----------------|
| 01 | [Analysis data access & rank-metric resolution](/docs/roadmap/0002-cross-rating-analysis/01.0-cross-rating-normalization/01-analysis-data-access.md) | Python Expert | -          | ⬜ Not started |
| 02 | [`rank_percentile` normalization method](/docs/roadmap/0002-cross-rating-analysis/01.0-cross-rating-normalization/02-rank-percentile.md)             | Python Expert | 01         | ⬜ Not started |
| 03 | [`ComparisonService`](/docs/roadmap/0002-cross-rating-analysis/01.0-cross-rating-normalization/03-comparison-service.md)                              | Python Expert | 01, 02     | ⬜ Not started |
| 04 | [`plot compare` CLI & derived plot rendering](/docs/roadmap/0002-cross-rating-analysis/01.0-cross-rating-normalization/04-plot-compare-cli.md)         | Python Expert | 03         | ⬜ Not started |
| 05 | [`minmax` / `zscore` methods (deferrable)](/docs/roadmap/0002-cross-rating-analysis/01.0-cross-rating-normalization/05-minmax-zscore.md)              | Python Expert | 02         | ⬜ Not started |
| 06 | [Cross-rating analysis user docs](/docs/roadmap/0002-cross-rating-analysis/01.0-cross-rating-normalization/06-docs.md)                                 | Docs Writer   | 04         | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

Subtask 05 is explicitly **deferrable**: the task may close as "✅ Complete (subtask 05
deferred)" once 01-04 and 06 land, because plan.md names `minmax`/`zscore` as later,
additive methods.

## Goal

Let a user compare one language's standing across several ratings **without ever putting raw
values from different ratings on one axis**. Every compared value is converted to a derived
`rank_percentile` score (1.0 = best, 0.0 = worst within that rating's ranked population for
that period), labelled as derived, computed on read and never persisted. Delivered as a pure
`src/langrank/analysis/` package (math, no DB), a `ComparisonService` (orchestration), and a
`langrank plot compare` sub-command.

## Baseline (what already exists)

- `src/langrank/db/repository.py:Database.query_rows` returns `QueryRow` (no `granularity`,
  `is_derived`, `derivation_method`, `metadata_json`). `QueryRow` is also what CSV/JSON export
  serialise via `asdict`, so it must **not** grow fields (would silently change export columns);
  subtask 01 adds a separate `AnalysisRow`.
- `src/langrank/cli.py:plot` is a single `@app.command()`; `plot compare` requires turning it
  into a Typer group whose callback keeps today's `langrank plot --rating ...` behaviour
  (subtask 04).
- `src/langrank/plotting/service.py:PlotService.plot` draws one metric; it only inverts the
  y-axis when `metric_id == "rank"`.
- **Metric IDs are provider-prefixed**: `tiobe-rank`, `pypl-rank`, `redmonk-rank`,
  `stackoverflow-survey-rank`; only `demo` uses bare `rank`. There is no structured "this metric
  is the rank metric" marker yet - that is
  [Milestone 0006 Task 01.0](/docs/roadmap/0006-provider-extensibility/plan.md#task-010---provider-capabilities-metadata)'s
  metric-role metadata. Interim rule (subtask 01): the rank metric of a rating is the unique
  `MetricDefinition` with `unit == "rank"`, overridable with `--metric-map`.
- Bundled provider CSVs (`src/langrank/providers/data/*.csv`) hold only ~5 tracked languages per
  period, while the real published lists are longer (TIOBE top 20/50, PYPL ~28, RedMonk ~20
  with ties). The stored row count per period is therefore **not** the ranked population `n`.
- `stackoverflow-survey-rank` is computed by the provider (ordering `worked_with_percent` among
  the rows in the CSV) but stored with `is_derived=False`. That is a provenance defect outside
  this milestone (belongs to 0001/0003); this task must not make it worse and must propagate
  `is_derived`/`derivation_method` of source rows when they are set.

## Design notes

- **Pure math in `analysis/`, orchestration in `services/`.** `analysis/normalization.py` takes
  `Sequence[AnalysisRow]` and returns derived points; it never opens the DB. This mirrors the
  providers-are-pure rule and makes the math unit-testable on literal rows.
- **Definition of `n` (ranked population).** For rating `R`, metric `M`, period `P`
  (`period_start` + `granularity`), `n` is resolved by the first rule that applies, and the
  rule used is recorded as `population_source`:
  1. `override` - user passed `--rank-population R=N`.
  2. `list_size` - every stored row for `(R, M, P)` carries the same integer
     `metadata_json["list_size"]` (the full published list length, set by a provider that
     parses the complete list). Providers are not required to set it; this is an opt-in hook.
  3. `max_rank` - `MAX(rank)` over **all stored rows** for `(R, M, P)` regardless of the
     user's language selection. This is a lower bound of the true population; output carries a
     warning that low-ranked languages score lower than they would against the full list.
- **Top-N sources.** Sources that publish only a top-N list make `rank_percentile` "position
  within the published list", not "position among all languages". To compare two ratings with
  different list lengths on equal footing, `--common-top N` sets `n = N` for every rating and
  excludes (does not zero) rows ranked worse than `N`; excluded rows are reported.
- **Ties** (RedMonk): equal ranks get equal scores; no tie-breaking.
- **Absent languages** produce no point (a gap), never `0.0`.
- **CLI default.** `plot compare --normalize` defaults to `rank-percentile` (plan allows
  "require or default to explicit normalization"), the value is always printed/plotted as
  derived, and `--normalize none` is rejected with exit code 2.
- **Legacy `plot` guard.** While restructuring `plot`, the legacy callback refuses rows that span
  more than one `rating_id` (points the user at `plot compare`) - enforcing the
  no-shared-axis rule that today is only enforced by accident of metric naming.

### Open questions

- Should `ComparisonService` accept multiple languages per call (one subplot per language)?
  Proposed default: yes at the service level (`language_ids: list[str]`), but the CLI requires
  exactly one `--language` in this task; multi-language faceting follows
  [Milestone 0005 Task 02.0](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#task-020---improved-plotting-options)'s `--facet`.

## Task exit criteria

- [ ] Every subtask above is ✅ (05 may be deferred).
- [ ] `langrank plot compare --language python --ratings tiobe,pypl,redmonk --years 10` writes a
      plot whose axis, title and legend label the series as derived `rank_percentile`.
- [ ] `plot compare --normalize none` exits 2 with an explanation; legacy `langrank plot
      --rating tiobe --metric rank ...` keeps working unchanged.
- [ ] `rank_percentile` is covered by unit tests against known `(r, n)` inputs, ties, `n = 1`,
      and each `population_source`.
- [ ] No normalized value is written to SQLite (asserted by a test).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- [plan.md § Derived-value labeling](/docs/roadmap/0002-cross-rating-analysis/plan.md#derived-value-labeling)
- [CLAUDE.md](/CLAUDE.md) § "Conventions worth knowing" (no shared axis across ratings)
- [docs/source-notes/redmonk.md](/docs/source-notes/redmonk.md) (ties),
  [docs/source-notes/pypl.md](/docs/source-notes/pypl.md) (combined `c-cpp` category)

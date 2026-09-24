# Task 02.0 - Improved Plotting Options

**Milestone:** [0005 - CLI & Storage Enhancements](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md) ·
**Spec source:** [plan.md § Task 02.0](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#task-020---improved-plotting-options) ·
**Category:** cli · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                                          | Role           | Depends on | Status         |
|----|--------------------------------------------------------------------------------------------------------------------------------------------------|----------------|------------|----------------|
| 01 | [Plotting-invariant regression harness](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/01-plotting-invariant-harness.md) | Testing Expert | -          | ⬜ Not started |
| 02 | [Fix rank-metric resolution in `plot` and top filters](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/02-rank-metric-resolution-fix.md) | Python Expert  | 01         | ⬜ Not started |
| 03 | [Gap-aware line segments](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/03-gap-aware-segments.md)                     | Python Expert  | 01         | ⬜ Not started |
| 04 | [`--annotate-methodology`](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/04-annotate-methodology.md)                   | Python Expert  | 01         | ⬜ Not started |
| 05 | [`--log-y` and `--legend-position`](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/05-log-y-and-legend-position.md)     | Python Expert  | 01         | ⬜ Not started |
| 06 | [`--smooth` (visual only)](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/06-visual-smoothing.md)                       | Python Expert  | 01, 03     | ⬜ Not started |
| 07 | [`--facet` (one panel per language)](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/07-facet-by-language.md)            | Python Expert  | 01, 03     | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

Extend `langrank plot` incrementally with the flags the plan lists, while pinning the
[plotting invariants](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#plotting-invariants)
with a named regression test each, and fixing the latent rank-metric bug that makes the
flagship example (`plot --rating redmonk --metric rank`) produce an empty chart today.

## Baseline (what already exists)

- `src/langrank/plotting/service.py:PlotService.plot(rows, *, metric_id, output, title, width,
  height, dpi, markers, invert_rank)` - one line per language, drops `value is None` points,
  inverts the y-axis only when `metric_id == "rank"`.
- `src/langrank/cli.py:plot` already has `--since/--until/--years/--top/--top-current/--markers/
  --invert-rank/--no-invert-rank/--width/--height/--dpi/--title/--output`.
- **Latent bug 1:** `plot` passes the raw CLI `--metric` value (e.g. `rank`) to both the post-query
  filter `row.metric_id == metric` and `PlotService`, but `_build_filters` has already mapped it to
  the provider-prefixed ID (`redmonk-rank`). Result: zero rows plotted for every production
  provider; only `demo` (bare `rank`) works.
- **Latent bug 2:** `QueryService._apply_top_filters` keys `--top`/`--top-current` on
  `row.metric_id == "rank"`, so both flags select nothing for production providers.
- **Invariant gap:** dropped `None`/missing periods are bridged by a straight line - an implicit
  visual interpolation the plan forbids by default.
- `tests/conftest.py` already forces `MPLBACKEND=Agg`.
- `Database.list_methodology_notes(rating_id)` and `methodology_notes` table (migration 2) exist
  today; providers already ship `MethodologyNote`s.

## Design notes

- **Rank detection uses existing metadata, not a new model field.** A metric is treated as a
  rank metric when its `MetricDefinition.unit == "rank"` (rows: `QueryRow.unit == "rank"`), and
  axis inversion follows `higher_is_better is False and unit == "rank"`. The principled,
  provider-declared metric role belongs to
  [Milestone 0006 Task 01.0](/docs/roadmap/0006-provider-extensibility/plan.md#task-010---provider-capabilities-metadata);
  subtask 02 must not add a model field that pre-empts it, only use what exists.
- **`--start`/`--end` are not added.** `plot` already has `--since`/`--until` with the same
  meaning; adding synonyms is the speculative complexity the plan warns against. `--help` text
  notes it. Window semantics are owned by
  [Task 05.0](/docs/roadmap/0005-cli-and-storage-enhancements/05.0-historical-selection-semantics/README.md).
- **Tests inspect artists, not pixels.** Each invariant test calls a pure builder that returns the
  `Figure` (subtask 01 splits `PlotService.plot` into `build_figure(...) -> Figure` + save/show),
  then asserts on `Line2D.get_xdata()/get_ydata()`, `Axes.yaxis_inverted()`, `Axes.get_yscale()`.
- **Every new flag gets an invariant test with the flag active** (plan success criterion).
- **Single-rating only.** `plot` takes one `--rating`; no flag here may combine ratings on one axis
  (cross-rating is Milestone 0002's `plot compare`).

### Open questions

- Gap threshold for monthly data with irregular publication (e.g. RedMonk twice-yearly):
  **default** = gap when a step exceeds 1.5× the series' modal step (subtask 03).

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] Each new flag ships with a test asserting the plotting invariants still hold with it active.
- [ ] `langrank plot --rating redmonk --metric rank --languages python,c++,rust --years 10`
      draws three inverted-axis lines.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- [plan.md § Plotting invariants](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#plotting-invariants)
- [Milestone 0003 Task 01.0](/docs/roadmap/0003-historical-data-quality/plan.md#task-010---methodology-break-tracking) (methodology data for subtask 04)

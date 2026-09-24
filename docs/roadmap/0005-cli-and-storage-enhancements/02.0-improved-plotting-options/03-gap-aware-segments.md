# Subtask 02.0/03 - Gap-aware line segments

**Task:** [02.0 - Improved Plotting Options](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Stop drawing a straight line across missing periods (an implicit visual interpolation): break
each language's line wherever a period is missing, with an explicit opt-in `--connect-gaps` to
restore the old look.

## Baseline

- `PlotService` builds `points` from rows with `value is not None` and passes them to one
  `ax.plot` call, so any gap (missing month, `None` value, language absent from an edition) is
  bridged.

## Files

| Action | Path                                   | Purpose |
|--------|----------------------------------------|---------|
| Modify | `src/langrank/plotting/service.py`     | `split_segments()`; insert NaN breaks |
| Modify | `src/langrank/cli.py`                  | `--connect-gaps/--no-connect-gaps` option (default off) |
| Modify | `tests/unit/test_plot_invariants.py`   | Tests below |

## Symbols / fields

| Symbol                         | Kind     | Type / signature | Default | Notes |
|--------------------------------|----------|------------------|---------|-------|
| `PlotOptions.connect_gaps`     | field    | `bool`           | `False` | |
| `split_segments`               | function | `(rows: list[QueryRow]) -> list[list[QueryRow]]` | - | Sorted by `period_start`; splits on `value is None` and on step > `GAP_FACTOR` × modal step |
| `GAP_FACTOR`                   | constant | `float`          | `1.5`   | Documented in docstring |

## Behaviour & validators

1. A row with `value is None` always ends a segment.
2. A step between consecutive rows larger than `GAP_FACTOR` × the series' modal step (in days)
   ends a segment. A series with <3 points has no modal step → only rule 1 applies.
3. Segments are drawn as one `Line2D` per language with `NaN` separators (single legend entry), so
   `get_ydata()` contains `nan` exactly at breaks - never a fabricated value.
4. `--connect-gaps` draws the old continuous line and appends ` (gaps connected)` to the title.
5. Single-point segments are drawn as a marker so isolated observations stay visible.

## Tests

| Test function                                   | File                                 | Type | Asserts |
|-------------------------------------------------|--------------------------------------|------|---------|
| `test_gap_breaks_line_on_missing_period`        | `tests/unit/test_plot_invariants.py` | Unit | Monthly series missing one month → a `nan` in y-data between neighbours |
| `test_none_value_breaks_line`                   | `tests/unit/test_plot_invariants.py` | Unit | `value=None` row → break, no zero |
| `test_regular_annual_series_unbroken`           | `tests/unit/test_plot_invariants.py` | Unit | Contiguous yearly data → no `nan` |
| `test_connect_gaps_opt_in`                      | `tests/unit/test_plot_invariants.py` | Unit | `connect_gaps=True` → no `nan`; title marked |
| `test_isolated_point_visible`                   | `tests/unit/test_plot_invariants.py` | Unit | Single-point segment has a marker |
| `test_split_segments_invariants`                | `tests/unit/test_plot_invariants.py` | Unit | `assert_plot_invariants` holds with gaps present |

## Success criteria

- [ ] Default plots never connect across a missing period.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- No interpolation of stored data; `NaN` separators are rendering-only.

## Out of scope

- Smoothing ([06](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/06-visual-smoothing.md)).

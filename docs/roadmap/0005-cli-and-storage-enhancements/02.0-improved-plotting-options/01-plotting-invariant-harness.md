# Subtask 02.0/01 - Plotting-invariant regression harness

**Task:** [02.0 - Improved Plotting Options](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/README.md) ·
**Role:** Testing Expert · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Make `PlotService` testable without rendering (a pure figure builder) and add one named test per
plotting invariant, so every later flag subtask can re-run the same assertions with its flag on.

## Baseline

- `PlotService.plot` builds, shows/saves, and closes the figure in one method; nothing is returned.
- No plotting tests exist (`grep -rn PlotService tests` is empty).

## Files

| Action | Path                                   | Purpose |
|--------|----------------------------------------|---------|
| Modify | `src/langrank/plotting/service.py`     | Split into `build_figure()` + `plot()` (which calls it, then saves/shows/closes) |
| Create | `tests/unit/test_plot_invariants.py`   | Invariant tests + reusable helpers |

## Symbols / fields

| Symbol                              | Kind     | Type / signature | Default | Notes |
|-------------------------------------|----------|------------------|---------|-------|
| `PlotOptions`                       | dataclass (frozen) | fields: `metric_id: str`, `title: str \| None`, `width: float`, `height: float`, `dpi: int`, `markers: bool`, `invert_rank: bool` | - | Later subtasks add fields; defaults keep existing CLI behaviour |
| `PlotService.build_figure`          | method   | `(rows: list[QueryRow], options: PlotOptions) -> Figure` | - | No I/O, no `plt.show()` |
| `PlotService.plot`                  | method   | `(rows: list[QueryRow], options: PlotOptions, output: Path \| None) -> None` | - | Signature change; update `cli.py:plot` caller |
| `lines_by_label`                    | test helper | `(fig: Figure) -> dict[str, Line2D]` | - | In the test module |
| `assert_plot_invariants`            | test helper | `(fig: Figure, rows: list[QueryRow]) -> None` | - | Reused by subtasks 02-07 |

## Behaviour & validators

1. `build_figure` must not mutate `rows` (invariant: stored/queried data never altered).
2. Every plotted x value equals a `date.fromisoformat(row.period_start)` of an input row
   (truthful dates) - unless a later flag explicitly adds a separately-labelled visual layer.
3. No plotted y value is `0` unless an input row has `value == 0` (missing ≠ zero).
4. `plot()` always closes the figure (no leaked figures across tests - assert
   `plt.get_fignums()` unchanged).

## Tests

| Test function                                  | File                                 | Type | Asserts |
|------------------------------------------------|--------------------------------------|------|---------|
| `test_missing_value_not_rendered_as_zero`      | `tests/unit/test_plot_invariants.py` | Unit | Row with `value=None` produces no point; no y == 0 |
| `test_plotted_dates_match_source_periods`      | `tests/unit/test_plot_invariants.py` | Unit | x-data ⊆ input `period_start` dates |
| `test_build_figure_does_not_mutate_rows`       | `tests/unit/test_plot_invariants.py` | Unit | `copy.deepcopy(rows) == rows` after build |
| `test_no_interpolated_points_added`            | `tests/unit/test_plot_invariants.py` | Unit | Point count per line == count of non-None input rows |
| `test_plot_closes_figure`                      | `tests/unit/test_plot_invariants.py` | Unit | `plt.get_fignums()` unchanged after `plot(..., output=tmp)` |
| `test_rank_axis_inverted_by_default_demo`      | `tests/unit/test_plot_invariants.py` | Unit | `metric_id="rank"` → `ax.yaxis_inverted()` (pins current demo behaviour) |

## Success criteria

- [ ] `PlotService.build_figure` exists and `cli.py:plot` output is unchanged (existing CLI tests pass).
- [ ] All six tests pass under `MPLBACKEND=Agg`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- No new runtime dependency; matplotlib only.
- Plotting invariants: [plan.md § Plotting invariants](/docs/roadmap/0005-cli-and-storage-enhancements/plan.md#plotting-invariants).

## Out of scope

- The bridging-line gap behaviour (subtask [03](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/03-gap-aware-segments.md)).
- The provider-prefixed rank bug (subtask [02](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/02-rank-metric-resolution-fix.md)).

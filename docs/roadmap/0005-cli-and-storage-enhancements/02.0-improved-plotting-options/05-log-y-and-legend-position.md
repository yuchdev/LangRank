# Subtask 02.0/05 - `--log-y` and `--legend-position`

**Task:** [02.0 - Improved Plotting Options](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Two small presentation flags: a logarithmic y-axis for share/percent metrics with a long tail,
and control over legend placement (including outside the axes for many languages).

## Baseline

- `PlotService` calls `ax.legend()` with matplotlib's default placement; linear y only.

## Files

| Action | Path                                   | Purpose |
|--------|----------------------------------------|---------|
| Modify | `src/langrank/plotting/service.py`     | Apply scale and legend placement |
| Modify | `src/langrank/cli.py`                  | `--log-y`, `--legend-position` options |
| Modify | `tests/unit/test_plot_invariants.py`   | Tests below |

## Symbols / fields

| Symbol                          | Kind     | Type / signature | Default | Notes |
|---------------------------------|----------|------------------|---------|-------|
| `LegendPosition`                | StrEnum  | `best`, `upper-left`, `upper-right`, `lower-left`, `lower-right`, `outside-right`, `none` | - | In `plotting/service.py` |
| `PlotOptions.log_y`             | field    | `bool`           | `False` | |
| `PlotOptions.legend_position`   | field    | `LegendPosition` | `LegendPosition.BEST` | |

## Behaviour & validators

1. `--log-y` on a rank metric (`rank_metric=True`) is rejected with `LangRankError` - log ranks are
   misleading and conflict with inversion.
2. `--log-y` when any plotted value ≤ 0 raises `LangRankError` naming the offending language/period;
   values are never dropped or clamped silently.
3. `outside-right` places the legend at `bbox_to_anchor=(1.02, 1)` and uses `bbox_inches="tight"`
   on save; `none` draws no legend.
4. Invalid `--legend-position` values fail Typer's enum validation (exit 2).

## Tests

| Test function                               | File                                 | Type | Asserts |
|---------------------------------------------|--------------------------------------|------|---------|
| `test_log_y_sets_log_scale`                 | `tests/unit/test_plot_invariants.py` | Unit | `ax.get_yscale() == "log"`; invariants hold |
| `test_log_y_rejects_rank_metric`            | `tests/unit/test_plot_invariants.py` | Unit | `LangRankError` |
| `test_log_y_rejects_non_positive_values`    | `tests/unit/test_plot_invariants.py` | Unit | Value 0 → `LangRankError`, message names language |
| `test_legend_position_outside_right`        | `tests/unit/test_plot_invariants.py` | Unit | Legend anchor outside axes |
| `test_legend_position_none`                 | `tests/unit/test_plot_invariants.py` | Unit | `ax.get_legend() is None` |

## Success criteria

- [ ] Both flags documented in `langrank plot --help`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Plotting invariants hold with each flag active.

## Out of scope

- Theme/style configuration.

# Subtask 02.0/07 - `--facet` (one panel per language)

**Task:** [02.0 - Improved Plotting Options](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/README.md) ·
**Role:** Python Expert · **Depends on:** 01, 03 · **Status:** ⬜ Not started

## Goal

Render one small-multiple panel per language (same rating, same metric, shared x-axis) so many
languages stay legible without a spaghetti chart.

## Baseline

- `PlotService.build_figure` (subtask 01) creates a single `Axes`.

## Files

| Action | Path                                   | Purpose |
|--------|----------------------------------------|---------|
| Modify | `src/langrank/plotting/service.py`     | Grid layout when faceting |
| Modify | `src/langrank/cli.py`                  | `--facet` flag, `--facet-cols` option |
| Modify | `tests/unit/test_plot_invariants.py`   | Tests below |

## Symbols / fields

| Symbol                   | Kind  | Type            | Default | Notes |
|--------------------------|-------|-----------------|---------|-------|
| `PlotOptions.facet`      | field | `bool`          | `False` | |
| `PlotOptions.facet_cols` | field | `int`           | `3`     | Must be ≥1 |

## Behaviour & validators

1. Facets are by **language only**; the command stays single-rating, so no panel ever mixes ratings.
2. Panels share x (`sharex=True`); y is shared only for rank metrics (same scale meaning), each
   rank panel is inverted per subtask 02 rules.
3. Panel title = language display name; empty trailing grid cells are hidden (`ax.set_visible(False)`).
4. Gap splitting, smoothing, methodology markers and log-y apply per panel.
5. `--facet` with a single language behaves like the non-faceted plot (one panel).

## Tests

| Test function                                | File                                 | Type | Asserts |
|----------------------------------------------|--------------------------------------|------|---------|
| `test_facet_creates_one_panel_per_language`  | `tests/unit/test_plot_invariants.py` | Unit | 4 languages, `facet_cols=3` → 4 visible axes, 2 rows |
| `test_facet_rank_panels_inverted`            | `tests/unit/test_plot_invariants.py` | Unit | Every visible axes `yaxis_inverted()` for a rank metric |
| `test_facet_keeps_invariants_per_panel`      | `tests/unit/test_plot_invariants.py` | Unit | `assert_plot_invariants` per axes |

## Success criteria

- [ ] `langrank plot --rating tiobe --metric rank --top 8 --facet --output f.png` writes a grid.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Never facet by rating in `plot` (cross-rating belongs to Milestone 0002 `plot compare`).

## Out of scope

- Faceting by metric.

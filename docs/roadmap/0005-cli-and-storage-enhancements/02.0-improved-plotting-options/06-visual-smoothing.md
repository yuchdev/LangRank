# Subtask 02.0/06 - `--smooth` (visual only)

**Task:** [02.0 - Improved Plotting Options](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/README.md) ·
**Role:** Python Expert · **Depends on:** 01, 03 · **Status:** ⬜ Not started

## Goal

Offer an opt-in trailing moving average to make noisy monthly series (TIOBE, PYPL) readable,
drawn as a clearly-labelled visual layer on top of the untouched raw points - never stored,
exported, or presented as source data.

## Baseline

- No smoothing exists; subtask 03 provides `split_segments`.

## Files

| Action | Path                                   | Purpose |
|--------|----------------------------------------|---------|
| Modify | `src/langrank/plotting/service.py`     | `trailing_mean()`; smoothed layer |
| Modify | `src/langrank/cli.py`                  | `--smooth N` option |
| Modify | `tests/unit/test_plot_invariants.py`   | Tests below |

## Symbols / fields

| Symbol                     | Kind     | Type / signature | Default | Notes |
|----------------------------|----------|------------------|---------|-------|
| `PlotOptions.smooth_window` | field   | `int \| None`    | `None`  | `None`/`1` = off; must be ≥2 when set |
| `trailing_mean`            | function | `(values: Sequence[float], window: int) -> list[float]` | - | `nan` for the first `window-1` positions (no look-ahead, no edge padding) |

## Behaviour & validators

1. Smoothing is computed **per segment** from `split_segments` - never across a gap.
2. The raw series is still drawn (markers, reduced alpha); the smoothed line has label
   `"<language> (smoothed N, visual only)"` and `gid="smoothed"`.
3. Title gets suffix `" - smoothed (visual only)"`.
4. `--smooth` never affects `query`/`export` output or the DB; `PlotService` has no DB handle.
5. `--smooth 1` or `0` → `typer.BadParameter`.

## Tests

| Test function                                   | File                                 | Type | Asserts |
|-------------------------------------------------|--------------------------------------|------|---------|
| `test_trailing_mean_known_values`               | `tests/unit/test_plot_invariants.py` | Unit | `[1,2,3,4], 2 → [nan,1.5,2.5,3.5]` |
| `test_smoothing_does_not_cross_gaps`            | `tests/unit/test_plot_invariants.py` | Unit | Window restarts after a gap (leading `nan`s) |
| `test_smoothing_keeps_raw_series`               | `tests/unit/test_plot_invariants.py` | Unit | Raw line's data equals input values; invariants hold on the raw line |
| `test_smoothed_layer_labelled_visual_only`      | `tests/unit/test_plot_invariants.py` | Unit | Legend label and title contain "visual only" |
| `test_smoothing_does_not_mutate_rows`           | `tests/unit/test_plot_invariants.py` | Unit | Input rows unchanged |

## Success criteria

- [ ] Smoothed output is always visibly distinguishable from raw data.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Derived values are never presented as raw ([CLAUDE.md](/CLAUDE.md)); not persisted.
- No pandas/numpy dependency beyond what matplotlib already brings (use stdlib or numpy via
  matplotlib only if already importable - prefer stdlib).

## Out of scope

- Other smoothing kernels (LOESS, EWMA).

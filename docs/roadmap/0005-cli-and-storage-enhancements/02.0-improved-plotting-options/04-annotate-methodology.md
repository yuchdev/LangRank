# Subtask 02.0/04 - `--annotate-methodology`

**Task:** [02.0 - Improved Plotting Options](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Draw a labelled vertical marker at each methodology boundary that falls inside the plotted date
range, so a reader never mistakes a methodology break for a real trend change.

## Baseline

- `methodology_notes` table (migration 2) and `Database.list_methodology_notes(rating_id) ->
  list[MethodologyNote]` already exist; providers populate them via `upsert_provider_metadata`.
- [Milestone 0003 Task 01.0](/docs/roadmap/0003-historical-data-quality/plan.md#task-010---methodology-break-tracking)
  may rename/extend this storage (`rating_methodologies`); this subtask depends only on the
  `MethodologyNote` dataclass, fetched through one `Database` method, so a rename is a one-line
  change.

## Files

| Action | Path                                   | Purpose |
|--------|----------------------------------------|---------|
| Modify | `src/langrank/plotting/service.py`     | Draw `axvline` + text per boundary |
| Modify | `src/langrank/cli.py`                  | `--annotate-methodology` flag; fetch notes for `--rating` |
| Modify | `tests/unit/test_plot_invariants.py`   | Tests below |

## Symbols / fields

| Symbol                                 | Kind     | Type / signature | Default | Notes |
|----------------------------------------|----------|------------------|---------|-------|
| `PlotOptions.methodology_notes`        | field    | `tuple[MethodologyNote, ...]` | `()` | Empty = flag off |
| `methodology_boundaries`               | function | `(notes: Sequence[MethodologyNote], start: date, end: date) -> list[tuple[date, str]]` | - | Returns `(valid_from, methodology_version)` inside `(start, end]` |

## Behaviour & validators

1. A boundary is each note's `valid_from` that lies strictly after the first plotted date and on or
   before the last. Notes with `valid_from is None` are skipped.
2. Markers are drawn with a distinct `gid="methodology-boundary"` so tests can find them; label text
   is the `methodology_version`.
3. The flag never changes line data (invariants hold).
4. `--annotate-methodology` without `--rating` is a usage error (`typer.BadParameter`).
5. If no boundary falls in range, print a one-line note (`console`), not an error.

## Tests

| Test function                                    | File                                 | Type | Asserts |
|--------------------------------------------------|--------------------------------------|------|---------|
| `test_methodology_boundary_drawn_in_range`       | `tests/unit/test_plot_invariants.py` | Unit | One `Line2D` with `gid="methodology-boundary"` at the note's date |
| `test_methodology_boundary_outside_range_skipped` | `tests/unit/test_plot_invariants.py` | Unit | Note before range → no marker |
| `test_methodology_annotation_keeps_invariants`   | `tests/unit/test_plot_invariants.py` | Unit | `assert_plot_invariants` passes with notes |
| `test_annotate_methodology_requires_rating`      | `tests/integration/test_cli.py`      | Integration | Exit code 2 without `--rating` |

## Success criteria

- [ ] `langrank plot --rating tiobe --metric rating --languages python --annotate-methodology` draws the provider's documented boundaries within range.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Records breaks only; never adjusts values across them (Milestone 0003 "no silent correction").

## Out of scope

- Authoring methodology history for providers (Milestone 0003 Task 01.0).

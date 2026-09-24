# Subtask 03.0/01 - `ReportService` skeleton and output layout

**Task:** [03.0 - Multi-Chart Report Generation](/docs/roadmap/0005-cli-and-storage-enhancements/03.0-multi-chart-report/README.md) ·
**Role:** Python Expert · **Depends on:** - · **Status:** ⬜ Not started

## Goal

Create the report service, its request/result types, and the fixed output directory layout that
later subtasks fill in.

## Baseline

- No `services/report.py`. Services take a `Database` in `__init__` (see `QueryService`).

## Files

| Action | Path                                 | Purpose |
|--------|--------------------------------------|---------|
| Create | `src/langrank/services/report.py`    | `ReportRequest`, `ReportResult`, `ReportService` |
| Create | `tests/unit/test_report_service.py`  | Tests below |

## Symbols / fields

| Symbol                        | Kind     | Type / signature | Default | Notes |
|-------------------------------|----------|------------------|---------|-------|
| `ReportRequest`               | frozen dataclass | fields below | - | |
| `ReportRequest.language_ids`  | field    | `tuple[str, ...]` | -      | Already resolved canonical IDs |
| `ReportRequest.rating_ids`    | field    | `tuple[str, ...]` | `()`   | Empty = every rating with data |
| `ReportRequest.years`         | field    | `int \| None`     | `None` | |
| `ReportRequest.since` / `until` | field  | `date \| None`    | `None` | |
| `ReportRequest.output_dir`    | field    | `Path`            | -      | |
| `ReportRequest.force`         | field    | `bool`            | `False` | Allow non-empty output dir |
| `ReportResult`                | frozen dataclass | `output_dir: Path`, `files: tuple[Path, ...]`, `skipped_ratings: tuple[str, ...]` | - | |
| `ReportService.__init__`      | method   | `(database: Database, registry: ProviderRegistry, plot_service: PlotService) -> None` | - | |
| `ReportService.generate`      | method   | `(request: ReportRequest) -> ReportResult` | - | Orchestrates subtasks 02-04 |
| `REPORT_LAYOUT`               | constant | `dict[str, str]` | - | `charts/`, `data/observations.csv`, `data/coverage.csv`, `data/latest_ranks.csv`, `README.md`, `report.json` |

## Behaviour & validators

1. Non-empty `output_dir` without `force` raises `LangRankError` (never overwrite silently).
2. `force=True` only overwrites files named in `REPORT_LAYOUT`/`charts/*.png`; unrelated files are
   left in place.
3. `language_ids` empty → `LangRankError` ("report requires --languages").
4. `generate` returns every written path in `files`, sorted.

## Tests

| Test function                                      | File                                | Type | Asserts |
|----------------------------------------------------|-------------------------------------|------|---------|
| `test_report_refuses_non_empty_output_dir`         | `tests/unit/test_report_service.py` | Unit | `LangRankError` |
| `test_report_force_preserves_unrelated_files`      | `tests/unit/test_report_service.py` | Unit | Foreign file survives |
| `test_report_requires_languages`                   | `tests/unit/test_report_service.py` | Unit | `LangRankError` |
| `test_report_creates_layout_directories`           | `tests/unit/test_report_service.py` | Unit | `charts/`, `data/` created |

## Success criteria

- [ ] `ReportService` importable, typed, mypy-clean.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Service layer owns logic; no Typer/rich imports in `services/report.py`.

## Out of scope

- Chart/table/summary content (subtasks 02-04); CLI wiring (05).

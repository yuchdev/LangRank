# Subtask 05.0/01 - Selection window model and resolver

**Task:** [05.0 - Historical Selection Semantics](/docs/roadmap/0005-cli-and-storage-enhancements/05.0-historical-selection-semantics/README.md) ·
**Role:** Python Expert · **Depends on:** - · **Status:** ⬜ Not started

## Goal

One pure function that turns `(years, since, until, year, policy)` plus the latest available
period(s) into a concrete date window per rating - the single source of truth for `--years`.

## Baseline

- `Database.resolve_year_bounds(rating_id) -> tuple[int | None, int | None]` (years only).

## Files

| Action | Path                                   | Purpose |
|--------|----------------------------------------|---------|
| Create | `src/langrank/services/selection.py`   | `EndpointPolicy`, `SelectionWindow`, `resolve_window`, `subtract_years` |
| Modify | `src/langrank/db/repository.py`        | `latest_period_start(rating_id, metric_id=None) -> date \| None` |
| Create | `tests/unit/test_selection_window.py`  | Tests below |

## Symbols / fields

| Symbol                         | Kind     | Type / signature | Default | Notes |
|--------------------------------|----------|------------------|---------|-------|
| `EndpointPolicy`               | StrEnum  | `PER_SOURCE="per-source"`, `GLOBAL="global"`, `EXPLICIT="explicit"` | - | |
| `SelectionWindow`              | frozen dataclass | `rating_id: str \| None`, `since: date \| None`, `until: date \| None`, `since_exclusive: bool`, `endpoint: date \| None`, `policy: EndpointPolicy`, `years: int \| None` | - | `since_exclusive=True` for `--years` windows |
| `subtract_years`               | function | `(value: date, years: int) -> date` | - | Feb 29 → Feb 28 |
| `resolve_window`               | function | `(*, rating_ids: Sequence[str \| None], latest: Mapping[str \| None, date \| None], years: int \| None, since: date \| None, until: date \| None, year: int \| None, policy: EndpointPolicy) -> dict[str \| None, SelectionWindow]` | - | Pure; no DB |
| `Database.latest_period_start` | method   | `(rating_id: str \| None, metric_id: str \| None = None) -> date \| None` | - | `MAX(period_start)` with optional filters |

## Behaviour & validators

1. `years` given, `until` not: per rating `E = latest[rating]` (`PER_SOURCE`) or
   `max(latest.values())` (`GLOBAL`); `since = subtract_years(E, years)` exclusive; `until = None`
   (upper bound is naturally `E`).
2. `until` given: policy becomes `EXPLICIT`, `E = until`, `since = subtract_years(until, years)`
   exclusive when `years` is set.
3. `year` given: `since = date(year,1,1)` inclusive, `until = date(year,12,31)`; `year` together with
   `years` → `LangRankError` (no silent precedence).
4. `since` and `years` both given → `LangRankError("--since and --years are mutually exclusive")`.
5. `latest[rating] is None` (no data) → window with `endpoint=None`, `since=None`, `until=None` and
   the caller returns no rows for it (no fabricated range).
6. `years <= 0` → `LangRankError`.

## Tests

| Test function                                   | File                                  | Type | Asserts |
|-------------------------------------------------|---------------------------------------|------|---------|
| `test_subtract_years_leap_day`                  | `tests/unit/test_selection_window.py` | Unit | 2024-02-29 − 1 → 2023-02-28 |
| `test_years_annual_yields_n_editions`           | `tests/unit/test_selection_window.py` | Unit | E=2025-01-01, N=10 → since 2015-01-01 exclusive |
| `test_years_monthly_counts_months_not_calendar_years` | `tests/unit/test_selection_window.py` | Unit | E=2025-03-01, N=1 → since 2024-03-01 exclusive |
| `test_per_source_uses_each_latest`              | `tests/unit/test_selection_window.py` | Unit | Two ratings with different E → different windows |
| `test_global_uses_max_latest`                   | `tests/unit/test_selection_window.py` | Unit | Same E for all |
| `test_until_forces_explicit_policy`             | `tests/unit/test_selection_window.py` | Unit | policy `EXPLICIT`, E = until |
| `test_since_and_years_mutually_exclusive`       | `tests/unit/test_selection_window.py` | Unit | `LangRankError` |
| `test_year_and_years_mutually_exclusive`        | `tests/unit/test_selection_window.py` | Unit | `LangRankError` |
| `test_no_data_rating_has_empty_window`          | `tests/unit/test_selection_window.py` | Unit | `endpoint is None` |
| `test_latest_period_start_by_metric`            | `tests/unit/test_selection_window.py` | Unit | Metric filter respected |

## Success criteria

- [ ] `resolve_window` is pure and fully unit-tested.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- No interpolation/padding of windows; missing data stays missing.

## Out of scope

- Using the resolver (subtask 02).

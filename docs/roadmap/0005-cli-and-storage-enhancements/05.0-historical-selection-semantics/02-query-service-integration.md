# Subtask 05.0/02 - Wire the resolver into `QueryService`

**Task:** [05.0 - Historical Selection Semantics](/docs/roadmap/0005-cli-and-storage-enhancements/05.0-historical-selection-semantics/README.md) ·
**Role:** Python Expert · **Depends on:** 01 · **Status:** ⬜ Not started

## Goal

Replace the calendar-year logic in `QueryService.resolve_filters` with `resolve_window`, add a
multi-rating query entry point, and support the exclusive lower bound in `Database.query_rows`.

## Baseline

- `resolve_filters` uses `resolve_year_bounds`; `QueryFilters` has no policy field;
  `query_rows` uses `period_start >= since`.

## Files

| Action | Path                               | Purpose |
|--------|------------------------------------|---------|
| Modify | `src/langrank/models.py`           | `QueryFilters.endpoint_policy`, `QueryFilters.since_exclusive` |
| Modify | `src/langrank/services/query.py`   | Use `resolve_window`; add `query_many`; expose resolved windows |
| Modify | `src/langrank/db/repository.py`    | `query_rows` honours `since_exclusive` (`>` vs `>=`) |
| Modify | `tests/unit/test_query_service.py` | Tests below |

## Symbols / fields

| Symbol                               | Kind   | Type / signature | Default | Notes |
|--------------------------------------|--------|------------------|---------|-------|
| `QueryFilters.endpoint_policy`       | field  | `EndpointPolicy` | `EndpointPolicy.PER_SOURCE` | Import from `services.selection` would invert layering - define `EndpointPolicy` in `models.py` and re-export from `services/selection.py` |
| `QueryFilters.since_exclusive`       | field  | `bool`           | `False` | |
| `ResolvedFilters.window`             | field  | `SelectionWindow` | -      | Recorded for sidecars/reports |
| `QueryService.query_many`            | method | `(rating_ids: Sequence[str], filters: QueryFilters) -> tuple[list[QueryRow], dict[str, SelectionWindow]]` | - | Applies policy across ratings |

## Behaviour & validators

1. `resolve_filters` computes the endpoint with `Database.latest_period_start(rating_id, metric_id)`
   - metric-aware, so `pypl-share` and `pypl-rank` can differ if one lags.
2. `query_many` with `GLOBAL` computes one endpoint over all `rating_ids` first.
3. `Database.resolve_year_bounds` is no longer used by `QueryService` (keep method if other callers
   exist; otherwise remove with its tests).
4. Top filters (`--top`, `--top-current`) run inside the resolved window.
5. `dataclasses.replace` replaces the three hand-copied `QueryFilters(...)` constructions.

## Tests

| Test function                                         | File                               | Type | Asserts |
|-------------------------------------------------------|------------------------------------|------|---------|
| `test_years_window_endpoint_is_latest_observation`    | `tests/unit/test_query_service.py` | Unit | Monthly data ending 2025-03, `years=1` → 12 months returned |
| `test_years_window_is_metric_aware`                   | `tests/unit/test_query_service.py` | Unit | Lagging metric gets its own endpoint |
| `test_query_many_per_source_windows`                  | `tests/unit/test_query_service.py` | Unit | Two ratings, different endpoints |
| `test_query_many_global_window`                       | `tests/unit/test_query_service.py` | Unit | Single shared endpoint |
| `test_since_exclusive_lower_bound`                    | `tests/unit/test_query_service.py` | Unit | Row exactly at `E − N` excluded |
| `test_top_current_filters_latest_snapshot`            | `tests/unit/test_query_service.py` | Unit | Existing test still passes |

## Success criteria

- [ ] No calendar-year arithmetic remains in `QueryService`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Business logic in services; `Database` remains the only SQL site.

## Out of scope

- CLI flags (subtask 03).

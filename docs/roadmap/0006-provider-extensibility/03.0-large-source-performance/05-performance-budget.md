# Subtask 03.0/05 - Performance Budget & Regression Gate

**Task:** [03.0 - Large-Source Performance Hardening](/docs/roadmap/0006-provider-extensibility/03.0-large-source-performance/README.md) ·
**Role:** Testing Expert · **Depends on:** 02, 03, 04 · **Status:** ⬜ Not started

## Goal

Turn the benchmark harness into an enforced, documented budget: explicit time and memory
ceilings per stage at the largest known source size, asserted by the benchmark tests and run
on a schedule/manual trigger in CI (not on every push).

## Baseline

- Harness + baseline numbers in `docs/dev/performance.md` ([subtask 01](/docs/roadmap/0006-provider-extensibility/03.0-large-source-performance/01-benchmark-fixture-harness.md)).
- `.github/workflows/ci.yml` runs ruff, ruff format, mypy, pytest on 3.12/3.13.

## Files

| Action | Path                                           | Purpose |
|--------|------------------------------------------------|---------|
| Modify | `tests/benchmarks/test_pipeline_benchmark.py`  | Budget assertions |
| Create | `tests/benchmarks/budget.toml`                 | Budget numbers (single source of truth) |
| Modify | `docs/dev/performance.md`                      | Budget table, before/after results, how to update the budget |
| Create | `.github/workflows/benchmark.yml`              | `workflow_dispatch` + weekly `schedule`; runs `uv run pytest -m benchmark` on 3.12 |

## Symbols / fields

| Symbol            | Kind     | Type / signature                                          | Default | Notes |
|-------------------|----------|-----------------------------------------------------------|---------|-------|
| `load_budget`     | function | `(path: Path) -> dict[str, StageBudget]`                  | -       | `tomllib`; in `tests/benchmarks/conftest.py` |
| `StageBudget`     | dataclass | frozen: `max_seconds: float`, `max_peak_mib: float`      | -       | |

Initial budget (confirm/adjust from measured results, then freeze):

| Stage (shape)                     | max_seconds | max_peak_mib |
|-----------------------------------|-------------|--------------|
| `parse` (survey, 90k rows)        | 5           | 150          |
| `upsert` (monthly ×scale, 200k obs)| 10         | 300          |
| `reupsert_unchanged` (200k obs)   | 5           | 300          |
| `download` (200 MiB mocked)       | 10          | 32           |

## Behaviour & validators

1. Each benchmark asserts `seconds <= max_seconds * tolerance` and `peak_mib <= max_peak_mib`,
   where `tolerance = float(os.environ.get("LANGRANK_BENCH_TOLERANCE", "1.5"))` to absorb runner noise.
2. A failing budget prints measured vs. budget per stage.
3. Changing `budget.toml` requires updating the table in `docs/dev/performance.md` (enforced by a
   unit test comparing the two).
4. The workflow never runs on `pull_request` by default (keeps CI fast and deterministic).

## Tests

| Test function                                | File                                          | Type | Asserts |
|----------------------------------------------|-----------------------------------------------|------|---------|
| `test_budget_toml_matches_performance_doc`   | `tests/unit/test_benchmark_budget.py`         | Unit | Budget numbers identical in TOML and doc table |
| `test_benchmark_*` (from subtask 01)         | `tests/benchmarks/test_pipeline_benchmark.py` | Integration (`benchmark`) | Now with budget assertions |

## Success criteria

- [ ] `uv run pytest -m benchmark` passes locally within budget; workflow run green once.
- [ ] `docs/dev/performance.md` shows baseline vs. optimised numbers per stage.
- [ ] Milestone exit: no new runtime dependency (`git diff pyproject.toml` touches only markers/dev config).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Budgets are about orders of magnitude, not micro-benchmarks - no `pytest-benchmark` dependency needed.

## Out of scope

- DuckDB analytical export path (plan.md: only if workloads justify it; would be a new task).

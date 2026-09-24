# Subtask 03.0/01 - Quality-check framework & `QualityService`

**Task:** [03.0 - Data Quality Dashboard](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/README.md) ·
**Role:** Python Expert · **Depends on:** - · **Status:** ⬜ Not started


> **Coordination - one rank-metric helper.** Three subtasks touch "which metrics are ranks":
> [0005 02.0/02](/docs/roadmap/0005-cli-and-storage-enhancements/02.0-improved-plotting-options/02-rank-metric-resolution-fix.md),
> [0003 03.0/01](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/01-quality-framework.md) and
> [0006 01.0/02](/docs/roadmap/0006-provider-extensibility/01.0-provider-capabilities-metadata/02-metric-role-lookups.md).
> There is exactly one helper, `Database.rank_metric_ids() -> set[str]`. Whichever of the first
> two lands first creates it (interim rule: `metrics.unit = 'rank' AND higher_is_better = 0`);
> the other reuses it. 0006 01.0/02 then re-implements its body on `metrics.kind = 'rank'`
> without changing callers. No other module may compare a metric ID with `"rank"`.

## Goal

Provide the check registry, finding/report types, read-only DB access, and the service that
runs a selected set of checks.

## Baseline

- `models.Severity` has `WARNING`, `ERROR`. `ValidationReport` exists but carries no row pointers.
- `Database.connect()` opens a read-write connection.

## Files

| Action | Path                                   | Purpose |
|--------|----------------------------------------|---------|
| Modify | `src/langrank/models.py`               | `Severity.INFO`; `QualityFinding`; `QualityReport` |
| Create | `src/langrank/services/quality.py`     | `QualityCheckSpec`, `CHECKS`, `QualityService` |
| Modify | `src/langrank/db/repository.py`        | `connect_readonly()`; `rank_metric_ids()` |
| Create | `tests/unit/test_quality_service.py`   | Framework tests |

## Symbols / fields

| Symbol                         | Kind      | Type / signature                                                                                              | Default | Notes |
|--------------------------------|-----------|---------------------------------------------------------------------------------------------------------------|---------|-------|
| `Severity.INFO`                | enum      | `"info"`                                                                                                      | -       | `ValidationReport.ok` unaffected |
| `QualityFinding`               | dataclass | frozen: `code: str`, `severity: Severity`, `rating_id: str \| None`, `metric_id: str \| None`, `language_id: str \| None`, `period_start: date \| None`, `message: str`, `detail: dict[str, Any]` | `detail={}` | |
| `QualityReport`                | dataclass | `findings: list[QualityFinding]`; `counts_by_code() -> dict[str, int]`; `max_severity() -> Severity \| None`; `to_dict() -> dict[str, Any]` | - | |
| `QualityCheckSpec`             | dataclass | frozen: `code: str`, `severity: Severity`, `description: str`, `run: Callable[[QualityContext], list[QualityFinding]]` | - | |
| `QualityContext`               | dataclass | frozen: `database: Database`, `rating_id: str \| None`, `thresholds: Mapping[str, float]`                      | - | |
| `CHECKS`                       | const     | `dict[str, QualityCheckSpec]`                                                                                 | -       | populated by subtasks 03-05 |
| `QualityService.run`           | method    | `(*, codes: Sequence[str] \| None = None, rating_id: str \| None = None, thresholds: Mapping[str, float] \| None = None) -> QualityReport` | - | |
| `Database.connect_readonly`    | method    | `() -> contextmanager[sqlite3.Connection]` (`mode=ro` URI)                                                    | -       | |
| `Database.rank_metric_ids`     | method    | `() -> set[str]` — metrics with `unit = 'rank'`                                                               | -       | interim; replaced by 0006 Task 01.0 metric roles |

## Behaviour & validators

1. Unknown code in `codes` → `ValidationError("unknown quality check: ...")`.
2. Findings sorted by (severity desc, code, rating_id, metric_id, language_id, period_start).
3. A check raising an exception yields one ERROR finding `check_failed` with the check code in `detail`; other checks still run.
4. `Database.quality_*` methods (added later) must use `connect_readonly()`.

## Tests

| Test function                                  | File                                 | Type        | Asserts |
|------------------------------------------------|--------------------------------------|-------------|---------|
| `test_run_unknown_code_raises`                 | `tests/unit/test_quality_service.py` | Unit        | `ValidationError` |
| `test_findings_sorted_by_severity_then_code`   | `tests/unit/test_quality_service.py` | Unit        | with stub checks |
| `test_failing_check_reported_as_check_failed`  | `tests/unit/test_quality_service.py` | Unit        | stub raising check |
| `test_connect_readonly_rejects_writes`         | `tests/unit/test_quality_service.py` | Integration | `sqlite3.OperationalError` on INSERT |
| `test_rank_metric_ids_matches_provider_metrics`| `tests/unit/test_quality_service.py` | Integration | includes `tiobe-rank` after tiobe fetch |

## Success criteria

- [ ] All five tests pass.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- SQL only in `Database`; `services/quality.py` contains no SQL strings.

## Out of scope

- Individual checks (subtasks 03-05); CLI ([subtask 06](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/06-quality-cli.md)).

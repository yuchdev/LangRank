# Task 03.0 - Data Quality Dashboard

**Milestone:** [0003 - Historical Data Quality](/docs/roadmap/0003-historical-data-quality/plan.md) ·
**Spec source:** [plan.md § Task 03.0](/docs/roadmap/0003-historical-data-quality/plan.md#task-030---data-quality-dashboard) ·
**Category:** data-quality · **Status:** ⬜ Not started

## Subtasks

| #  | Subtask                                                                                                                                         | Role           | Depends on | Status         |
|----|-------------------------------------------------------------------------------------------------------------------------------------------------|----------------|------------|----------------|
| 01 | [Quality-check framework & `QualityService`](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/01-quality-framework.md)                        | Python Expert  | -          | ⬜ Not started |
| 02 | [Seeded-anomaly fixture builder](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/02-seeded-anomaly-fixture.md)                               | Testing Expert | 01         | ⬜ Not started |
| 03 | [Structural checks (gaps, duplicates, unmapped names)](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/03-structural-checks.md)              | Python Expert  | 02         | ⬜ Not started |
| 04 | [Value checks (discontinuities, suspicious percentages)](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/04-value-checks.md)                | Python Expert  | 02         | ⬜ Not started |
| 05 | [Temporal & provenance checks](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/05-temporal-and-provenance-checks.md)                        | Python Expert  | 02         | ⬜ Not started |
| 06 | [`langrank quality` command](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/06-quality-cli.md)                                             | Python Expert  | 03, 04, 05 | ⬜ Not started |
| 07 | [Document the quality checks](/docs/roadmap/0003-historical-data-quality/03.0-data-quality-dashboard/07-docs.md)                                                   | Docs Writer    | 06         | ⬜ Not started |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Goal

`langrank quality` reports every anomaly class as a flag pointing at the affected rows, in
table or JSON form, and never edits or deletes data.

## Baseline (what already exists)

- `Database.validation_queries()` runs 8 SQL checks (duplicates, invalid ranks, impossible
  dates, duplicate aliases, unknown languages, malformed units, missing provider metadata,
  percentage range); `ValidationService.validate()` maps all to ERROR; `langrank validate
  [--strict]` prints them. These are *integrity* checks; the dashboard adds *plausibility*
  checks and keeps `validate` unchanged.
- `StatusService.statuses()` computes `provider_state` (`current`/`stale`/`ready`/`unknown`)
  from the hard-coded `upstream_latest_period()` — usable by the stale-provider check now,
  replaced by real freshness in [Milestone 0004 Task 01.0](/docs/roadmap/0004-freshness-and-releases/plan.md#task-010---source-freshness-monitoring--scheduled-updates) (soft dependency).
- **Known defect, not fixed here:** `invalid_ranks` (and `QueryService._apply_top_filters`,
  `PlotService` rank inversion) compare `metric_id = 'rank'`, which matches only `demo`
  (production metrics are `tiobe-rank`, `pypl-rank`, …). The fix — metric-role metadata — is
  owned by [Milestone 0006 Task 01.0](/docs/roadmap/0006-provider-extensibility/plan.md#task-010---provider-capabilities-metadata).
  Until then, rank-based checks here identify rank metrics with the interim helper
  `Database.rank_metric_ids()` (`unit = 'rank'` in `metrics`), which 0006 replaces.

## Design notes

- **Checks are data, not code paths in the CLI.** Each check is a `QualityCheckSpec`
  (code, severity, description, runner) in a registry in `services/quality.py`; SQL lives in
  `Database.quality_*` methods.
- **Read-only by construction.** Quality `Database` methods use a read-only connection
  (`sqlite3.connect("file:...?mode=ro", uri=True)`) — enforced by a test that hashes the DB
  file before/after a run.
- **Every finding points at rows:** `rating_id`, `metric_id`, `language_id`, `period_start`
  (as applicable) plus a `detail` dict.
- **Severity:** adds `Severity.INFO` for informational flags (methodology crossings).
  `langrank quality --strict` fails on WARNING or ERROR; INFO never fails.

### Check catalog

| Code                              | Severity | Subtask | Database method                         |
|-----------------------------------|----------|---------|-----------------------------------------|
| `missing_periods`                 | WARNING  | 03      | `quality_missing_periods()`             |
| `source_gaps`                     | WARNING  | 03      | `quality_source_gaps()`                 |
| `duplicate_ranks`                 | WARNING  | 03      | `quality_duplicate_ranks()`             |
| `unmapped_source_names`           | WARNING  | 03      | `quality_unmapped_source_names()`       |
| `abrupt_discontinuities`          | WARNING  | 04      | `quality_series()` + Python threshold   |
| `suspicious_percentages`          | WARNING  | 04      | `quality_share_sums()`                  |
| `latest_source_mismatch`          | WARNING  | 05      | `quality_latest_by_metric()`            |
| `stale_providers`                 | WARNING  | 05      | via `StatusService`                     |
| `methodology_boundary_crossings`  | INFO     | 05      | via `ValidationService.methodology_breaks` |
| `methodology_orphan_note`         | WARNING  | 05      | `quality_orphan_methodology_notes()`    |
| `observation_before_introduction` | WARNING  | 05      | reuses Task 02.0/05 query               |

### Open questions

- Thresholds for discontinuities? *Default: rank jump ≥ 10 positions between consecutive
  periods, or relative value change ≥ 50 %; module constants, overridable via
  `--threshold code=value`.*

## Task exit criteria

- [ ] Every subtask above is ✅.
- [ ] Each check fires on the seeded fixture and is silent on the clean demo dataset.
- [ ] Running `langrank quality` leaves the DB byte-identical (plan.md criterion).
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## References

- [Task 01.0](/docs/roadmap/0003-historical-data-quality/01.0-methodology-break-tracking/README.md), [Task 02.0](/docs/roadmap/0003-historical-data-quality/02.0-language-lifecycle-and-alias-validity/README.md)

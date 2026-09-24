# Subtask 01.0/06 - UpdateService Pipeline

**Task:** [01.0 - Source Freshness Monitoring & Scheduled Updates](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/README.md) ·
**Role:** Python Expert · **Depends on:** 04, 05 · **Status:** ⬜ Not started

## Goal

Orchestrate the plan's five update steps - check freshness, fetch only stale providers,
validate, report methodology changes, summarize - as an idempotent service that reuses
`FetchService` rather than duplicating the pipeline.

## Baseline

- `services/fetch.py:FetchService.fetch(provider, request) -> FetchSummary` runs the full
  pipeline and records `fetch_runs`.
- `Database.list_methodology_notes(rating_id)` and `Database.last_fetch_run(rating_id)` exist.
- `ProviderMetadata.methodology_notes` is upserted by `upsert_provider_metadata`.

## Files

| Action | Path | Purpose |
|---|---|---|
| Create | `src/langrank/services/update.py` | `UpdateRequest`, `ProviderUpdateResult`, `UpdateSummary`, `UpdateService` |
| Create | `tests/unit/test_update_service.py` | Service tests with fake providers |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|---|---|---|---|---|
| `UpdateAction` | StrEnum | `FETCHED`, `SKIPPED_FRESH`, `SKIPPED_UNKNOWN`, `SKIPPED_POLICY`, `SKIPPED_INTERVAL`, `DRY_RUN`, `FAILED` | - | |
| `UpdateRequest` | frozen dataclass | `provider_ids: list[str]`, `scheduled: bool`, `online: bool`, `include_unknown: bool`, `dry_run: bool`, `force: bool` | `[]`, `False`, `False`, `False`, `False`, `False` | empty list = all providers |
| `ProviderUpdateResult` | frozen dataclass | `provider_id: str`, `action: UpdateAction`, `freshness: FreshnessCheck`, `fetch: FetchSummary \| None`, `policy: PolicyDecision`, `methodology_changes: list[MethodologyNote]`, `error: str \| None` | - | |
| `UpdateSummary` | frozen dataclass | `started_at: datetime`, `finished_at: datetime`, `results: list[ProviderUpdateResult]`, `warnings: list[str]` | - | `ok` property: no `FAILED` |
| `UpdateSummary.to_dict` / `to_markdown` | methods | `() -> dict[str, Any]` / `() -> str` | - | Summary report |
| `UpdateService.__init__` | method | `(database: Database, registry: ProviderRegistry, status: StatusService, config: AppConfig)` | - | |
| `UpdateService.run` | method | `(request: UpdateRequest) -> UpdateSummary` | - | |

## Behaviour & validators

1. Freshness first: one `StatusService.statuses(online=request.online)` call.
2. Selection per provider, in order: `FRESH` → `SKIPPED_FRESH` (unless `force`);
   `UNKNOWN`/`UNSUPPORTED`/`ERROR` → `SKIPPED_UNKNOWN` unless `include_unknown`;
   `request.scheduled and not policy.allowed` → `SKIPPED_POLICY`;
   `request.scheduled` and last successful fetch younger than
   `source_policy.min_interval_hours` → `SKIPPED_INTERVAL`. `force` never bypasses the
   policy or interval checks when `scheduled=True`.
3. Stale & allowed → `FetchService.fetch(provider, FetchRequest(dry_run=request.dry_run))`.
   A provider exception becomes `FAILED` with `error`; other providers continue.
4. Methodology changes: snapshot `Database.list_methodology_notes(id)` before the fetch,
   compare to after by `(methodology_version, valid_from, valid_to)`; new ones are reported.
5. Idempotency: running `run()` twice back-to-back with unchanged sources yields
   `FETCHED` at most in the first run and only `SKIPPED_*` in the second.
6. Unknown IDs in `config.scheduled_fetch_overrides` produce a summary warning (from 05, rule 4).
7. Validation issues from `FetchSummary.validation_report` surface in the summary; a
   validation error (`report.ok is False`) marks the result `FAILED`.

## Tests

| Test function | File | Type | Asserts |
|---|---|---|---|
| `test_update_fetches_only_stale_providers` | `tests/unit/test_update_service.py` | Integration | fresh fake provider untouched; stale one fetched |
| `test_update_is_idempotent` | same | Integration | second run has zero `FETCHED` |
| `test_scheduled_update_respects_policy` | same | Unit | disallowed provider → `SKIPPED_POLICY` |
| `test_scheduled_update_respects_min_interval` | same | Unit | recent success → `SKIPPED_INTERVAL` |
| `test_force_does_not_bypass_policy_when_scheduled` | same | Unit | rule 2 |
| `test_update_reports_new_methodology_notes` | same | Integration | provider adds a note → listed in result |
| `test_update_continues_after_provider_failure` | same | Unit | one `FAILED`, others processed; `summary.ok is False` |
| `test_update_dry_run_writes_no_observations` | same | Integration | `count_observations` unchanged |

## Success criteria

- [ ] `UpdateService.run` implements rules 1-7.
- [ ] No pipeline logic duplicated from `FetchService`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Service layer only; no Rich/Typer imports.
- Missing data stays missing - the service never back-fills skipped providers ([CLAUDE.md](/CLAUDE.md)).

## Out of scope

- CLI rendering and exit codes - [07](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/07-update-cli.md).

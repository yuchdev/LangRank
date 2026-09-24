# Subtask 01.0/04 - StatusService Freshness & `status --json`

**Task:** [01.0 - Source Freshness Monitoring & Scheduled Updates](/docs/roadmap/0004-freshness-and-releases/01.0-source-freshness-and-updates/README.md) ·
**Role:** Python Expert · **Depends on:** 03 · **Status:** ⬜ Not started

## Goal

Rebuild `StatusService` on top of `FreshnessCheck`, and add `--json` and `--online` to
`langrank status` with a versioned, documented JSON schema suitable for scripts and CI.

## Baseline

- `services/status.py:ProviderStatus` fields: `provider_id`, `latest_local_observation`,
  `last_fetch_status`, `last_failed_fetch_at`, `last_fetch_started_at`, `record_count`,
  `upstream_latest_period`, `provider_state`.
- `cli.py:status` renders a Rich `Table` only.

## Files

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/langrank/services/status.py` | Build `FreshnessContext` from DB, call probe, attach `freshness` |
| Modify | `src/langrank/cli.py` | `status --json`, `status --online` |
| Create | `docs/ops/status-json.md` | JSON schema reference (`status_schema_version: 1`) |
| Create | `tests/unit/test_status_service.py` | Service tests |
| Modify | `tests/integration/test_cli.py` | CLI `--json` acceptance test |

## Symbols / fields

| Symbol | Kind | Type / signature | Default | Notes |
|---|---|---|---|---|
| `ProviderStatus.freshness` | field | `FreshnessCheck` | - | New |
| `ProviderStatus.provider_state` | field | `str` | - | Kept for table compatibility; now `= freshness.state.value` |
| `ProviderStatus.upstream_latest_period` | field | `str \| None` | - | Now `= freshness.upstream_latest_period` |
| `ProviderStatus.to_dict` | method | `() -> dict[str, Any]` | - | Nests `freshness.to_dict()` |
| `StatusService.statuses` | method | `(*, online: bool = False) -> list[ProviderStatus]` | `online=False` | |
| `STATUS_SCHEMA_VERSION` | constant | `int` | `1` | In `services/status.py` |
| `status` CLI | command | `--json/--no-json` (`False`), `--online/--offline` (`False`) | - | |

## Behaviour & validators

1. `StatusService` builds `FreshnessContext` from
   `Database.latest_observation_for_provider` and `Database.latest_raw_artifact` (02).
2. Providers without a probe (`freshness_probe_for` → `None`) get a synthesized
   `FreshnessCheck(state=UNSUPPORTED, mechanism=NONE)` - never an exception.
3. `--json` prints exactly one JSON document to stdout:
   `{"status_schema_version": 1, "generated_at": ISO8601, "online": bool, "providers": [ProviderStatus.to_dict(), ...]}`
   sorted by `provider_id`, `sort_keys=True`, no Rich markup.
4. Exit code is `0` regardless of staleness (status is informational); `ERROR` states are
   reported in the payload, not via exit code.
5. `docs/ops/status-json.md` documents every key and the enum values of `state` and
   `mechanism`.

## Tests

| Test function | File | Type | Asserts |
|---|---|---|---|
| `test_statuses_attach_freshness_for_every_provider` | `tests/unit/test_status_service.py` | Integration | every `ProviderStatus.freshness` populated |
| `test_statuses_offline_makes_no_http_requests` | same | Mock | injected MockTransport records zero requests |
| `test_statuses_unsupported_provider_does_not_raise` | same | Unit | fake provider without probe → `UNSUPPORTED` |
| `test_status_json_is_valid_and_versioned` | `tests/integration/test_cli.py` | E2E | `CliRunner` output parses; `status_schema_version == 1`; providers sorted |
| `test_status_table_still_renders` | `tests/integration/test_cli.py` | E2E | default invocation exit 0, contains `State` column |

## Success criteria

- [ ] `langrank status --json` emits the documented schema.
- [ ] No `hasattr` in `services/status.py`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` green.

## Constraints

- Business logic stays in `services/`; `cli.py` only renders ([CLAUDE.md](/CLAUDE.md)).
- The HTTP client used for `--online` is constructed in `AppState`/service wiring and
  passed down so tests can inject a transport.

## Out of scope

- Persisting freshness history.
